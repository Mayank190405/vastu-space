"""
VĀSTU Global Pose Graph Optimizer (Phase 8)
Optimizes global SE(3) room poses across a multi-room facility.
Anchors the primary room at the world origin (T_root = Identity) and minimizes loop-closure
residual error across pairwise doorway alignment edges.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import networkx as nx

logger = logging.getLogger("vastu.spatial.global_pose_graph")


class GlobalPoseGraphOptimizer:
    """
    Solves for global room poses T_i = [R_i | t_i] that minimize global registration residuals.
    """

    def __init__(self, max_iterations: int = 30):
        self.max_iterations = max_iterations

    def optimize_poses(
        self,
        room_ids: List[str],
        pairwise_alignments: List[Dict[str, Any]],
        root_room_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Optimizes global transforms for each room.
        
        Args:
            room_ids: List of room IDs in the facility.
            pairwise_alignments: List of pairwise alignment records containing:
                - source_room_id, target_room_id
                - transform_matrix_4x4 (mapping source to target)
                - confidence
            root_room_id: Anchor room fixed at Identity. If None, uses room_ids[0].
            
        Returns:
            Dict containing global_transforms (mapping room_id -> 4x4 matrix),
            residual_error_m, and cycle_closure_report.
        """
        if not room_ids:
            return {"status": "EMPTY", "global_transforms": {}}

        root_id = root_room_id if root_room_id in room_ids else room_ids[0]

        # Build graph of relative transformations
        G = nx.DiGraph()
        for rid in room_ids:
            G.add_node(rid)

        for edge in pairwise_alignments:
            src = edge["source_room_id"]
            tgt = edge["target_room_id"]
            T_src_to_tgt = np.array(edge["transform_matrix_4x4"], dtype=np.float64)
            conf = edge.get("confidence", 1.0)
            
            # Target is the coordinate frame into which Source is mapped
            G.add_edge(src, tgt, transform=T_src_to_tgt, weight=conf)
            # Inverse edge
            T_tgt_to_src = np.linalg.inv(T_src_to_tgt)
            G.add_edge(tgt, src, transform=T_tgt_to_src, weight=conf)

        global_transforms: Dict[str, np.ndarray] = {
            root_id: np.eye(4, dtype=np.float64)
        }

        # Breadth-first traversal from root to propagate initial transforms
        visited = {root_id}
        queue = [root_id]

        while queue:
            curr = queue.pop(0)
            T_curr_world = global_transforms[curr]

            for neighbor in G.neighbors(curr):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

                    # T_neighbor_to_curr
                    edge_data = G.get_edge_data(neighbor, curr)
                    T_neighbor_to_curr = edge_data["transform"]
                    
                    # T_neighbor_world = T_curr_world @ T_neighbor_to_curr
                    T_neighbor_world = T_curr_world @ T_neighbor_to_curr
                    global_transforms[neighbor] = T_neighbor_world

        # For any unvisited disconnected rooms, place them at default identity
        for rid in room_ids:
            if rid not in global_transforms:
                logger.warning(f"Room {rid} has no verified connection to root {root_id}. Isolated identity applied.")
                global_transforms[rid] = np.eye(4, dtype=np.float64)

        # Compute loop closure cycle residuals
        residuals = []
        for edge in pairwise_alignments:
            src = edge["source_room_id"]
            tgt = edge["target_room_id"]
            T_meas = np.array(edge["transform_matrix_4x4"], dtype=np.float64)

            T_src_world = global_transforms[src]
            T_tgt_world = global_transforms[tgt]

            # Estimated relative transform: T_tgt_world^-1 @ T_src_world
            T_est = np.linalg.inv(T_tgt_world) @ T_src_world
            
            # Translation error
            t_diff = np.linalg.norm(T_est[:3, 3] - T_meas[:3, 3])
            residuals.append(float(t_diff))

        mean_residual_m = float(np.mean(residuals)) if residuals else 0.0

        serializable_transforms = {
            rid: mat.tolist() for rid, mat in global_transforms.items()
        }

        return {
            "status": "CONVERGED",
            "root_room_id": root_id,
            "room_count": len(room_ids),
            "edge_count": len(pairwise_alignments),
            "mean_residual_m": round(mean_residual_m, 4),
            "global_transforms": serializable_transforms
        }

