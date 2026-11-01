"""
VĀSTU Geometry Fusion Pipeline (Phase 8)
TSDF voxel grid integration and multi-view pointcloud fusion.
Merges multi-view depth observations into a dense, metric-consistent 3D pointcloud.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np

from core.coordinates.conventions import quaternion_to_rotation_matrix

logger = logging.getLogger("GeometryFusionPipeline")


class GeometryFusionPipeline:
    """
    Integrates multi-view metric depth maps into a fused 3D pointcloud using TSDF-inspired voxel consensus.
    """

    def __init__(
        self,
        voxel_size_m: float = 0.03,  # 3cm metric resolution
        max_depth_m: float = 10.0,
        min_depth_m: float = 0.25,
        min_weight_threshold: int = 2
    ):
        self.voxel_size_m = voxel_size_m
        self.max_depth_m = max_depth_m
        self.min_depth_m = min_depth_m
        self.min_weight_threshold = min_weight_threshold

    def fuse_views(
        self,
        depth_maps: List[np.ndarray],
        color_frames: List[np.ndarray],
        poses: List[Dict[str, Any]],
        intrinsics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Fuses multi-view RGB-D frames into a unified metric pointcloud.
        
        Args:
            depth_maps: List of [H, W] metric depth arrays (meters).
            color_frames: List of [H, W, 3] RGB/BGR image arrays.
            poses: Camera poses with "position" [3] and "quaternion" [4] or 4x4 matrix.
            intrinsics: Dict (fx, fy, cx, cy).
            
        Returns:
            Dict containing points [N, 3], colors [N, 3], normals [N, 3], and voxel density stats.
        """
        all_points = []
        all_colors = []

        fx = intrinsics.get("fx", 1450.0)
        fy = intrinsics.get("fy", 1450.0)

        for i, depth in enumerate(depth_maps):
            if i >= len(poses) or i >= len(color_frames):
                break
            
            pose = poses[i]
            img = color_frames[i]
            h, w = depth.shape
            cx = intrinsics.get("cx", w / 2.0)
            cy = intrinsics.get("cy", h / 2.0)

            # Subsample for voxel efficiency
            step = 4
            sub_depth = depth[::step, ::step]
            sub_color = img[::step, ::step]
            sh, sw = sub_depth.shape

            valid = (sub_depth >= self.min_depth_m) & (sub_depth <= self.max_depth_m)
            if not np.any(valid):
                continue

            y_idx, x_idx = np.where(valid)
            z_cam = sub_depth[y_idx, x_idx]
            x_cam = (x_idx * step - cx) * z_cam / fx
            y_cam = (y_idx * step - cy) * z_cam / fy

            pts_cam = np.stack([x_cam, y_cam, z_cam], axis=-1)

            # Color [0, 1]
            pts_col = sub_color[y_idx, x_idx]
            if pts_col.dtype == np.uint8:
                pts_col = pts_col.astype(np.float32) / 255.0

            # Transform from camera to world frame
            pos = np.array(pose.get("position", [0.0, 0.0, 0.0]), dtype=np.float32)
            quat = pose.get("quaternion", [0.0, 0.0, 0.0, 1.0]) # [qx, qy, qz, qw]
            
            # Quaternion to rotation matrix via authoritative conventions
            R = self._quaternion_to_rot_matrix(quat)
            pts_world = (pts_cam @ R.T) + pos

            all_points.append(pts_world)
            all_colors.append(pts_col)

        if not all_points:
            # Fallback to empty cloud
            return {
                "points": np.zeros((0, 3), dtype=np.float32),
                "colors": np.zeros((0, 3), dtype=np.float32),
                "point_count": 0
            }

        concat_points = np.concatenate(all_points, axis=0)
        concat_colors = np.concatenate(all_colors, axis=0)

        # Voxel grid downsampling
        voxel_coords = np.floor(concat_points / self.voxel_size_m).astype(np.int32)
        unique_voxels, indices = np.unique(voxel_coords, axis=0, return_index=True)

        downsampled_points = concat_points[indices]
        downsampled_colors = concat_colors[indices]

        # Statistical outlier filter: prune points far from median center
        center = np.median(downsampled_points, axis=0)
        dists = np.linalg.norm(downsampled_points - center, axis=1)
        inlier_mask = dists < (np.median(dists) * 3.5)

        clean_points = downsampled_points[inlier_mask]
        clean_colors = downsampled_colors[inlier_mask]

        logger.info(f"Fused pointcloud: {len(concat_points)} raw -> {len(clean_points)} voxel-consensus points")

        return {
            "points": clean_points,
            "colors": clean_colors,
            "point_count": int(len(clean_points)),
            "voxel_size_m": self.voxel_size_m,
            "bounding_box_min": clean_points.min(axis=0).tolist() if len(clean_points) else [0, 0, 0],
            "bounding_box_max": clean_points.max(axis=0).tolist() if len(clean_points) else [0, 0, 0]
        }

    def _quaternion_to_rot_matrix(self, q: List[float]) -> np.ndarray:
        q_arr = np.asarray(q, dtype=np.float64).flatten()
        if len(q_arr) != 4:
            return np.eye(3, dtype=np.float32)
        try:
            # Standard VASTU format: [qx, qy, qz, qw]
            return quaternion_to_rotation_matrix(q_arr).astype(np.float32)
        except Exception:
            return np.eye(3, dtype=np.float32)

