"""
VĀSTU Indoor Navigation Engine: A* Router
Provides 3D indoor shortest-path calculation with wheelchair and ADA slope constraints.
"""

import heapq
from typing import List, Optional, Tuple, Dict, Any
import numpy as np
from navigation.graph import NavigationGraphModel, NavNode, NavEdge

class IndoorAStarRouter:
    def __init__(self, graph: NavigationGraphModel):
        self.graph = graph

    def plan_route(
        self,
        start_point: np.ndarray,
        target_point: np.ndarray,
        require_wheelchair: bool = False,
        avoid_stairs: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Executes A* pathfinding between start_point and target_point in 3D metric space.
        """
        start_node = self.graph.find_nearest_node(start_point, require_wheelchair)
        target_node = self.graph.find_nearest_node(target_point, require_wheelchair)

        if not start_node or not target_node:
            return None

        # Priority queue stores (f_score, counter, current_node_id)
        counter = 0
        open_set = []
        heapq.heappush(open_set, (0.0, counter, start_node.node_id))

        came_from: Dict[str, Tuple[str, NavEdge]] = {}
        g_score: Dict[str, float] = {node_id: float("inf") for node_id in self.graph.nodes}
        g_score[start_node.node_id] = 0.0

        f_score: Dict[str, float] = {node_id: float("inf") for node_id in self.graph.nodes}
        f_score[start_node.node_id] = start_node.distance_to(target_node)

        visited = set()

        while open_set:
            _, _, current_id = heapq.heappop(open_set)
            if current_id in visited:
                continue
            visited.add(current_id)

            if current_id == target_node.node_id:
                # Reconstruct path
                return self._build_route_result(start_point, target_point, came_from, target_node.node_id)

            current_node = self.graph.nodes[current_id]
            for edge in current_node.edges:
                neighbor = edge.to_node

                if require_wheelchair and not edge.is_wheelchair_accessible:
                    continue
                if avoid_stairs and edge.edge_type == "STAIRS":
                    continue
                if require_wheelchair and edge.slope_degrees > 4.76:
                    continue  # Violates 1:12 ADA maximum slope

                tentative_g = g_score[current_id] + edge.distance_meters
                if tentative_g < g_score[neighbor.node_id]:
                    came_from[neighbor.node_id] = (current_id, edge)
                    g_score[neighbor.node_id] = tentative_g
                    h_val = neighbor.distance_to(target_node)
                    f_score[neighbor.node_id] = tentative_g + h_val

                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor.node_id], counter, neighbor.node_id))

        return None

    def _build_route_result(
        self,
        start_pt: np.ndarray,
        target_pt: np.ndarray,
        came_from: Dict[str, Tuple[str, NavEdge]],
        target_id: str
    ) -> Dict[str, Any]:
        curr = target_id
        path_nodes = []
        path_edges = []
        total_dist = 0.0

        while curr in came_from:
            prev_id, edge = came_from[curr]
            path_nodes.append(self.graph.nodes[curr])
            path_edges.append(edge)
            total_dist += edge.distance_meters
            curr = prev_id

        path_nodes.append(self.graph.nodes[curr])
        path_nodes.reverse()
        path_edges.reverse()

        waypoints = [start_pt.tolist()] + [n.position.tolist() for n in path_nodes] + [target_pt.tolist()]
        est_seconds = int(total_dist / 1.2)  # ~1.2 m/s avg walking speed

        return {
            "success": True,
            "total_distance_meters": round(total_dist, 2),
            "estimated_walk_seconds": est_seconds,
            "waypoints": waypoints,
            "path_node_ids": [n.node_id for n in path_nodes],
            "path_edge_ids": [e.edge_id for e in path_edges],
            "node_count": len(path_nodes),
            "edge_count": len(path_edges),
            "is_wheelchair_accessible": all(e.is_wheelchair_accessible for e in path_edges),
        }
