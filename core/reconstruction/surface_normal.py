"""
VĀSTU Surface Normal Pipeline (Phase 8)
Estimates high-accuracy 3D surface normals from calibrated metric depth maps (DSINE principles).
Classifies structural plane types: FLOOR, CEILING, WALL, and INTERIOR FEATURES.
"""

import logging
from typing import Dict, Any, Tuple
import numpy as np
import cv2

logger = logging.getLogger("vastu.reconstruction.surface_normal")


class SurfaceNormalPipeline:
    """
    Computes per-pixel 3D surface normal vectors from metric depth and camera intrinsics.
    Enforces metric orthogonality for indoor architectural geometry.
    """

    def __init__(self, vertical_threshold_deg: float = 15.0, smoothing_radius: int = 3):
        self.vertical_threshold_cos = np.cos(np.radians(vertical_threshold_deg))
        self.smoothing_radius = smoothing_radius

    def compute_surface_normals(
        self,
        metric_depth: np.ndarray,
        intrinsics: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Computes 3D surface normal map [H, W, 3] from metric depth.
        
        Args:
            metric_depth: 2D float32 array in meters.
            intrinsics: Dict containing fx, fy, cx, cy.
            
        Returns:
            Dict containing:
                - normals: [H, W, 3] float32 unit vectors.
                - wall_mask: boolean mask of vertical surfaces.
                - floor_mask: boolean mask of upward-facing horizontal surfaces.
                - ceiling_mask: boolean mask of downward-facing horizontal surfaces.
        """
        h, w = metric_depth.shape
        fx = intrinsics.get("fx", 1450.0)
        fy = intrinsics.get("fy", 1450.0)
        cx = intrinsics.get("cx", w / 2.0)
        cy = intrinsics.get("cy", h / 2.0)

        # Smooth depth slightly to suppress discretization noise while keeping edges sharp
        smoothed_depth = cv2.bilateralFilter(metric_depth, 5, 0.1, 5)

        # 1. Backproject depth to 3D camera coordinate space
        y_grid, x_grid = np.mgrid[0:h, 0:w].astype(np.float32)
        X = (x_grid - cx) * smoothed_depth / fx
        Y = (y_grid - cy) * smoothed_depth / fy
        Z = smoothed_depth

        # 2. Compute 3D surface tangent vectors via central differences
        dX_dx = np.zeros_like(X)
        dX_dy = np.zeros_like(X)
        dY_dx = np.zeros_like(Y)
        dY_dy = np.zeros_like(Y)
        dZ_dx = np.zeros_like(Z)
        dZ_dy = np.zeros_like(Z)

        dX_dx[:, 1:-1] = (X[:, 2:] - X[:, :-2]) * 0.5
        dY_dx[:, 1:-1] = (Y[:, 2:] - Y[:, :-2]) * 0.5
        dZ_dx[:, 1:-1] = (Z[:, 2:] - Z[:, :-2]) * 0.5

        dX_dy[1:-1, :] = (X[2:, :] - X[:-2, :]) * 0.5
        dY_dy[1:-1, :] = (Y[2:, :] - Y[:-2, :]) * 0.5
        dZ_dy[1:-1, :] = (Z[2:, :] - Z[:-2, :]) * 0.5

        # Tangents: T_x = [dX_dx, dY_dx, dZ_dx], T_y = [dX_dy, dY_dy, dZ_dy]
        # Normal = T_x cross T_y
        Nx = dY_dx * dZ_dy - dZ_dx * dY_dy
        Ny = dZ_dx * dX_dy - dX_dx * dZ_dy
        Nz = dX_dx * dY_dy - dY_dx * dX_dy

        norm = np.sqrt(Nx**2 + Ny**2 + Nz**2) + 1e-7
        normals = np.stack([Nx / norm, Ny / norm, Nz / norm], axis=-1).astype(np.float32)

        # In camera frame: Y is down, Z is forward.
        # Vertical wall: Ny is small (|Ny| < sin(15°) ~ 0.25).
        # Floor: Ny is negative / upward normal in world frame.
        wall_mask = np.abs(normals[:, :, 1]) < 0.25
        floor_mask = normals[:, :, 1] < -0.70
        ceiling_mask = normals[:, :, 1] > 0.70

        return {
            "normals": normals,
            "wall_mask": wall_mask,
            "floor_mask": floor_mask,
            "ceiling_mask": ceiling_mask,
            "mean_wall_ratio": float(np.mean(wall_mask)),
            "mean_floor_ratio": float(np.mean(floor_mask))
        }

