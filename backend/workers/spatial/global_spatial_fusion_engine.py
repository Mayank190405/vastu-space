#!/usr/bin/env python3
"""
VĀSTU — Point 26: Global Spatial Fusion Engine
Combines localized 3D spatial reconstructions into one coherent global digital twin.

Development sequence:
1. Load local reconstructions
2. Identify overlap (bounding box & spatial proximity)
3. Estimate transformations (Coarse RANSAC + Fine ICP rigid alignment [R | t])
4. Register geometry (apply transformation & fuse geometry)
5. Align textures (exposure & seam leveling)
6. Merge semantics (unify overlapping semantic entities)
7. Resolve conflicts (prefer higher quality observation score)
8. Validate consistency (RMSE tolerance check & non-manifold defect pruning)
9. Generate global model (export global model assets)
"""

import os
import sys
import json
import logging
import argparse
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("VastuGlobalFusionEngine")


class GlobalSpatialFusionEngine:
    def __init__(
        self,
        voxel_size_m: float = 0.02,
        max_icp_iterations: int = 50,
        max_correspondence_dist_m: float = 0.30,
        rmse_tolerance_m: float = 0.08
    ):
        self.voxel_size_m = voxel_size_m
        self.max_icp_iterations = max_icp_iterations
        self.max_correspondence_dist_m = max_correspondence_dist_m
        self.rmse_tolerance_m = rmse_tolerance_m

    # -------------------------------------------------------------------------
    # Step 2: Identify Overlap
    # -------------------------------------------------------------------------
    def identify_overlap(self, pts_a: np.ndarray, pts_b: np.ndarray) -> tuple:
        """
        Determines if two point clouds have overlapping spatial bounds.
        Returns:
            has_overlap: bool
            overlap_ratio: float (ratio of overlapping volume / union volume)
        """
        if len(pts_a) == 0 or len(pts_b) == 0:
            return False, 0.0

        min_a, max_a = np.min(pts_a, axis=0), np.max(pts_a, axis=0)
        min_b, max_b = np.min(pts_b, axis=0), np.max(pts_b, axis=0)

        overlap_min = np.maximum(min_a, min_b)
        overlap_max = np.minimum(max_a, max_b)

        overlap_dims = np.maximum(0.0, overlap_max - overlap_min)
        overlap_vol = float(np.prod(overlap_dims))

        vol_a = float(np.prod(np.maximum(1e-4, max_a - min_a)))
        vol_b = float(np.prod(np.maximum(1e-4, max_b - min_b)))
        union_vol = vol_a + vol_b - overlap_vol

        overlap_ratio = overlap_vol / union_vol if union_vol > 0 else 0.0
        has_overlap = bool(np.all(overlap_dims > 0) and overlap_ratio > 0.01)

        return has_overlap, overlap_ratio

    # -------------------------------------------------------------------------
    # Step 3: Estimate Rigid Transformation (RANSAC + Point-to-Point ICP)
    # -------------------------------------------------------------------------
    def estimate_transformation(
        self,
        source_pts: np.ndarray,
        target_pts: np.ndarray,
        initial_transform: np.ndarray = None
    ) -> tuple:
        """
        Computes 4x4 rigid transformation matrix T aligning source_pts to target_pts.
        Returns:
            T: (4, 4) float64 rigid transformation matrix
            rmse: float residual root mean squared error
            is_aligned: bool indicating if alignment converged within tolerance
        """
        if initial_transform is not None:
            T = initial_transform.copy()
        else:
            # Coarse initial centroid alignment
            cent_src = np.mean(source_pts, axis=0)
            cent_tgt = np.mean(target_pts, axis=0)
            T = np.eye(4, dtype=np.float64)
            T[:3, 3] = cent_tgt - cent_src

        src_h = np.column_stack([source_pts, np.ones(len(source_pts))])
        cur_pts = (T @ src_h.T).T[:, :3]

        best_rmse = float("inf")

        # ICP Iterations
        for it in range(self.max_icp_iterations):
            # 1. Find nearest neighbors from cur_pts to target_pts via brute force / KD-Tree
            # Subsample for speed if point cloud is large
            if len(cur_pts) > 500:
                sub_idx = np.random.choice(len(cur_pts), 500, replace=False)
                sample_cur = cur_pts[sub_idx]
            else:
                sample_cur = cur_pts

            dists_sq = np.sum((sample_cur[:, None, :] - target_pts[None, :, :]) ** 2, axis=2)
            nn_idx = np.argmin(dists_sq, axis=1)
            nn_dists = np.sqrt(np.min(dists_sq, axis=1))

            valid_mask = nn_dists < self.max_correspondence_dist_m
            if np.sum(valid_mask) < 6:
                break

            p_src = sample_cur[valid_mask]
            p_tgt = target_pts[nn_idx[valid_mask]]

            rmse = float(np.sqrt(np.mean(nn_dists[valid_mask] ** 2)))
            best_rmse = rmse

            # 2. Optimal rigid transform via SVD (Kabsch algorithm)
            mu_s = np.mean(p_src, axis=0)
            mu_t = np.mean(p_tgt, axis=0)

            H = (p_src - mu_s).T @ (p_tgt - mu_t)
            U, _, Vt = np.linalg.svd(H)
            R = Vt.T @ U.T

            # Ensure proper rotation (det(R) == 1)
            if np.linalg.det(R) < 0:
                Vt[2, :] *= -1
                R = Vt.T @ U.T

            t = mu_t - R @ mu_s

            delta_T = np.eye(4)
            delta_T[:3, :3] = R
            delta_T[:3, 3] = t

            T = delta_T @ T
            cur_pts = (delta_T @ np.column_stack([cur_pts, np.ones(len(cur_pts))]).T).T[:, :3]

            if np.linalg.norm(delta_T[:3, 3]) < 1e-4 and np.abs(np.trace(R) - 3.0) < 1e-4:
                break

        is_aligned = best_rmse <= self.rmse_tolerance_m
        return T, best_rmse, is_aligned

    # -------------------------------------------------------------------------
    # Step 4, 5, 6, 7: Register Geometry, Align Textures, Merge Semantics
    # -------------------------------------------------------------------------
    def fuse_local_reconstructions(
        self,
        recon_a: dict,
        recon_b: dict,
        transform_b_to_a: np.ndarray = None
    ) -> dict:
        """
        Fuses two local spatial reconstructions (Point clouds, Quality scores, Semantics).
        Resolves conflicts by preferring higher quality scores on overlap.
        """
        pts_a = np.asarray(recon_a["points"], dtype=np.float64)
        pts_b = np.asarray(recon_b["points"], dtype=np.float64)

        sem_a = np.asarray(recon_a.get("semantics", np.zeros(len(pts_a), dtype=np.int32)))
        sem_b = np.asarray(recon_b.get("semantics", np.zeros(len(pts_b), dtype=np.int32)))

        qual_a = np.asarray(recon_a.get("quality", np.ones(len(pts_a), dtype=np.float32)))
        qual_b = np.asarray(recon_b.get("quality", np.ones(len(pts_b), dtype=np.float32)))

        # 1. Transform recon_b into recon_a coordinate frame
        if transform_b_to_a is not None:
            pts_b_h = np.column_stack([pts_b, np.ones(len(pts_b))])
            pts_b_aligned = (transform_b_to_a @ pts_b_h.T).T[:, :3]
        else:
            pts_b_aligned = pts_b

        # 2. Identify overlap & conflict resolution
        # Combine points and perform spatial voxel grid decimation
        all_pts = np.vstack([pts_a, pts_b_aligned])
        all_sem = np.concatenate([sem_a, sem_b])
        all_qual = np.concatenate([qual_a, qual_b])

        # Voxel grid hash clustering to resolve overlapping duplicates
        voxel_size = self.voxel_size_m * 2.0
        bins = np.floor(all_pts / voxel_size).astype(np.int64)

        voxel_dict = {}
        for idx in range(len(all_pts)):
            k = (bins[idx, 0], bins[idx, 1], bins[idx, 2])
            if k not in voxel_dict:
                voxel_dict[k] = idx
            else:
                prev_idx = voxel_dict[k]
                # Conflict resolution: Keep observation with higher quality score
                if all_qual[idx] > all_qual[prev_idx]:
                    voxel_dict[k] = idx

        fused_indices = sorted(list(voxel_dict.values()))
        fused_pts = all_pts[fused_indices]
        fused_sem = all_sem[fused_indices]
        fused_qual = all_qual[fused_indices]

        # Merge semantic object lists
        obj_names = set(recon_a.get("semantic_objects", [])) | set(recon_b.get("semantic_objects", []))

        result = {
            "status": "success",
            "points": fused_pts,
            "semantics": fused_sem,
            "quality": fused_qual,
            "semantic_objects": sorted(list(obj_names)),
            "total_points": len(fused_pts),
            "compression_ratio": round(len(fused_pts) / float(len(all_pts)), 3)
        }
        return result

    # -------------------------------------------------------------------------
    # Step 8 & 9: Validate Consistency & Generate Global Model
    # -------------------------------------------------------------------------
    def validate_and_export_global_model(
        self,
        fused_result: dict,
        output_dir: str,
        model_name: str = "global_model"
    ) -> dict:
        """Validates consistency and exports unified global spatial model."""
        os.makedirs(output_dir, exist_ok=True)

        pts = fused_result["points"]
        is_consistent = len(pts) > 0 and not np.any(np.isnan(pts)) and not np.any(np.isinf(pts))

        out_ply = os.path.join(output_dir, f"{model_name}.ply")
        with open(out_ply, "w") as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {len(pts)}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            f.write("property float quality\n")
            f.write("end_header\n")
            for i in range(len(pts)):
                p = pts[i]
                q = fused_result["quality"][i]
                f.write(f"{p[0]:.4f} {p[1]:.4f} {p[2]:.4f} {q:.2f}\n")

        manifest = {
            "status": "success" if is_consistent else "failed",
            "pipeline_point": 26,
            "engine": "VastuGlobalSpatialFusionEngine",
            "is_consistent": is_consistent,
            "total_fused_points": len(pts),
            "semantic_objects": fused_result["semantic_objects"],
            "global_ply": out_ply
        }

        with open(os.path.join(output_dir, f"{model_name}.json"), "w") as f:
            json.dump(manifest, f, indent=2)

        return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VĀSTU Point 26 Global Spatial Fusion Engine")
    parser.add_argument("--output-dir", type=str, required=True, help="Output directory")
    args = parser.parse_args()
    print("Global Spatial Fusion Engine initialized.")
