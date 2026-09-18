import numpy as np
import pytest
from navigation.graph import NavigationGraphModel, NavNode, NavEdge
from navigation.router import IndoorAStarRouter
from navigation.instructions import generate_turn_instructions

def test_astar_router_simple_path():
    graph = NavigationGraphModel()
    n1 = NavNode("n1", 0.0, 0.0, 0.0)
    n2 = NavNode("n2", 2.0, 0.0, 0.0)
    n3 = NavNode("n3", 5.0, 0.0, 0.0)
    
    graph.add_node(n1)
    graph.add_node(n2)
    graph.add_node(n3)
    
    e1 = NavEdge("e1", n1, n2)
    e2 = NavEdge("e2", n2, n3)
    graph.add_edge(e1)
    graph.add_edge(e2)
    
    router = IndoorAStarRouter(graph)
    route = router.plan_route(np.array([0.0, 0.0, 0.0]), np.array([5.0, 0.0, 0.0]))
    
    assert route is not None
    assert route["success"] is True
    assert route["total_distance_meters"] == pytest.approx(5.0, 0.01)
    assert len(route["path_node_ids"]) == 3

def test_wheelchair_slope_constraint():
    graph = NavigationGraphModel()
    # Path A: Steep ramp (slope 8.0 degrees)
    # Path B: Flat path around
    start = NavNode("start", 0.0, 0.0, 0.0)
    steep_node = NavNode("steep", 1.0, 0.0, 0.0)
    dest = NavNode("dest", 3.0, 0.0, 0.0)
    
    flat_node = NavNode("flat", 1.0, 0.0, 2.0)
    
    graph.add_node(start)
    graph.add_node(steep_node)
    graph.add_node(dest)
    graph.add_node(flat_node)
    
    # Steep path direct to dest
    e_steep1 = NavEdge("e_steep1", start, steep_node, slope_degrees=8.0, is_wheelchair_accessible=True)
    e_steep2 = NavEdge("e_steep2", steep_node, dest, slope_degrees=0.0)
    graph.add_edge(e_steep1)
    graph.add_edge(e_steep2)
    
    # Flat detour
    e_flat1 = NavEdge("e_flat1", start, flat_node, slope_degrees=2.0)
    e_flat2 = NavEdge("e_flat2", flat_node, dest, slope_degrees=2.0)
    graph.add_edge(e_flat1)
    graph.add_edge(e_flat2)
    
    router = IndoorAStarRouter(graph)
    
    # Without wheelchair requirement: should pick direct steep path
    std_route = router.plan_route(start.position, dest.position, require_wheelchair=False)
    assert std_route is not None
    assert "steep" in std_route["path_node_ids"]
    
    # With wheelchair requirement: should reject 8.0 deg slope and take flat detour
    wheelchair_route = router.plan_route(start.position, dest.position, require_wheelchair=True)
    assert wheelchair_route is not None
    assert "flat" in wheelchair_route["path_node_ids"]
    assert "steep" not in wheelchair_route["path_node_ids"]

def test_turn_instructions():
    waypoints = [
        [0.0, 0.0, 0.0],
        [0.0, 0.0, 5.0],
        [5.0, 0.0, 5.0],
        [5.0, 0.0, 10.0]
    ]
    steps = generate_turn_instructions(waypoints)
    assert len(steps) == 3
    assert steps[0]["turn_type"] == "straight"
    assert steps[-1]["turn_type"] == "arrive"
