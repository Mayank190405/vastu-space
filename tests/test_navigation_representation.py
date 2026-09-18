"""
Unit & Integration Tests for Navigation Representation Subsystem (Stage 21)
Validates:
1. Full 6-stage pipeline: floor -> obstacles -> footprints -> human-radius inflation -> walkable region -> NavMesh/graph.
2. Obstacle accounting: walls, furniture, columns, and doorways.
3. Human-radius inflation (r_human = 0.35m default).
4. Narrow passage detection: pinch points < 2 * r_human (0.70m) identified with NARROW_PASSAGE cause.
5. Disconnected floor detection: elevation steps > 0.50m tagged with DISCONNECTED_FLOOR cause.
6. Strict rule: Zero derivation from Gaussian splats (derived_from_gaussian_splats is False).
7. Acceptance Criterion: Navigation model can be visualized independently, and EVERY blocked region has an identifiable geometric cause.
8. FastAPI Control Plane Endpoints: POST /navigation/build, GET /navigation/representation/{version_id}, GET /navigation/blocked-regions.
"""

import uuid
import pytest
from fastapi.testclient import TestClient

from core.schemas.navigation_representation import (
    BlockedRegionCause,
    BlockedRegion,
    WalkablePolygon,
    DoorwayChokepoint,
    NavigationRepresentation
)
from core.schemas.structural_geometry import StructuralPlane, PlaneEquation, StructuralOpening
from core.schemas.representation_bundle import CollisionObstacle
from core.navigation.generator import NavigationRepresentationGenerator
from api.main import app


@pytest.fixture
def standard_geometry():
    """Generates standard architectural structural planes, collision furniture, columns, and doors."""
    # Floor: 12m x 10m ground floor
    floor_plane = StructuralPlane(
        structure_id="floor_east_wing",
        plane_type="FLOOR",
        plane_equation=PlaneEquation(a=0.0, b=0.0, c=1.0, d=0.0),
        normal_vector=[0.0, 0.0, 1.0],
        inlier_points_count=3500,
        surface_area_m2=120.0,
        corners_3d=[[-6.0, -5.0, 0.0], [6.0, -5.0, 0.0], [6.0, 5.0, 0.0], [-6.0, 5.0, 0.0]]
    )

    # Perimeter North Wall
    north_wall = StructuralPlane(
        structure_id="wall_north_01",
        plane_type="WALL",
        plane_equation=PlaneEquation(a=0.0, b=1.0, c=0.0, d=-5.0),
        normal_vector=[0.0, 1.0, 0.0],
        inlier_points_count=1800,
        surface_area_m2=33.6,
        corners_3d=[[-6.0, 5.0, 0.0], [6.0, 5.0, 0.0], [6.0, 5.0, 2.8], [-6.0, 5.0, 2.8]]
    )

    # Collision Furniture: Conference Table
    conference_table = CollisionObstacle(
        obstacle_id="furn_table_conf",
        obstacle_type="CONFERENCE_TABLE",
        center=[0.0, 0.0, 0.45],
        extent=[2.4, 1.2, 0.9],
        is_walkable=False
    )

    # Structural Column
    column = {
        "id": "col_c1",
        "center": [-3.0, 2.0, 1.4],
        "radius": 0.30,
        "extent": [0.6, 0.6, 2.8]
    }

    # Open Doorway
    door = StructuralOpening(
        opening_type="DOOR",
        width_m=1.10,
        height_m=2.10,
        center_3d=[0.0, 5.0, 1.05]
    )

    return {
        "floor": floor_plane,
        "wall": north_wall,
        "table": conference_table,
        "column": column,
        "door": door
    }


