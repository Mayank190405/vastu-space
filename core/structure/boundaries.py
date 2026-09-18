"""
Architectural Plane Boundary Extractor: Computes 2D/3D boundaries, convex hulls, and surface areas.
"""

from typing import Tuple, List
import numpy as np

class PlaneBoundaryExtractor:
    def __init__(self, padding_margin_m: float = 0.02):
        self.padding_margin_m = padding_margin_m

    def extract_boundaries(
        self,
        points: np.ndarray,
        plane_equation: np.ndarray
    ) -> Tuple[List[List[float]], List[List[float]], float]:
        """
        Extracts boundary polygon and 4 principal corners for a plane in 3D.
        Returns:
            corners_3d: 4 corners of oriented bounding box in 3D [p0, p1, p2, p3]
            boundary_polygon_3d: list of 3D points forming the boundary polygon (convex hull)
            surface_area_m2: surface area in square meters
        """
        if len(points) < 3:
            return [], [], 0.0

        normal = plane_equation[:3]
        norm_len = np.linalg.norm(normal)
        if norm_len < 1e-6:
            return [], [], 0.0
        unit_normal = normal / norm_len

        # Construct local orthonormal frame on plane
        centroid = np.mean(points, axis=0)
        ref_vec = np.array([1.0, 0.0, 0.0]) if abs(unit_normal[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u_axis = np.cross(unit_normal, ref_vec)
        u_axis = u_axis / np.linalg.norm(u_axis)
        v_axis = np.cross(unit_normal, u_axis)

        # 2D projection
        diffs = points - centroid
        u_vals = np.dot(diffs, u_axis)
        v_vals = np.dot(diffs, v_axis)
        pts_2d = np.column_stack([u_vals, v_vals])

        # Compute oriented bounding box in 2D
        # Use PCA / covariance of 2D points to find dominant orientation
        cov_2d = np.cov(pts_2d.T)
        eigvals, eigvecs = np.linalg.eigh(cov_2d)
        dir1 = eigvecs[:, 1]  # primary direction
        dir2 = eigvecs[:, 0]  # secondary direction

        proj1 = np.dot(pts_2d, dir1)
        proj2 = np.dot(pts_2d, dir2)

        min1, max1 = float(np.min(proj1)), float(np.max(proj1))
        min2, max2 = float(np.min(proj2)), float(np.max(proj2))

        # 4 corners in 2D PCA frame
        c1_2d = min1 * dir1 + min2 * dir2
        c2_2d = max1 * dir1 + min2 * dir2
        c3_2d = max1 * dir1 + max2 * dir2
        c4_2d = min1 * dir1 + max2 * dir2

        # Convert back to 3D
        def to_3d(p2):
            return (centroid + p2[0] * u_axis + p2[1] * v_axis).tolist()

        corners_3d = [to_3d(c1_2d), to_3d(c2_2d), to_3d(c3_2d), to_3d(c4_2d)]

        # Calculate surface area
        width_m = max1 - min1
        height_m = max2 - min2
        surface_area = float(max(width_m * height_m, 0.01))

        # Calculate convex hull for detailed boundary polygon if scipy available
        try:
            from scipy.spatial import ConvexHull
            hull = ConvexHull(pts_2d)
            hull_pts_2d = pts_2d[hull.vertices]
            boundary_polygon_3d = [to_3d(p) for p in hull_pts_2d]
        except Exception:
            boundary_polygon_3d = corners_3d

        return corners_3d, boundary_polygon_3d, surface_area
