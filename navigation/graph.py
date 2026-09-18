"""
VĀSTU Indoor Navigation Engine: Graph Model
Represents topological NavMesh nodes, directional edges, and spatial adjacency.
"""

from typing import Dict, List, Optional
import math
import numpy as np

class NavNode:
    def __init__(
        self,
        node_id: str,
        x: float,
        y: float,
        z: float,
        is_wheelchair_accessible: bool = True,
        floor_level: int = 1
    ):
        self.node_id = node_id
        self.position = np.array([x, y, z], dtype=np.float64)
        self.is_wheelchair_accessible = is_wheelchair_accessible
        self.floor_level = floor_level
        self.edges: List["NavEdge"] = []

    def distance_to(self, other: "NavNode") -> float:
        return float(np.linalg.norm(self.position - other.position))

class NavEdge:
    def __init__(
        self,
        edge_id: str,
        from_node: NavNode,
        to_node: NavNode,
        edge_type: str = "CORRIDOR",
        is_wheelchair_accessible: bool = True,
        clearance_width_meters: float = 1.20,
        slope_degrees: float = 0.0
    ):
        self.edge_id = edge_id
        self.from_node = from_node
        self.to_node = to_node
        self.distance_meters = from_node.distance_to(to_node)
        self.edge_type = edge_type
        self.is_wheelchair_accessible = is_wheelchair_accessible
        self.clearance_width_meters = clearance_width_meters
        self.slope_degrees = slope_degrees

class NavigationGraphModel:
    def __init__(self):
        self.nodes: Dict[str, NavNode] = {}
        self.edges: Dict[str, NavEdge] = {}

    def add_node(self, node: NavNode):
        self.nodes[node.node_id] = node

    def add_edge(self, edge: NavEdge):
        self.edges[edge.edge_id] = edge
        edge.from_node.edges.append(edge)

    def find_nearest_node(self, point: np.ndarray, require_wheelchair: bool = False) -> Optional[NavNode]:
        best_node = None
        best_dist = float("inf")
        for node in self.nodes.values():
            if require_wheelchair and not node.is_wheelchair_accessible:
                continue
            dist = float(np.linalg.norm(node.position - point))
            if dist < best_dist:
                best_dist = dist
                best_node = node
        return best_node