def test_navigation_pipeline_end_to_end(standard_geometry):
    """Verify complete 6-stage execution from structural + collision inputs."""
    generator = NavigationRepresentationGenerator(human_radius_m=0.35)

    nav_rep = generator.build_navigation_representation(
        model_id="twin_model_01",
        version="1.0.0",
        structural_planes=[standard_geometry["floor"], standard_geometry["wall"]],
        collision_obstacles=[standard_geometry["table"]],
        custom_columns=[standard_geometry["column"]],
        doors=[standard_geometry["door"]]
    )

    assert isinstance(nav_rep, NavigationRepresentation)
    assert nav_rep.model_id == "twin_model_01"
    assert nav_rep.version == "1.0.0"
    assert nav_rep.human_radius_m == 0.35

    # Areas
    assert nav_rep.total_floor_area_m2 == 120.0
    assert 0.0 < nav_rep.walkable_area_m2 < nav_rep.total_floor_area_m2
    assert nav_rep.blocked_area_m2 > 0.0

    # NavMesh Graph
    assert nav_rep.navmesh_graph is not None
    assert len(nav_rep.navmesh_graph.nodes) > 0
    assert len(nav_rep.navmesh_graph.edges) > 0

    # Blocked Regions
    assert len(nav_rep.blocked_regions) >= 3  # Wall, Table, Column


def test_human_radius_inflation(standard_geometry):
    """Verify obstacle footprints are inflated by human radius r=0.35m."""
    generator = NavigationRepresentationGenerator(human_radius_m=0.35)

    nav_rep = generator.build_navigation_representation(
        model_id="twin_model_02",
        structural_planes=[standard_geometry["floor"]],
        collision_obstacles=[standard_geometry["table"]]
    )

    # Find blocked region for table
    table_blocked = next((br for br in nav_rep.blocked_regions if br.source_entity_id == "furn_table_conf"), None)
    assert table_blocked is not None
    assert table_blocked.cause == BlockedRegionCause.FURNITURE

    # Extent of table was [2.4, 1.2, 0.9]; with 2 * 0.35m = 0.70m inflation in 2D
    # 2D bounding polygon width should be approx 2.4 + 0.7 = 3.1m
    b_pts = table_blocked.geometry_2d
    dx = max(p[0] for p in b_pts) - min(p[0] for p in b_pts)
    dy = max(p[1] for p in b_pts) - min(p[1] for p in b_pts)
    assert pytest.approx(dx, 0.1) == 3.1
    assert pytest.approx(dy, 0.1) == 1.9
    assert "r=0.35m" in table_blocked.explanation


def test_walls_furniture_columns_doors(standard_geometry):
    """Verify walls, furniture, columns, and doorway portals are explicitly processed."""
    generator = NavigationRepresentationGenerator(human_radius_m=0.35)

    nav_rep = generator.build_navigation_representation(
        model_id="twin_model_03",
        structural_planes=[standard_geometry["floor"], standard_geometry["wall"]],
        collision_obstacles=[standard_geometry["table"]],
        custom_columns=[standard_geometry["column"]],
        doors=[standard_geometry["door"]]
    )

    causes = {br.cause for br in nav_rep.blocked_regions}
    assert BlockedRegionCause.WALL in causes
    assert BlockedRegionCause.FURNITURE in causes
    assert BlockedRegionCause.COLUMN in causes

    # Doorway chokepoints
    assert len(nav_rep.doorways) == 1
    door = nav_rep.doorways[0]
    assert door.width_m == 1.10
    assert door.is_passable is True

    # Doorway edge in graph
    doorway_edges = [e for e in nav_rep.navmesh_graph.edges if e.edge_type == "DOORWAY"]
    assert len(doorway_edges) > 0


