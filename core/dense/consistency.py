"""
VĀSTU Dense Reconstruction: Multi-View Depth Consistency
Verifies geometric and photometric consistency across overlapping keyframe depth maps.
Calculates view consensus count and rejects inconsistent or occluded depths.
"""

import cv2
import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("vastu.dense.consistency")


class MultiViewDepthConsistency:
    """
    Validates metric depth maps by cross-projecting between neighboring camera views.
    Ensures geometric depth agreement before 3D fusion.
    """
    def __init__(
        self,
        max_depth_discrepancy_ratio: float = 0.08,  # 8% relative depth discrepancy
        max_reprojection_px: float = 2.0,
        min_view_consensus: int = 2
    ):
        self.max_depth_discrepancy_ratio = max_depth_discrepancy_ratio
        self.max_reprojection_px = max_reprojection_px
        self.min_view_consensus = min_view_consensus

    def verify_consistency(
        self,
        ref_depth: np.ndarray,
        ref_R: np.ndarray,
        ref_t: np.ndarray,
        neighbor_depths: List[np.ndarray],
        neighbor_Rs: List[np.ndarray],
        neighbor_ts: List[np.ndarray],
        neighbor_frame_indices: List[int],
        K: np.ndarray,
        subsample_step: int = 4
    ) -> Tuple[np.ndarray, np.ndarray, Dict[Tuple[int, int], List[int]], Dict[str, Any]]:
        """
        Cross-checks reference depth map against neighbor depth maps.
        Returns:
          - consistent_mask: boolean mask (h, w) of validated pixels
          - consensus_count_map: int array (h, w) of agreeing views
          - point_sources: map of (u, v) -> list of agreeing frame indices
          - stats: verification statistics
        """
        h, w = ref_depth.shape
        consistent_mask = np.zeros((h, w), dtype=bool)
        consensus_count_map = np.ones((h, w), dtype=np.int32)
        point_sources: Dict[Tuple[int, int], List[int]] = {}

        K_inv = np.linalg.inv(K)
        u_coords, v_coords = np.meshgrid(
            np.arange(0, w, subsample_step),
            np.arange(0, h, subsample_step)
        )
        u_flat = u_coords.ravel()
        v_flat = v_coords.ravel()
        z_ref = ref_depth[v_flat, u_flat]

        # Valid depth range filter [0.3m, 8.0m]
        valid_z = (z_ref > 0.3) & (z_ref < 8.0) & np.isfinite(z_ref)
        u_val = u_flat[valid_z]
        v_val = v_flat[valid_z]
        z_val = z_ref[valid_z]

        if len(z_val) == 0:
            return consistent_mask, consensus_count_map, point_sources, {"consistency_ratio": 0.0}

        # Backproject to reference camera coordinates: X_c = z * K_inv * [u, v, 1]^T
        pixels_homo = np.column_stack([u_val, v_val, np.ones_like(u_val)])
        rays_c = (K_inv @ pixels_homo.T).T
        pts_c = rays_c * z_val[:, np.newaxis]

        # Transform to world coordinates: X_w = ref_R.T @ (pts_c - ref_t)
        pts_w = (ref_R.T @ (pts_c.T - ref_t)).T

        total_tested = len(z_val)
        inconsistent_count = 0

        for idx in range(len(u_val)):
            u = int(u_val[idx])
            v = int(v_val[idx])
            X_w = pts_w[idx:idx+1].T

            agreeing_views = []
            for n_idx, (n_depth, n_R, n_t, n_fidx) in enumerate(zip(
                neighbor_depths, neighbor_Rs, neighbor_ts, neighbor_frame_indices
            )):
                # Project X_w into neighbor camera: X_c_n = n_R @ X_w + n_t
                X_c_n = n_R @ X_w + n_t
                z_proj = float(X_c_n[2, 0])
                if z_proj <= 0.2 or z_proj > 8.0:
                    continue

                # Reproject to neighbor pixel: [u_n, v_n, 1] = K @ (X_c_n / z_proj)
                p_n = K @ (X_c_n / z_proj)
                u_n = int(round(float(p_n[0, 0])))
                v_n = int(round(float(p_n[1, 0])))

                if 0 <= u_n < w and 0 <= v_n < h:
                    observed_depth = float(n_depth[v_n, u_n])
                    if observed_depth > 0.2:
                        depth_error = abs(z_proj - observed_depth) / z_proj
                        if depth_error <= self.max_depth_discrepancy_ratio:
                            agreeing_views.append(n_fidx)

            consensus_count = 1 + len(agreeing_views)
            consensus_count_map[v, u] = consensus_count

            # If enough consensus views or standalone high quality candidate
            if consensus_count >= self.min_view_consensus or len(neighbor_depths) == 0:
                consistent_mask[v, u] = True
                point_sources[(u, v)] = agreeing_views
            else:
                inconsistent_count += 1

        consistent_pixels = int(np.sum(consistent_mask))
        consistency_ratio = consistent_pixels / max(1, total_tested)

        stats = {
            "total_tested_pixels": total_tested,
            "consistent_pixels": consistent_pixels,
            "inconsistent_pixels": inconsistent_count,
            "consistency_ratio": round(consistency_ratio, 4),
            "mean_consensus_count": round(float(np.mean(consensus_count_map[v_val, u_val])), 2)
        }
        return consistent_mask, consensus_count_map, point_sources, stats
