"""
Unit & Integration Tests for Route Planning Engine (Stage 22)
Validates:
1. Full 5-stage pipeline: nearest valid point -> A* -> waypoint extraction -> path smoothing -> collision validation.
2. Destination POI resolution (resolving POI entity, name, viewpoint, coordinates).
3. Multi-criteria cost optimization: distance, excessive turns, narrow passages, wheelchair slope.
4. Path smoothing via string-pulling shortcutting.
5. Strict rejection policy: Trapped endpoints or colliding obstacles reject routes rather than returning them.
6. Acceptance Criterion: Every returned route is collision-free against the current collision model.
7. FastAPI HTTP Endpoints: POST /api/v1/navigation/plan and POST /api/v1/navigation/route.
"""

import uuid
import pytest
import numpy as np
from fastapi.testclient import TestClient

from core.schemas.route_planning import (
    RoutePlanningRequest,
    RouteTurnStep,
    RoutePlanningResult
)
from core.schemas.representation_bundle import CollisionObstacle
from core.schemas.poi import PointOfInterest, POICoordinates, POICameraViewpoint
from core.poi.service import POIService
from core.navigation.planner import RoutePlanningEngine
from navigation.graph import NavigationGraphModel, NavNode, NavEdge
from api.main import app


@pytest.fixture
def test_environment():
    """Sets up a comprehensive navigation graph, obstacles, and POI service."""
    graph = NavigationGraphModel()
    poi_service = POIService()

    # Create 4x4 Grid Navigation Graph (Spacing: 2.0m)
    # x from 0 to 6, y from 0 to 6
    nodes = {}
    for x in [0.0, 2.0, 4.0, 6.0]:
        for y in [0.0, 2.0, 4.0, 6.0]:
            nid = f"n_{int(x)}_{int(y)}"
            node = NavNode(nid, x, y, 0.0, is_wheelchair_accessible=True, floor_level=1)
            graph.add_node(node)
            nodes[(x, y)] = node

    # Add bidirectional grid edges
    edge_id = 1
    for (x, y), n in nodes.items():
        # Connect to (x+2, y)
        if (x + 2.0, y) in nodes:
            neighbor = nodes[(x + 2.0, y)]
            e1 = NavEdge(f"e_{edge_id}", n, neighbor, clearance_width_meters=1.50)
            e2 = NavEdge(f"e_{edge_id+1}", neighbor, n, clearance_width_meters=1.50)
            graph.add_edge(e1)
            graph.add_edge(e2)
            edge_id += 2
        # Connect to (x, y+2)
        if (x, y + 2.0) in nodes:
            neighbor = nodes[(x, y + 2.0)]
            e1 = NavEdge(f"e_{edge_id}", n, neighbor, clearance_width_meters=1.50)
            e2 = NavEdge(f"e_{edge_id+1}", neighbor, n, clearance_width_meters=1.50)
            graph.add_edge(e1)
            graph.add_edge(e2)
            edge_id += 2

    # Add Obstacle in the middle: Table at [2.0, 2.0]
    table = CollisionObstacle(
        obstacle_id="obs_table_center",
        obstacle_type="FURNITURE",
        center=[2.0, 2.0, 0.45],
        extent=[1.2, 1.2, 0.9],
        is_walkable=False
    )

    # Add POI: Meeting Room 4 at [6.0, 6.0]
    target_poi = PointOfInterest(
        id=uuid.uuid4(),
        name="Meeting Room 4",
        aliases=["MR-04"],
        category="ROOM",
        coordinates=POICoordinates(x=6.0, y=6.0, z=0.0),
        coordinates_m=POICoordinates(x=6.0, y=6.0, z=0.0),
        viewpoint=POICameraViewpoint(position=[5.8, 5.8, 0.0], look_at=[6.0, 6.0, 0.0]),
        room="Executive Suite",
        model_version="1.0.0"
    )
    poi_service.create_poi(target_poi)

    return {
        "graph": graph,
        "obstacles": [table],
        "poi_service": poi_service,
        "target_poi": target_poi,
        "planner": RoutePlanningEngine(default_human_radius_m=0.35)
    }