def test_narrow_passage_detection():
    """Verify passages narrower than 2 * r_human (0.70m) are pinched out with NARROW_PASSAGE cause."""
    generator = NavigationRepresentationGenerator(human_radius_m=0.35)

    floor = StructuralPlane(
        structure_id="floor_corridor",
        plane_type="FLOOR",
        plane_equation=PlaneEquation(a=0.0, b=0.0, c=1.0, d=0.0),
        normal_vector=[0.0, 0.0, 1.0],
        inlier_points_count=1000,
        surface_area_m2=50.0,
        corners_3d=[[-5.0, -2.5, 0.0], [5.0, -2.5, 0.0], [5.0, 2.5, 0.0], [-5.0, 2.5, 0.0]]
    )

    # Obstacle A: Cabinet 1 at [0.0, -1.0] with extent [1.0, 1.0]
    # Obstacle B: Cabinet 2 at [0.0, 0.5] with extent [1.0, 1.0]
    # Center distance is 1.5m. Edge-to-edge gap is 1.5 - (0.5 + 0.5) = 0.50m
    # 0.50m < 0.70m (2 * 0.35m), so this creates a narrow passage pinch point
    obs_a = CollisionObstacle(
        obstacle_id="cab_01",
        obstacle_type="CABINET",
        center=[0.0, -1.0, 0.5],
        extent=[1.0, 1.0, 1.0],
        is_walkable=False
    )
    obs_b = CollisionObstacle(
        obstacle_id="cab_02",
        obstacle_type="CABINET",
        center=[0.0, 0.5, 0.5],
        extent=[1.0, 1.0, 1.0],
        is_walkable=False
    )

    nav_rep = generator.build_navigation_representation(
        model_id="twin_pinch",
        structural_planes=[floor],
        collision_obstacles=[obs_a, obs_b]
    )

    narrow_blocked = [br for br in nav_rep.blocked_regions if br.cause == BlockedRegionCause.NARROW_PASSAGE]
    assert len(narrow_blocked) > 0
    pinch = narrow_blocked[0]
    assert pinch.clearance_m is not None
    assert pinch.clearance_m < 0.70
    assert pinch.required_clearance_m == 0.70
    assert "Narrow passage" in pinch.explanation


def test_disconnected_floor_detection():
    """Verify elevation difference > 0.5m without stairs is flagged as DISCONNECTED_FLOOR."""
    generator = NavigationRepresentationGenerator()

    ground_floor = StructuralPlane(
        structure_id="floor_level_1",
        plane_type="FLOOR",
        plane_equation=PlaneEquation(a=0.0, b=0.0, c=1.0, d=0.0),
        normal_vector=[0.0, 0.0, 1.0],
        inlier_points_count=2000,
        surface_area_m2=100.0,
        corners_3d=[[-5.0, -5.0, 0.0], [5.0, -5.0, 0.0], [5.0, 5.0, 0.0], [-5.0, 5.0, 0.0]]
    )

    mezzanine_floor = StructuralPlane(
        structure_id="floor_mezzanine",
        plane_type="FLOOR",
        plane_equation=PlaneEquation(a=0.0, b=0.0, c=1.0, d=-3.2),
        normal_vector=[0.0, 0.0, 1.0],
        inlier_points_count=1000,
        surface_area_m2=40.0,
        corners_3d=[[6.0, -5.0, 3.2], [10.0, -5.0, 3.2], [10.0, 5.0, 3.2], [6.0, 5.0, 3.2]]
    )

    nav_rep = generator.build_navigation_representation(
        model_id="twin_multi_level",
        structural_planes=[ground_floor, mezzanine_floor]
    )

    disconnected_regions = [br for br in nav_rep.blocked_regions if br.cause == BlockedRegionCause.DISCONNECTED_FLOOR]
    assert len(disconnected_regions) == 1
    disc = disconnected_regions[0]
    assert disc.source_entity_id == "floor_mezzanine"
    assert "vertically disconnected" in disc.explanation


def test_zero_gaussian_splat_derivation(standard_geometry):
    """Verify strict prohibition: Navigation must NEVER be derived from Gaussian splats."""
    generator = NavigationRepresentationGenerator()
    nav_rep = generator.build_navigation_representation(
        model_id="twin_model_splat_check",
        structural_planes=[standard_geometry["floor"]]
    )

    assert nav_rep.derived_from_gaussian_splats is False


