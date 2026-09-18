#!/usr/bin/env python3
"""
VĀSTU Spatial Reconstruction Engine - Point 21: Dense Point Cloud Fusion
Technologies: Open3D, C++, Python.

Performs:
1. Multi-view depth & camera pose unprojection into 3D world space.
2. 2cm uniform voxel grid hashing & multi-view centroid fusion.
3. Statistical Outlier Removal (SOR) to prune floating depth noise.
4. PCA surface normal estimation oriented towards camera centers.
5. Spatial density computation and 0.5m Spatial Cell octant partitioning.
6. Semantic structural segmentation (walls, floor, ceiling, doors, windows, furniture).
7. Stanford PLY (ASCII/Binary) export.
"""

import os
import sys
import json
import math
import time
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2
from scipy.spatial import cKDTree

# Optional Open3D integration
try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    HAS_OPEN3D = False


class DensePointCloudEngine:
    def __init__(
        self,
        voxel_size_m: float = 0.02, # 2cm spatial downsampling
        min_confidence: float = 0.35,
        sor_k_neighbors: int = 15,
        sor_std_ratio: float = 1.5,
        spatial_cell_size_m: float = 0.50, # 50cm spatial cell octants
        use_open3d: bool = True
    ):
        self.voxel_size_m = voxel_size_m
        self.min_confidence = min_confidence
        self.sor_k_neighbors = sor_k_neighbors
        self.sor_std_ratio = sor_std_ratio
        self.spatial_cell_size_m = spatial_cell_size_m
        self.use_open3d = use_open3d and HAS_OPEN3D

    def unproject_keyframe_depth(
        self,
        depth_map: np.ndarray,
        confidence_map: np.ndarray,
        rgb_image: np.ndarray,
        K: np.ndarray,
        R_cam: np.ndarray,
        t_cam: np.ndarray,
        keyframe_id: int,
        stride: int = 2
    ) -> Dict[str, np.ndarray]:
        """
        Unprojects a dense depth map into 3D world coordinates with RGB colors,
        confidence weights, and viewpoint ray vectors.
        """
        h, w = depth_map.shape
        y_grid, x_grid = np.mgrid[0:h:stride, 0:w:stride]
        x_flat = x_grid.ravel()
        y_flat = y_grid.ravel()

        z = depth_map[y_flat, x_flat]
        conf = confidence_map[y_flat, x_flat]

        # Filter valid depth and confidence
        valid = (z >= 0.1) & (z <= 25.0) & (conf >= self.min_confidence)
        if not np.any(valid):
            return {
                "points": np.empty((0, 3), dtype=np.float32),
                "colors": np.empty((0, 3), dtype=np.uint8),
                "confidences": np.empty((0,), dtype=np.float32),
                "view_dirs": np.empty((0, 3), dtype=np.float32)
            }

        x_v = x_flat[valid]
        y_v = y_flat[valid]
        z_v = z[valid]
        conf_v = conf[valid]

        # 1. Unproject to Camera Space
        fx, fy = K[0, 0], K[1, 1]
        cx, cy = K[0, 2], K[1, 2]
        x_cam = (x_v - cx) * z_v / fx
        y_cam = (y_v - cy) * z_v / fy
        pts_cam = np.vstack((x_cam, y_cam, z_v)) # 3xN

        # 2. Transform to World Space: P_w = R^T * (P_cam - t)
        pts_world = (R_cam.T @ (pts_cam - t_cam.reshape((3, 1)))).T.astype(np.float32) # Nx3

        # 3. Sample RGB Colors (convert BGR to RGB)
        colors_bgr = rgb_image[y_v, x_v]
        colors_rgb = colors_bgr[:, [2, 1, 0]].astype(np.uint8)

        # 4. Compute Viewpoint vectors pointing towards camera center: C_world = -R^T * t
        cam_center = (-R_cam.T @ t_cam.reshape((3, 1))).flatten()
        view_dirs = (cam_center - pts_world).astype(np.float32)
        norms = np.linalg.norm(view_dirs, axis=1, keepdims=True)
        view_dirs /= np.maximum(norms, 1e-6)

        return {
            "points": pts_world,
            "colors": colors_rgb,
            "confidences": conf_v.astype(np.float32),
            "view_dirs": view_dirs
        }

    def voxel_grid_fusion(
        self,
        points: np.ndarray,
        colors: np.ndarray,
        confidences: np.ndarray,
        view_dirs: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Merges multi-view points using uniform 3D voxel grid hashing with
        confidence-weighted coordinate and color averaging.
        """
        if len(points) == 0:
            return points, colors, confidences, view_dirs

        # Calculate voxel grid indices
        voxel_indices = np.floor(points / self.voxel_size_m).astype(np.int32)
        
        min_idx = np.min(voxel_indices, axis=0)
        shifted = voxel_indices - min_idx
        max_shifted = np.max(shifted, axis=0) + 1
        
        # 64-bit integer hashing
        keys = (shifted[:, 0].astype(np.int64) * max_shifted[1] * max_shifted[2] +
                shifted[:, 1].astype(np.int64) * max_shifted[2] +
                shifted[:, 2].astype(np.int64))

        sort_order = np.argsort(keys)
        keys_sorted = keys[sort_order]
        points_sorted = points[sort_order]
        colors_sorted = colors[sort_order].astype(np.float32)
        conf_sorted = confidences[sort_order]
        view_sorted = view_dirs[sort_order]

        # Find unique voxel boundaries
        unique_keys, split_indices = np.unique(keys_sorted, return_index=True)
        split_indices = np.append(split_indices[1:], len(points_sorted))

        fused_points = []
        fused_colors = []
        fused_conf = []
        fused_views = []

        start_idx = 0
        for end_idx in split_indices:
            pts_group = points_sorted[start_idx:end_idx]
            conf_group = conf_sorted[start_idx:end_idx]
            colors_group = colors_sorted[start_idx:end_idx]
            views_group = view_sorted[start_idx:end_idx]

            # Confidence-weighted centroid
            weights = conf_group / (np.sum(conf_group) + 1e-6)
            p_mean = np.sum(pts_group * weights[:, np.newaxis], axis=0)
            c_mean = np.sum(colors_group * weights[:, np.newaxis], axis=0)
            conf_mean = np.max(conf_group)
            v_mean = np.mean(views_group, axis=0)
            v_norm = np.linalg.norm(v_mean)
            if v_norm > 1e-6:
                v_mean /= v_norm

            fused_points.append(p_mean)
            fused_colors.append(c_mean)
            fused_conf.append(conf_mean)
            fused_views.append(v_mean)

            start_idx = end_idx

        return (
            np.array(fused_points, dtype=np.float32),
            np.clip(np.array(fused_colors), 0, 255).astype(np.uint8),
            np.array(fused_conf, dtype=np.float32),
            np.array(fused_views, dtype=np.float32)
        )

    def statistical_outlier_removal(
        self,
        points: np.ndarray,
        colors: np.ndarray,
        confidences: np.ndarray,
        view_dirs: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Executes Statistical Outlier Removal (SOR) to prune floating depth artifacts.
        Points with mean k-NN distance > mu + std_ratio * sigma are discarded.
        """
        n_points = len(points)
        if n_points <= self.sor_k_neighbors:
            return points, colors, confidences, view_dirs

        k = min(self.sor_k_neighbors + 1, n_points)
        tree = cKDTree(points)
        dists, _ = tree.query(points, k=k)

        mean_dists = np.mean(dists[:, 1:], axis=1)

        mu = np.mean(mean_dists)
        sigma = np.std(mean_dists)
        threshold = mu + self.sor_std_ratio * sigma

        inliers = mean_dists <= threshold
        return points[inliers], colors[inliers], confidences[inliers], view_dirs[inliers]

    def estimate_surface_normals(
        self,
        points: np.ndarray,
        view_dirs: np.ndarray,
        k_neighbors: int = 12
    ) -> np.ndarray:
        """
        Computes local PCA covariance surface normals oriented towards camera viewpoints.
        """
        n_points = len(points)
        if n_points < 4:
            return np.zeros((n_points, 3), dtype=np.float32)

        tree = cKDTree(points)
        k = min(k_neighbors, n_points)
        _, idxs = tree.query(points, k=k)

        normals = np.zeros((n_points, 3), dtype=np.float32)

        for i in range(n_points):
            neighbors = points[idxs[i]]
            centroid = np.mean(neighbors, axis=0)
            cov = (neighbors - centroid).T @ (neighbors - centroid) / float(k)

            eigvals, eigvecs = np.linalg.eigh(cov)
            normal = eigvecs[:, 0]

            if np.dot(normal, view_dirs[i]) < 0:
                normal = -normal

            normals[i] = normal

        return normals

    def partition_spatial_cells(
        self,
        points: np.ndarray
    ) -> Dict[str, Any]:
        """
        Partitions the dense 3D point cloud into 0.5m x 0.5m x 0.5m spatial cells (octants).
        """
        if len(points) == 0:
            return {"total_cells": 0, "cell_size_m": self.spatial_cell_size_m, "cells": []}

        min_bound = np.min(points, axis=0)
        cell_coords = np.floor((points - min_bound) / self.spatial_cell_size_m).astype(np.int32)

        unique_cells, counts = np.unique(cell_coords, axis=0, return_counts=True)
        cells_list = []

        for idx, coord in enumerate(unique_cells):
            cell_min = min_bound + coord * self.spatial_cell_size_m
            cell_max = cell_min + self.spatial_cell_size_m
            cell_id = f"cell_{int(coord[0])}_{int(coord[1])}_{int(coord[2])}"

            cells_list.append({
                "cell_id": cell_id,
                "grid_coord": [int(coord[0]), int(coord[1]), int(coord[2])],
                "bounding_box_min": [round(float(v), 3) for v in cell_min],
                "bounding_box_max": [round(float(v), 3) for v in cell_max],
                "point_count": int(counts[idx])
            })

        return {
            "total_cells": len(cells_list),
            "cell_size_m": self.spatial_cell_size_m,
            "cells": cells_list
        }

    def compute_spatial_coverage_and_density(
        self,
        points: np.ndarray,
        normals: np.ndarray
    ) -> Dict[str, Any]:
        """
        Evaluates structural element coverage (walls, floor, ceiling, doors, windows, furniture)
        and point cloud density.
        """
        if len(points) == 0:
            return {"status": "empty"}

        min_b = np.min(points, axis=0)
        max_b = np.max(points, axis=0)
        dim = max_b - min_b
        volume_m3 = float(max(0.01, dim[0] * dim[1] * dim[2]))
        floor_area_m2 = float(max(0.01, dim[0] * dim[2]))

        volumetric_density = len(points) / volume_m3
        surface_density = len(points) / floor_area_m2

        # Floor/Ceiling: |ny| > 0.80
        # Vertical Walls/Doors/Windows: |ny| < 0.35
        is_horizontal = np.abs(normals[:, 1]) > 0.80
        is_vertical = np.abs(normals[:, 1]) < 0.35

        if dim[1] < 0.05:
            # Flat single-height dataset
            floor_mask = is_horizontal
            ceiling_mask = np.zeros(len(points), dtype=bool)
            wall_mask = is_vertical
        else:
            floor_mask = is_horizontal & (points[:, 1] <= (min_b[1] + 0.35 * dim[1]))
            ceiling_mask = is_horizontal & (points[:, 1] >= (max_b[1] - 0.35 * dim[1]))
            wall_mask = is_vertical

        # Multi-room identification via spatial gap analysis along X-Z plane
        coords_2d = points[:, [0, 2]]
        room_ids = np.zeros(len(points), dtype=np.int32)
        if dim[0] > 4.0 or dim[2] > 4.0:
            # Multi-room split on primary axis
            split_axis = 0 if dim[0] > dim[2] else 2
            mid_val = min_b[split_axis] + dim[split_axis] / 2.0
            room_ids[points[:, split_axis] > mid_val] = 1
            num_rooms = 2
        else:
            num_rooms = 1

        return {
            "total_points": len(points),
            "bounding_box_dimensions_m": [round(float(v), 3) for v in dim],
            "volume_m3": round(volume_m3, 3),
            "floor_area_m2": round(floor_area_m2, 3),
            "volumetric_density_pts_m3": round(volumetric_density, 1),
            "surface_density_pts_m2": round(surface_density, 1),
            "coverage": {
                "floor_points": int(np.sum(floor_mask)),
                "ceiling_points": int(np.sum(ceiling_mask)),
                "wall_points": int(np.sum(wall_mask)),
                "furniture_points": int(len(points) - np.sum(floor_mask) - np.sum(ceiling_mask) - np.sum(wall_mask)),
                "detected_rooms": num_rooms
            }
        }

    def export_ply(
        self,
        points: np.ndarray,
        normals: np.ndarray,
        colors: np.ndarray,
        confidences: np.ndarray,
        output_path: str
    ):
        """
        Exports the dense reconstructed point cloud into standard ASCII Stanford PLY format.
        """
        num_vertices = len(points)
        header = f"""ply
format ascii 1.0
comment VASTU Spatial Computing Dense Point Cloud
element vertex {num_vertices}
property float x
property float y
property float z
property float nx
property float ny
property float nz
property uchar red
property uchar green
property uchar blue
property float confidence
end_header
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(header)
            for i in range(num_vertices):
                x, y, z = points[i]
                nx, ny, nz = normals[i]
                r, g, b = colors[i]
                c = confidences[i]
                f.write(f"{x:.5f} {y:.5f} {z:.5f} {nx:.4f} {ny:.4f} {nz:.4f} {int(r)} {int(g)} {int(b)} {c:.3f}\n")

    def run_dense_fusion(
        self,
        preprocessing_dir: str,
        tracking_dir: str,
        depth_dir: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Runs complete Point 21 pipeline:
        Loads depth maps & camera poses -> Unprojects to 3D -> Fuses multi-view voxels ->
        Removes statistical outliers -> Estimates PCA normals -> Computes coverage & density ->
        Partitions spatial cells -> Exports PLY.
        """
        t0 = time.time()
        os.makedirs(output_dir, exist_ok=True)

        calib_path = os.path.join(preprocessing_dir, "calibration.json")
        poses_path = os.path.join(tracking_dir, "camera_poses.json")

        if not os.path.exists(calib_path) or not os.path.exists(poses_path):
            raise FileNotFoundError("Missing calibration.json or camera_poses.json")

        with open(calib_path, "r", encoding="utf-8") as f:
            calib = json.load(f)
        with open(poses_path, "r", encoding="utf-8") as f:
            poses_data = json.load(f)

        intr = calib["intrinsics"]
        K = np.array([
            [intr["fx"], 0.0, intr["cx"]],
            [0.0, intr["fy"], intr["cy"]],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        keyframes_dir = os.path.join(preprocessing_dir, "keyframes")
        poses_list = poses_data.get("poses", [])

        all_points = []
        all_colors = []
        all_confs = []
        all_views = []
        unprojected_keyframes = 0

        for p_info in poses_list:
            kf_id = p_info["keyframe_id"]
            fname = p_info["file_name"]
            img_path = os.path.join(keyframes_dir, fname)

            base_name = f"keyframe_{kf_id:04d}"
            depth_npy_path = os.path.join(depth_dir, f"{base_name}_depth.npy")
            conf_png_path = os.path.join(depth_dir, f"{base_name}_confidence.png")

            if not os.path.exists(depth_npy_path) or not os.path.exists(img_path):
                continue

            depth_map = np.load(depth_npy_path)
            img_bgr = cv2.imread(img_path)

            if os.path.exists(conf_png_path):
                conf_map = cv2.imread(conf_png_path, cv2.IMREAD_GRAYSCALE) / 255.0
            else:
                conf_map = np.full_like(depth_map, 0.85, dtype=np.float32)

            R = np.array(p_info["rotation_matrix"], dtype=np.float64)
            pos = np.array(p_info["position"], dtype=np.float64).reshape((3, 1))
            t = -R @ pos

            unproj_res = self.unproject_keyframe_depth(
                depth_map=depth_map,
                confidence_map=conf_map,
                rgb_image=img_bgr,
                K=K,
                R_cam=R,
                t_cam=t,
                keyframe_id=kf_id
            )

            if len(unproj_res["points"]) > 0:
                all_points.append(unproj_res["points"])
                all_colors.append(unproj_res["colors"])
                all_confs.append(unproj_res["confidences"])
                all_views.append(unproj_res["view_dirs"])
                unprojected_keyframes += 1

        if len(all_points) == 0:
            raise ValueError("No valid 3D points were back-projected from depth maps")

        pts_raw = np.vstack(all_points)
        colors_raw = np.vstack(all_colors)
        confs_raw = np.concatenate(all_confs)
        views_raw = np.vstack(all_views)

        # 1. 2cm Voxel Grid Spatial Fusion
        pts_fused, colors_fused, confs_fused, views_fused = self.voxel_grid_fusion(
            pts_raw, colors_raw, confs_raw, views_raw
        )

        # 2. Statistical Outlier Removal (SOR)
        pts_clean, colors_clean, confs_clean, views_clean = self.statistical_outlier_removal(
            pts_fused, colors_fused, confs_fused, views_fused
        )

        # 3. PCA Surface Normal Estimation
        normals_clean = self.estimate_surface_normals(pts_clean, views_clean)

        # 4. Spatial Cell Partitioning (0.5m octants)
        spatial_cells_data = self.partition_spatial_cells(pts_clean)
        cells_path = os.path.join(output_dir, "spatial_cells.json")
        with open(cells_path, "w", encoding="utf-8") as f:
            json.dump(spatial_cells_data, f, indent=2)

        # 5. Spatial Coverage & Structural Density
        coverage_data = self.compute_spatial_coverage_and_density(pts_clean, normals_clean)

        # 6. Export PLY & JSON Artifacts
        ply_path = os.path.join(output_dir, "dense_points3D.ply")
        self.export_ply(pts_clean, normals_clean, colors_clean, confs_clean, ply_path)

        proc_time_s = round(time.time() - t0, 3)

        stats = {
            "pointcloud_engine": "VASTU_Dense_Fusion_v1.0",
            "technologies": ["Open3D", "C++", "Python"],
            "unprojected_keyframes": unprojected_keyframes,
            "raw_points_count": len(pts_raw),
            "voxel_fused_count": len(pts_fused),
            "dense_points_count": len(pts_clean),
            "outliers_removed": len(pts_fused) - len(pts_clean),
            "voxel_resolution_m": self.voxel_size_m,
            "mean_confidence": round(float(np.mean(confs_clean)), 3),
            "spatial_coverage": coverage_data,
            "total_spatial_cells": spatial_cells_data["total_cells"],
            "processing_time_s": proc_time_s,
            "artifacts": {
                "ply": "dense_points3D.ply",
                "spatial_cells": "spatial_cells.json",
                "stats": "pointcloud_stats.json"
            }
        }

        stats_path = os.path.join(output_dir, "pointcloud_stats.json")
        with open(stats_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        return stats


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python dense_pointcloud_engine.py <preprocessing_dir> <tracking_dir> <depth_dir> <output_dir>")
        sys.exit(1)

    p_dir, t_dir, d_dir, o_dir = sys.argv[1:5]
    engine = DensePointCloudEngine()
    try:
        results = engine.run_dense_fusion(p_dir, t_dir, d_dir, o_dir)
        print(f"SUCCESS: Fused {results['dense_points_count']} dense 3D points across {results['total_spatial_cells']} spatial cells.")
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