def test_route_planning_pipeline_end_to_end(test_environment):
    """Verify full 5-stage execution: nearest point -> A* -> waypoints -> smoothing -> collision check."""
    planner = test_environment["planner"]
    graph = test_environment["graph"]
    obstacles = test_environment["obstacles"]

    req = RoutePlanningRequest(
        start_position=[0.0, 0.0, 0.0],
        destination_coordinates=[6.0, 4.0, 0.0],
        human_radius_m=0.35,
        enable_smoothing=True
    )

    result = planner.plan_route(req, graph, obstacles=obstacles)

    assert result.success is True
    assert result.route_id.startswith("route_")
    assert len(result.waypoints) >= 2
    assert result.total_distance_meters > 0.0
    assert result.estimated_duration_seconds > 0
    assert result.collision_validated is True
    assert len(result.steps) >= 2
    assert result.steps[0].action == "START"
    assert result.steps[-1].action == "ARRIVE"


def test_poi_destination_resolution(test_environment):
    """Verify route planning resolves destination POI by ID and approaches via viewpoint."""
    planner = test_environment["planner"]
    graph = test_environment["graph"]
    obstacles = test_environment["obstacles"]
    poi_service = test_environment["poi_service"]
    target_poi = test_environment["target_poi"]

    req = RoutePlanningRequest(
        start_position=[0.0, 0.0, 0.0],
        destination_poi_id=str(target_poi.id),
        enable_smoothing=True
    )

    result = planner.plan_route(req, graph, obstacles=obstacles, poi_service=poi_service)

    assert result.success is True
    assert result.destination_poi_id == str(target_poi.id)
    assert result.destination_poi_name == "Meeting Room 4"
    assert pytest.approx(result.destination_position[0], 0.1) == 5.8
    assert pytest.approx(result.destination_position[1], 0.1) == 5.8


def test_multi_criteria_turn_penalty():
    """Verify excessive turning angles are penalized in cost function compared to straight routes."""
    graph = NavigationGraphModel()

    # Route A: Straight line of 3 nodes (distance = 6m, turns = 0)
    # Route B: Detour with two sharp 90-degree turns (distance = 6.2m, turns = 2)
    s = NavNode("start", 0.0, 0.0, 0.0)
    g = NavNode("goal", 6.0, 0.0, 0.0)

    # Route A intermediate
    a1 = NavNode("a1", 3.0, 0.0, 0.0)

    # Route B intermediate (zig-zag detour)
    b1 = NavNode("b1", 1.0, 2.0, 0.0)
    b2 = NavNode("b2", 5.0, 2.0, 0.0)

    for n in [s, g, a1, b1, b2]:
        graph.add_node(n)

    # Route A edges
    graph.add_edge(NavEdge("ea1", s, a1, clearance_width_meters=1.5))
    graph.add_edge(NavEdge("ea2", a1, g, clearance_width_meters=1.5))

    # Route B edges
    graph.add_edge(NavEdge("eb1", s, b1, clearance_width_meters=1.5))
    graph.add_edge(NavEdge("eb2", b1, b2, clearance_width_meters=1.5))
    graph.add_edge(NavEdge("eb3", b2, g, clearance_width_meters=1.5))

    planner = RoutePlanningEngine()
    req = RoutePlanningRequest(
        start_position=[0.0, 0.0, 0.0],
        destination_coordinates=[6.0, 0.0, 0.0],
        turn_penalty_weight=2.0,
        enable_smoothing=False
    )

    result = planner.plan_route(req, graph)
    assert result.success is True
    # Router must pick the straight route (a1) rather than the zig-zag detour (b1, b2)
    assert "a1" in [wp for wp in result.raw_waypoints] or result.turn_count == 0