def test_acceptance_criterion_independent_visualization_and_causality(standard_geometry):
    """
    ACCEPTANCE CRITERION TEST:
    The navigation model can be visualized independently and every blocked region has an identifiable geometric cause.
    """
    generator = NavigationRepresentationGenerator(human_radius_m=0.35)

    nav_rep = generator.build_navigation_representation(
        model_id="twin_acceptance",
        structural_planes=[standard_geometry["floor"], standard_geometry["wall"]],
        collision_obstacles=[standard_geometry["table"]],
        custom_columns=[standard_geometry["column"]],
        doors=[standard_geometry["door"]]
    )

    # 1. Independent Visualization Capability:
    # Model contains complete 2D/3D walkable polygons and graph nodes/edges
    assert len(nav_rep.walkable_regions) > 0
    assert len(nav_rep.walkable_regions[0].boundary) >= 4
    assert nav_rep.walkable_regions[0].surface_area_m2 > 0.0
    assert len(nav_rep.navmesh_graph.nodes) > 0
    assert len(nav_rep.navmesh_graph.edges) > 0

    # 2. Identifiable Geometric Cause For EVERY Blocked Region:
    assert len(nav_rep.blocked_regions) > 0
    for br in nav_rep.blocked_regions:
        # Must have valid cause enum
        assert isinstance(br.cause, BlockedRegionCause)
        assert br.cause in [
            BlockedRegionCause.WALL,
            BlockedRegionCause.FURNITURE,
            BlockedRegionCause.COLUMN,
            BlockedRegionCause.DOOR_CLOSED,
            BlockedRegionCause.NARROW_PASSAGE,
            BlockedRegionCause.DISCONNECTED_FLOOR,
            BlockedRegionCause.INACCESSIBLE_ISLAND
        ]

        # Must identify source entity
        assert br.source_entity_id is not None
        assert len(br.source_entity_id) > 0

        # Must have 3D center coordinates
        assert len(br.center_3d) == 3

        # Must have non-empty diagnostic explanation
        assert br.explanation is not None
        assert len(br.explanation.strip()) > 10


def test_fastapi_navigation_endpoints():
    """Verify POST /api/v1/navigation/build, GET /representation/{version_id}, and GET /blocked-regions."""
    client = TestClient(app)

    # Test POST /api/v1/navigation/build
    payload = {
        "model_id": "test_fastapi_twin",
        "version": "1.0.0",
        "human_radius_m": 0.35,
        "structural_planes": [
            {
                "structure_id": "floor_api_01",
                "plane_type": "FLOOR",
                "plane_equation": {"a": 0.0, "b": 0.0, "c": 1.0, "d": 0.0},
                "normal_vector": [0.0, 0.0, 1.0],
                "inlier_points_count": 1000,
                "surface_area_m2": 80.0,
                "corners_3d": [[-4.0, -5.0, 0.0], [4.0, -5.0, 0.0], [4.0, 5.0, 0.0], [-4.0, 5.0, 0.0]]
            }
        ],
        "collision_obstacles": [
            {
                "obstacle_id": "desk_api_01",
                "obstacle_type": "DESK",
                "center": [0.0, 0.0, 0.4],
                "extent": [1.2, 0.8, 0.8],
                "is_walkable": False
            }
        ],
        "doors": []
    }

    build_res = client.post("/api/v1/navigation/build", json=payload)
    assert build_res.status_code == 200
    data = build_res.json()
    assert data["model_id"] == "test_fastapi_twin"
    assert data["derived_from_gaussian_splats"] is False
    assert len(data["blocked_regions"]) >= 1

    # Test GET /api/v1/navigation/representation/1.0.0
    rep_res = client.get("/api/v1/navigation/representation/1.0.0")
    assert rep_res.status_code == 200
    rep_data = rep_res.json()
    assert rep_data["version"] == "1.0.0"

    # Test GET /api/v1/navigation/blocked-regions
    blocked_res = client.get("/api/v1/navigation/blocked-regions?version=1.0.0")
    assert blocked_res.status_code == 200
    blocked_data = blocked_res.json()
    assert len(blocked_data) >= 1
    assert "cause" in blocked_data[0]
    assert "explanation" in blocked_data[0]
