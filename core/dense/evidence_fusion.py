"""
VĀSTU Dense Reconstruction: Evidence Point Cloud Fusion
Integrates consistent depth measurements into a dense evidence point cloud representation.
Tracks point confidence, density maps, and observation provenance for full traceability.
"""

import os
import json
import numpy as np
import logging
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("vastu.dense.fusion")


class DenseEvidencePoint:
    """Individual 3D point with confidence and source observation traceability."""
    def __init__(
        self,
        position: np.ndarray,      # [x, y, z] in world meters
        color: np.ndarray,         # [r, g, b] uint8
        normal: np.ndarray,        # [nx, ny, nz]
        confidence: float,         # [0.0, 1.0]
        source_frames: List[int]   # list of frame indices observing this point
    ):
        self.position = position
        self.color = color
        self.normal = normal
        self.confidence = confidence
        self.source_frames = source_frames


class DenseEvidenceFusion:
    """
    Fuses multi-view verified depth observations into a traceable 3D evidence representation.
    """
    def __init__(self, voxel_size_m: float = 0.03):
        self.voxel_size_m = voxel_size_m

    def fuse_views(
        self,
        keyframe_records: List[Dict[str, Any]],
        consistent_depths: List[np.ndarray],
        consensus_maps: List[np.ndarray],
        point_sources_list: List[Dict[Tuple[int, int], List[int]]],
        rgb_images: List[np.ndarray],
        poses_trajectory: List[Dict[str, Any]],
        K: np.ndarray,
        step: int = 4
    ) -> List[DenseEvidencePoint]:
        """
        Unprojects and fuses multi-view consistent points into world space.
        """
        K_inv = np.linalg.inv(K)
        fx = K[0, 0]
        fy = K[1, 1]
        cx = K[0, 2]
        cy = K[1, 2]

        fused_raw_points: List[DenseEvidencePoint] = []
        pose_by_frame = {p["frame_index"]: p for p in poses_trajectory}

        for idx, kf in enumerate(keyframe_records):
            f_idx = kf["frame_index"]
            if f_idx not in pose_by_frame:
                continue

            depth_map = consistent_depths[idx]
            consensus_map = consensus_maps[idx]
            point_sources = point_sources_list[idx]
            rgb = rgb_images[idx]
            pose = pose_by_frame[f_idx]

            R = np.array(pose["R"], dtype=np.float64)
            t = np.array(pose["t"], dtype=np.float64).reshape(3, 1)

            h, w = depth_map.shape
            u_coords, v_coords = np.meshgrid(
                np.arange(0, w, step),
                np.arange(0, h, step)
            )
            u_flat = u_coords.ravel()
            v_flat = v_coords.ravel()
            z_flat = depth_map[v_flat, u_flat]

            valid = (z_flat > 0.3) & (z_flat < 8.0) & np.isfinite(z_flat)
            u_val = u_flat[valid]
            v_val = v_flat[valid]
            z_val = z_flat[valid]

            if len(z_val) == 0:
                continue

            # Camera coordinates
            x_cam = (u_val - cx) * z_val / fx
            y_cam = (v_val - cy) * z_val / fy
            pts_cam = np.column_stack([x_cam, y_cam, z_val])

            # World coordinates: X_w = R.T @ (pts_cam.T - t)
            pts_w = (R.T @ (pts_cam.T - t)).T

            # Camera forward ray in world space for approximate normal
            view_dir = (R.T @ np.array([[0], [0], [-1]])).flatten()
            norm_unit = view_dir / np.linalg.norm(view_dir)

            cols = rgb[v_val, u_val]

            for pt_idx in range(len(u_val)):
                u = int(u_val[pt_idx])
                v = int(v_val[pt_idx])
                n_consensus = int(consensus_map[v, u])
                agreeing = point_sources.get((u, v), [])
                all_sources = sorted(list(set([f_idx] + agreeing)))

                # Confidence calculation based on view consensus count and depth range
                depth_penalty = max(0.0, 1.0 - (z_val[pt_idx] / 8.0) * 0.3)
                conf = min(1.0, max(0.1, (n_consensus / 3.0) * 0.7 * depth_penalty + 0.3))

                point = DenseEvidencePoint(
                    position=pts_w[pt_idx],
                    color=cols[pt_idx],
                    normal=norm_unit,
                    confidence=round(conf, 3),
                    source_frames=all_sources
                )
                fused_raw_points.append(point)

        # Spatial Hash Deduplication with Observation Provenance Union
        voxel_map: Dict[Tuple[int, int, int], DenseEvidencePoint] = {}
        inv_v = 1.0 / self.voxel_size_m

        for pt in fused_raw_points:
            vx = int(np.floor(pt.position[0] * inv_v))
            vy = int(np.floor(pt.position[1] * inv_v))
            vz = int(np.floor(pt.position[2] * inv_v))
            key = (vx, vy, vz)

            if key not in voxel_map:
                voxel_map[key] = pt
            else:
                existing = voxel_map[key]
                # Union source observations for complete traceability
                combined_sources = sorted(list(set(existing.source_frames + pt.source_frames)))
                existing.source_frames = combined_sources
                # Retain highest confidence
                if pt.confidence > existing.confidence:
                    existing.confidence = pt.confidence
                    existing.position = (existing.position + pt.position) / 2.0
                    existing.color = pt.color

        deduped_points = list(voxel_map.values())
        logger.info(f"Dense Evidence Fusion: {len(fused_raw_points)} raw points fused into {len(deduped_points)} voxel-deduped points")
        return deduped_points

    def compute_density_map(
        self,
        points: List[DenseEvidencePoint],
        cell_size_m: float = 0.50
    ) -> Dict[str, Any]:
        """
        Computes spatial volumetric density (points/m^3) across 3D cells.
        """
        if not points:
            return {"mean_density_pts_m3": 0.0, "total_occupied_cells": 0, "cells": []}

        coords = np.array([p.position for p in points])
        min_bound = np.min(coords, axis=0)
        max_bound = np.max(coords, axis=0)

        cell_vol = cell_size_m ** 3
        inv_c = 1.0 / cell_size_m

        grid_counts: Dict[Tuple[int, int, int], int] = {}
        for pos in coords:
            cx = int(np.floor(pos[0] * inv_c))
            cy = int(np.floor(pos[1] * inv_c))
            cz = int(np.floor(pos[2] * inv_c))
            key = (cx, cy, cz)
            grid_counts[key] = grid_counts.get(key, 0) + 1

        densities = [count / cell_vol for count in grid_counts.values()]
        mean_density = float(np.mean(densities)) if densities else 0.0

        return {
            "bounding_box_min": min_bound.tolist(),
            "bounding_box_max": max_bound.tolist(),
            "cell_size_m": cell_size_m,
            "total_occupied_cells": len(grid_counts),
            "mean_density_pts_m3": round(mean_density, 1),
            "max_density_pts_m3": round(float(np.max(densities)), 1) if densities else 0.0,
            "min_density_pts_m3": round(float(np.min(densities)), 1) if densities else 0.0
        }

    def write_ply(self, points: List[DenseEvidencePoint], output_ply_path: str):
        """
        Serializes evidence point cloud to standard ASCII PLY with confidence
        and primary source observation attributes.
        """
        os.makedirs(os.path.dirname(os.path.abspath(output_ply_path)), exist_ok=True)
        n = len(points)
        with open(output_ply_path, "w") as f:
            f.write("ply\nformat ascii 1.0\n")
            f.write(f"element vertex {n}\n")
            f.write("property float x\nproperty float y\nproperty float z\n")
            f.write("property uchar red\nproperty uchar green\nproperty uchar blue\n")
            f.write("property float nx\nproperty float ny\nproperty float nz\n")
            f.write("property float confidence\n")
            f.write("property int primary_source_frame\n")
            f.write("end_header\n")
            for p in points:
                px, py, pz = p.position
                r, g, b = p.color
                nx, ny, nz = p.normal
                conf = p.confidence
                src = p.source_frames[0] if p.source_frames else 0
                f.write(f"{px:.4f} {py:.4f} {pz:.4f} {int(r)} {int(g)} {int(b)} {nx:.3f} {ny:.3f} {nz:.3f} {conf:.3f} {src}\n")