def test_narrow_passage_cost_penalty():
    """Verify narrow passages (< 1.20m) incur penalties, favoring wider corridors when available."""
    graph = NavigationGraphModel()

    s = NavNode("start", 0.0, 0.0, 0.0)
    g = NavNode("goal", 4.0, 0.0, 0.0)

    # Path 1: Wide corridor (clearance = 1.80m)
    w1 = NavNode("wide", 2.0, 1.0, 0.0)
    # Path 2: Narrow pinch (clearance = 0.75m)
    n1 = NavNode("narrow", 2.0, -0.2, 0.0)

    for n in [s, g, w1, n1]:
        graph.add_node(n)

    # Wide path
    graph.add_edge(NavEdge("ew1", s, w1, clearance_width_meters=1.80))
    graph.add_edge(NavEdge("ew2", w1, g, clearance_width_meters=1.80))

    # Narrow path
    graph.add_edge(NavEdge("en1", s, n1, clearance_width_meters=0.75))
    graph.add_edge(NavEdge("en2", n1, g, clearance_width_meters=0.75))

    planner = RoutePlanningEngine()
    req = RoutePlanningRequest(
        start_position=[0.0, 0.0, 0.0],
        destination_coordinates=[4.0, 0.0, 0.0],
        narrow_passage_penalty_weight=3.0,
        enable_smoothing=False
    )

    result = planner.plan_route(req, graph)
    assert result.success is True
    # Router chooses wide path despite narrow path being 0.2m shorter
    assert result.total_distance_meters == pytest.approx(4.4, 0.1)


def test_wheelchair_accessibility_constraints():
    """Verify wheelchair mode strictly rejects slopes > 4.76 degrees and stairs."""
    graph = NavigationGraphModel()

    start = NavNode("start", 0.0, 0.0, 0.0)
    dest = NavNode("dest", 4.0, 0.0, 0.0)

    # Steep ramp node (slope = 8.0 deg > 4.76 deg)
    steep = NavNode("steep", 2.0, 0.0, 0.0)
    # Flat detour node (slope = 1.0 deg)
    flat = NavNode("flat", 2.0, 2.0, 0.0)

    for n in [start, dest, steep, flat]:
        graph.add_node(n)

    # Steep path
    graph.add_edge(NavEdge("e_steep1", start, steep, slope_degrees=8.0, is_wheelchair_accessible=True))
    graph.add_edge(NavEdge("e_steep2", steep, dest, slope_degrees=0.0))

    # Flat accessible path
    graph.add_edge(NavEdge("e_flat1", start, flat, slope_degrees=1.0, is_wheelchair_accessible=True))
    graph.add_edge(NavEdge("e_flat2", flat, dest, slope_degrees=1.0, is_wheelchair_accessible=True))

    planner = RoutePlanningEngine()

    # Wheelchair Mode: MUST reject steep path and take flat accessible detour
    req_wc = RoutePlanningRequest(
        start_position=[0.0, 0.0, 0.0],
        destination_coordinates=[4.0, 0.0, 0.0],
        require_wheelchair=True,
        enable_smoothing=False
    )
    res_wc = planner.plan_route(req_wc, graph)
    assert res_wc.success is True
    assert res_wc.max_slope_degrees <= 4.76
    assert res_wc.is_wheelchair_accessible is True


def test_path_smoothing_shortcuts():
    """Verify string-pulling eliminates collinear intermediate lattice nodes in open space."""
    graph = NavigationGraphModel()

    # 5 collinear nodes along X axis: [0,0], [1,0], [2,0], [3,0], [4,0]
    prev = None
    for x in range(5):
        node = NavNode(f"node_{x}", float(x), 0.0, 0.0)
        graph.add_node(node)
        if prev:
            graph.add_edge(NavEdge(f"edge_{x}", prev, node, clearance_width_meters=2.0))
        prev = node

    planner = RoutePlanningEngine()
    req = RoutePlanningRequest(
        start_position=[0.0, 0.0, 0.0],
        destination_coordinates=[4.0, 0.0, 0.0],
        enable_smoothing=True
    )

    result = planner.plan_route(req, graph, obstacles=[])
    assert result.success is True
    # Smoothed path shortcuts directly from start to end in 2 waypoints!
    assert len(result.waypoints) == 2
    assert len(result.raw_waypoints) == 5
    assert result.metadata["smoothed_node_reduction"] == 3


