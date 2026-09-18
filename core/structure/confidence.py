"""
Architectural Plane Confidence Estimator: Computes measurable plane confidence [0.0, 1.0].
"""

from typing import Optional
import numpy as np

class PlaneConfidenceEstimator:
    def __init__(
        self,
        min_inliers_expected: int = 50,
        rmse_scale_m: float = 0.03,
        min_aspect_ratio: float = 0.05
    ):
        self.min_inliers_expected = min_inliers_expected
        self.rmse_scale_m = rmse_scale_m
        self.min_aspect_ratio = min_aspect_ratio

    def compute_confidence(
        self,
        points: np.ndarray,
        plane_equation: np.ndarray,
        point_normals: Optional[np.ndarray] = None
    ) -> float:
        """
        Computes multi-factor plane confidence in [0.0, 1.0].
        Args:
            points: (N, 3) inlier 3D points
            plane_equation: [a, b, c, d] where ax + by + cz + d = 0
            point_normals: Optional (N, 3) surface normals for each inlier point
        """
        N = len(points)
        if N < 3:
            return 0.0

        normal = plane_equation[:3]
        norm_len = np.linalg.norm(normal)
        if norm_len < 1e-6:
            return 0.0
        unit_normal = normal / norm_len
        d = float(plane_equation[3]) / norm_len

        # 1. Inlier count score: asymptotic saturation towards 1.0
        count_score = float(np.tanh(N / (2.0 * self.min_inliers_expected)))

        # 2. Planar fit RMSE score
        distances = np.abs(np.dot(points, unit_normal) + d)
        rmse = float(np.sqrt(np.mean(distances ** 2)))
        rmse_score = float(np.exp(-rmse / max(self.rmse_scale_m, 1e-4)))

        # 3. Normal alignment consistency score
        if point_normals is not None and len(point_normals) == N:
            pt_norms = np.linalg.norm(point_normals, axis=1, keepdims=True)
            valid_mask = (pt_norms.flatten() > 1e-6)
            if np.any(valid_mask):
                unit_pt_normals = point_normals[valid_mask] / pt_norms[valid_mask]
                dot_products = np.abs(np.dot(unit_pt_normals, unit_normal))
                normal_score = float(np.mean(dot_products))
            else:
                normal_score = 0.8
        else:
            normal_score = 0.85  # Neutral default if normals not provided

        # 4. 2D Spatial Spread Score (checking that points form a true 2D surface, not a 1D line)
        # Construct local 2D basis on the plane
        ref_vec = np.array([1.0, 0.0, 0.0]) if abs(unit_normal[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
        u_axis = np.cross(unit_normal, ref_vec)
        u_axis = u_axis / np.linalg.norm(u_axis)
        v_axis = np.cross(unit_normal, u_axis)

        p_centered = points - np.mean(points, axis=0)
        u_coords = np.dot(p_centered, u_axis)
        v_coords = np.dot(p_centered, v_axis)
        coords_2d = np.column_stack([u_coords, v_coords])

        cov_2d = np.cov(coords_2d.T)
        eigvals = np.linalg.eigvalsh(cov_2d)
        lambda_min = max(0.0, float(eigvals[0]))
        lambda_max = max(1e-6, float(eigvals[1]))
        spread_ratio = lambda_min / lambda_max
        spread_score = float(np.clip(spread_ratio / self.min_aspect_ratio, 0.0, 1.0))

        # Multi-factor weighted confidence
        # Inlier count (25%), RMSE fit (35%), normal consistency (25%), 2D spread (15%)
        confidence = (
            0.25 * count_score +
            0.35 * rmse_score +
            0.25 * normal_score +
            0.15 * spread_score
        )

        return float(np.clip(confidence, 0.0, 1.0))
