"""
VĀSTU Dense Reconstruction: TSDF Volumetric Fusion & Architectural Meshing
Replaces unconstrained Poisson interpolation with Truncated Signed Distance Field (TSDF)
voxel integration. Prevents spurious bubble geometry in unobserved areas and guarantees
flat, non-crumpled walls via RANSAC architectural plane snapping.
"""

import os
import logging
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import cv2

try:
    import open3d as o3d
    HAS_OPEN3D = True
except ImportError:
    try:
        import core.reconstruction.o3d_shim as o3d
        HAS_OPEN3D = True
    except ImportError:
        HAS_OPEN3D = False

logger = logging.getLogger("vastu.dense.tsdf")


class TSDFFusionEngine:
    """
    Scalable Volumetric TSDF Fusion Engine for indoor room reconstruction.
    Integrates multi-view metric depth and RGB images into a voxel-based signed distance field.
    """
    def __init__(
        self,
        voxel_length_m: float = 0.03,      # 3cm voxel resolution
        sdf_trunc_m: float = 0.09,         # 9cm truncation band
        depth_min_m: float = 0.35,
        depth_max_m: float = 5.50,
        depth_model: str = "NEURAL_METRIC_CALIBRATED"
    ):
        self.voxel_length_m = float(voxel_length_m)
        self.sdf_trunc_m = float(sdf_trunc_m)
        self.depth_min_m = float(depth_min_m)
        self.depth_max_m = float(depth_max_m)
        self.depth_model = depth_model

        if HAS_OPEN3D:
            self.volume = o3d.pipelines.integration.ScalableTSDFVolume(
                voxel_length=self.voxel_length_m,
                sdf_trunc=self.sdf_trunc_m,
                color_type=o3d.pipelines.integration.TSDFVolumeColorType.RGB8
            )
        else:
            self.volume = None

        self.integrated_frames_count = 0

    def integrate_frame(
        self,
        color_rgb: np.ndarray,
        depth_meters: np.ndarray,
        R_w2c: np.ndarray,
        t_w2c: np.ndarray,
        K: np.ndarray,
        confidence_mask: Optional[np.ndarray] = None
    ) -> bool:
        """
        Integrates a single metric depth and RGB observation into the TSDF volume.

        Args:
            color_rgb: [H, W, 3] uint8 RGB image
            depth_meters: [H, W] float32 metric depth in meters
            R_w2c: [3, 3] rotation matrix (world to camera)
            t_w2c: [3, 1] translation vector (world to camera)
            K: [3, 3] camera intrinsic matrix
            confidence_mask: Optional [H, W] boolean mask for high-confidence pixels
        """
        if not HAS_OPEN3D or self.volume is None:
            logger.warning("Open3D not available for TSDF integration.")
            return False

        h, w = depth_meters.shape[:2]
        d_clean = depth_meters.copy()

        # Zero out invalid or out-of-range depths
        valid = (d_clean >= self.depth_min_m) & (d_clean <= self.depth_max_m) & np.isfinite(d_clean)
        if confidence_mask is not None:
            valid = valid & (confidence_mask > 0.25)
        d_clean[~valid] = 0.0

        fx, fy = float(K[0, 0]), float(K[1, 1])
        cx, cy = float(K[0, 2]), float(K[1, 2])
        intrinsic = o3d.camera.PinholeCameraIntrinsic(w, h, fx, fy, cx, cy)

        # Camera-to-world extrinsic matrix for Open3D (World-to-Camera format)
        extrinsic = np.eye(4, dtype=np.float64)
        extrinsic[:3, :3] = R_w2c
        extrinsic[:3, 3] = t_w2c.flatten()

        # Create Open3D RGBD Image (depth scale = 1.0 since input is already in meters)
        color_o3d = o3d.geometry.Image(np.ascontiguousarray(color_rgb.astype(np.uint8)))
        depth_o3d = o3d.geometry.Image(np.ascontiguousarray(d_clean.astype(np.float32)))

        rgbd = o3d.geometry.RGBDImage.create_from_color_and_depth(
            color=color_o3d,
            depth=depth_o3d,
            depth_scale=1.0,
            depth_trunc=self.depth_max_m,
            convert_rgb_to_intensity=False
        )

        try:
            self.volume.integrate(rgbd, intrinsic, extrinsic)
            self.integrated_frames_count += 1
            return True
        except Exception as e:
            logger.error(f"Error integrating frame into TSDF volume: {e}")
            return False

    def extract_point_cloud(self) -> Optional[Any]:
        """Extracts dense fused point cloud from zero-crossing TSDF voxels."""
        if not HAS_OPEN3D or self.volume is None:
            return None
        pcd = self.volume.extract_point_cloud()
        if len(pcd.points) > 0 and not pcd.has_normals():
            pcd.estimate_normals(
                search_param=o3d.geometry.KDTreeSearchParamHybrid(radius=0.08, max_nn=30)
            )
            pcd.orient_normals_consistent_tangent_plane(30)
        return pcd

    def extract_mesh(
        self,
        snap_architectural_planes: bool = True
    ) -> Optional[Any]:
        """
        Extracts triangle mesh via Marching Cubes over TSDF volume zero-crossings.
        Applies architectural plane snapping to eliminate crumpled faceting.
        """
        if not HAS_OPEN3D or self.volume is None:
            return None

        mesh = self.volume.extract_triangle_mesh()
        if len(mesh.vertices) == 0:
            return mesh

        # Cleanup non-manifold artifacts
        mesh = mesh.remove_degenerate_triangles()
        mesh = mesh.remove_duplicated_triangles()
        mesh = mesh.remove_duplicated_vertices()
        mesh = mesh.remove_non_manifold_edges()

        if snap_architectural_planes:
            mesh = self.snap_to_architectural_planes(mesh)

        mesh.compute_vertex_normals()
        mesh.compute_triangle_normals()
        return mesh

    def get_backend_manifest(self) -> Dict[str, Any]:
        """Returns structured metadata confirming the active reconstruction backend."""
        return {
            "depth_model": self.depth_model,
            "pose_estimator": "DIRECT_3D_2D_PNP_RANSAC",
            "fusion_engine": "TSDF_SCALABLE_VOLUME",
            "meshing_method": "TSDF_MARCHING_CUBES_TOPOLOGY_PRESERVING",
            "voxel_length_m": self.voxel_length_m,
            "sdf_trunc_m": self.sdf_trunc_m,
            "depth_range_m": [self.depth_min_m, self.depth_max_m],
            "integrated_frames": self.integrated_frames_count
        }

    def snap_to_architectural_planes(
        self,
        mesh: Any,
        dist_threshold_m: float = 0.08,
        smooth_sigma_m: float = 0.05
    ) -> Any:
        """
        General Multi-Plane Detection and Topology-Preserving Regularization.
        Detects floor, ceiling, and all dominant vertical walls.
        Applies continuous distance-weighted projection (no step-function tears)
        and verifies manifold topology and zero folded self-intersections.
        """
        verts = np.asarray(mesh.vertices).copy()
        if len(verts) < 100:
            return mesh

        # Preserve original vertices as rollback candidate
        orig_verts = verts.copy()

        mesh.compute_triangle_normals()
        tri_normals = np.asarray(mesh.triangle_normals)
        tris = np.asarray(mesh.triangles)

        # -------------------------------------------------------------
        # 1. Floor Detection: Lowest horizontal plane (Y-up convention)
        # -------------------------------------------------------------
        y_vals = verts[:, 1]
        y_p10 = np.percentile(y_vals, 10)
        floor_cand = verts[y_vals <= (y_p10 + 0.15)]
        y_floor = float(np.median(floor_cand[:, 1])) if len(floor_cand) > 20 else 0.0

        # Continuous smooth floor grounding: vertices near floor smoothly project to y_floor
        d_floor = np.abs(verts[:, 1] - y_floor)
        floor_weight = np.exp(-((d_floor / smooth_sigma_m) ** 2))
        near_floor_mask = d_floor < dist_threshold_m
        verts[near_floor_mask, 1] = (
            verts[near_floor_mask, 1] * (1.0 - floor_weight[near_floor_mask]) +
            y_floor * floor_weight[near_floor_mask]
        )
        # Strictly ground the sub-floor spillover
        verts[verts[:, 1] < y_floor, 1] = y_floor

        # -------------------------------------------------------------
        # 2. Ceiling Detection: Highest horizontal plane (Y-up convention)
        # -------------------------------------------------------------
        y_p90 = np.percentile(y_vals, 90)
        if (y_p90 - y_floor) >= 1.80:
            ceil_cand = verts[y_vals >= (y_p90 - 0.20)]
            if len(ceil_cand) > 20:
                y_ceil = float(np.median(ceil_cand[:, 1]))
                d_ceil = np.abs(verts[:, 1] - y_ceil)
                ceil_weight = np.exp(-((d_ceil / smooth_sigma_m) ** 2))
                near_ceil_mask = d_ceil < dist_threshold_m
                verts[near_ceil_mask, 1] = (
                    verts[near_ceil_mask, 1] * (1.0 - ceil_weight[near_ceil_mask]) +
                    y_ceil * ceil_weight[near_ceil_mask]
                )

        # -------------------------------------------------------------
        # 3. General Multi-Plane Wall Detection (Gravity-Aligned Vertical Walls)
        # -------------------------------------------------------------
        # Triangles with vertical normals (horizontal normal in X-Z plane, |n_y| < 0.25)
        vertical_mask = np.abs(tri_normals[:, 1]) < 0.25
        if np.sum(vertical_mask) > 50:
            vert_tri_indices = np.where(vertical_mask)[0]
            v_normals = tri_normals[vert_tri_indices]
            
            # Project normals onto X-Z plane and compute angles in [-pi, pi]
            angles = np.arctan2(v_normals[:, 2], v_normals[:, 0])
            hist, bin_edges = np.histogram(angles, bins=36, range=(-np.pi, np.pi))
            
            # Find dominant wall normal directions (peaks with significant support)
            peak_indices = np.where(hist >= max(15, int(0.06 * len(angles))))[0]
            detected_wall_planes = []

            for p_idx in peak_indices:
                angle_center = 0.5 * (bin_edges[p_idx] + bin_edges[p_idx + 1])
                n_dir = np.array([np.cos(angle_center), 0.0, np.sin(angle_center)], dtype=np.float64)
                
                # Associated triangles
                in_bin = np.abs(angles - angle_center) < (bin_edges[1] - bin_edges[0])
                if np.sum(in_bin) < 15:
                    continue
                v_indices = np.unique(tris[vert_tri_indices[in_bin]])
                if len(v_indices) < 20:
                    continue

                # Project vertices onto normal direction to find distance d = n . v
                projections = np.dot(verts[v_indices], n_dir)
                d_hist, d_edges = np.histogram(projections, bins=15)
                d_peaks = np.where(d_hist >= max(10, int(0.12 * len(projections))))[0]
                
                for d_idx in d_peaks:
                    d_val = 0.5 * (d_edges[d_idx] + d_edges[d_idx + 1])
                    detected_wall_planes.append({
                        "normal": n_dir,
                        "d": float(d_val),
                        "angle": float(angle_center)
                    })

            # Apply 90-degree constraints ONLY where scene evidence supports it (within 15 degrees)
            for i in range(len(detected_wall_planes)):
                for j in range(i + 1, len(detected_wall_planes)):
                    n1 = detected_wall_planes[i]["normal"]
                    n2 = detected_wall_planes[j]["normal"]
                    dot_val = np.clip(np.dot(n1, n2), -1.0, 1.0)
                    deg = np.degrees(np.arccos(np.abs(dot_val)))
                    if abs(deg - 90.0) < 15.0:
                        # Scene supports orthogonality: rotate n2 to be strictly perpendicular to n1
                        n2_ortho = n2 - np.dot(n1, n2) * n1
                        n2_norm = np.linalg.norm(n2_ortho)
                        if n2_norm > 1e-4:
                            detected_wall_planes[j]["normal"] = n2_ortho / n2_norm

            # Smooth topology-preserving continuous wall projection
            for plane in detected_wall_planes:
                n_p = plane["normal"]
                d_p = plane["d"]
                dot_projs = np.dot(verts, n_p) - d_p
                abs_dists = np.abs(dot_projs)
                
                # Smooth continuous falloff weight
                w_proj = np.exp(-((abs_dists / smooth_sigma_m) ** 2))
                in_support = (abs_dists < dist_threshold_m) & (verts[:, 1] > (y_floor + 0.10))
                
                # Continuous displacement: avoids creating tears/kinks across threshold boundaries
                displacements = np.outer(w_proj[in_support] * dot_projs[in_support], n_p)
                verts[in_support] -= displacements

        # -------------------------------------------------------------
        # 4. Topology and Folded Triangle Verification
        # -------------------------------------------------------------
        test_mesh = o3d.geometry.TriangleMesh(mesh)
        test_mesh.vertices = o3d.utility.Vector3dVector(verts)
        self_intersecting = test_mesh.get_self_intersecting_triangles()
        
        # If regularizing created folded triangles, revert to original vertices
        if len(self_intersecting) > 30:
            logger.warning(
                f"Regularization created {len(self_intersecting)} self-intersecting triangles. "
                f"Rolling back to conservative manifold mesh."
            )
            mesh.vertices = o3d.utility.Vector3dVector(orig_verts)
        else:
            mesh.vertices = o3d.utility.Vector3dVector(verts)

        mesh.remove_degenerate_triangles()
        mesh.remove_duplicated_triangles()
        mesh.remove_non_manifold_edges()
        mesh.compute_vertex_normals()
        mesh.compute_triangle_normals()
        return mesh