def test_strict_rejection_of_colliding_routes():
    """Verify routes passing through obstacles or trapped endpoints are strictly rejected."""
    graph = NavigationGraphModel()
    n1 = NavNode("n1", 0.0, 0.0, 0.0)
    n2 = NavNode("n2", 4.0, 0.0, 0.0)
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_edge(NavEdge("e1", n1, n2))

    # Impassable wall blocking the exact segment between [0,0] and [4,0]
    wall_obstacle = CollisionObstacle(
        obstacle_id="obs_wall_impassable",
        obstacle_type="WALL",
        center=[2.0, 0.0, 0.5],
        extent=[1.5, 3.0, 2.5],
        is_walkable=False
    )

    planner = RoutePlanningEngine(default_human_radius_m=0.35)

    # Route directly hits the obstacle
    req = RoutePlanningRequest(
        start_position=[0.0, 0.0, 0.0],
        destination_coordinates=[4.0, 0.0, 0.0]
    )

    result = planner.plan_route(req, graph, obstacles=[wall_obstacle])

    # Rejection policy: Never return a colliding route!
    assert result.success is False
    assert result.rejection_reason is not None
    assert "REJECTED_COLLISION_DETECTED" in result.rejection_reason
    assert result.collision_validated is False


def test_acceptance_criterion_all_returned_routes_collision_free(test_environment):
    """
    ACCEPTANCE CRITERION TEST:
    Every returned route is collision-free against the current collision model.
    """
    planner = test_environment["planner"]
    graph = test_environment["graph"]
    obstacles = test_environment["obstacles"]

    test_queries = [
        ([0.0, 0.0, 0.0], [6.0, 0.0, 0.0]),
        ([0.0, 0.0, 0.0], [6.0, 6.0, 0.0]),
        ([0.0, 4.0, 0.0], [6.0, 2.0, 0.0]),
    ]

    human_r = 0.35

    for start, target in test_queries:
        req = RoutePlanningRequest(
            start_position=start,
            destination_coordinates=target,
            human_radius_m=human_r,
            enable_smoothing=True
        )

        res = planner.plan_route(req, graph, obstacles=obstacles)
        if res.success:
            assert res.collision_validated is True

            # Perform independent dense metric validation (every 0.05m along all segments)
            wps = res.waypoints
            for i in range(len(wps) - 1):
                p1 = np.array(wps[i])
                p2 = np.array(wps[i+1])
                seg_len = float(np.linalg.norm(p2 - p1))
                steps = max(2, int(seg_len / 0.05))

                for s in range(steps + 1):
                    t = s / float(steps)
                    pt = (1.0 - t) * p1 + t * p2

                    for obs in obstacles:
                        # Bounding box clearance check
                        cx, cy = obs.center[0], obs.center[1]
                        hx, hy = obs.extent[0] / 2.0, obs.extent[1] / 2.0
                        dx = max(0.0, abs(pt[0] - cx) - hx)
                        dy = max(0.0, abs(pt[1] - cy) - hy)
                        dist = np.sqrt(dx*dx + dy*dy)

                        # Must maintain full body radius clearance
                        assert dist >= (human_r - 1e-3), (
                            f"Collision violation at {pt} with obstacle {obs.obstacle_id}: clearance {dist:.3f}m < {human_r}m"
                        )


def test_fastapi_route_planning_endpoint(test_environment):
    """Verify HTTP POST /api/v1/navigation/plan endpoint with POI resolution and rejection handling."""
    client = TestClient(app)
    target_poi = test_environment["target_poi"]

    # 1. Valid Route Request (corridor along Y=2.5 clear of center desk at Y=0.0)
    payload = {
        "start_position": [-3.0, 2.5, 0.0],
        "destination_coordinates": [3.0, 2.5, 0.0],
        "human_radius_m": 0.35,
        "enable_smoothing": True
    }
    res = client.post("/api/v1/navigation/plan", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert len(data["waypoints"]) >= 2
    assert "steps" in data
    assert data["collision_validated"] is True

    # 2. Invalid POI Rejection (returns HTTP 422 with diagnostic reason)
    invalid_payload = {
        "start_position": [0.0, 0.0, 0.0],
        "destination_poi_id": "non_existent_poi_uuid",
        "human_radius_m": 0.35
    }
    fail_res = client.post("/api/v1/navigation/plan", json=invalid_payload)
    assert fail_res.status_code == 422
    assert "REJECTED_DESTINATION_NOT_FOUND" in fail_res.json()["detail"]
