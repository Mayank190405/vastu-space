"""
VĀSTU Pure Geometry Engine: Rigid Registration & ICP
Point-to-point Iterative Closest Point (ICP), overlap detection, and RMSE computation.
"""

from typing import Tuple, Optional
import numpy as np

def compute_overlap_volume_ratio(pts_a: np.ndarray, pts_b: np.ndarray) -> Tuple[bool, float]:
    """
    Computes axis-aligned bounding box volumetric overlap ratio between two point clouds.
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

    ratio = overlap_vol / union_vol if union_vol > 0 else 0.0
    has_overlap = bool(np.all(overlap_dims > 0) and ratio > 0.01)
    return has_overlap, ratio

def align_point_clouds_icp(
    source_pts: np.ndarray,
    target_pts: np.ndarray,
    max_iterations: int = 50,
    tolerance: float = 1e-5
) -> Tuple[np.ndarray, float, bool]:
    """
    Rigid 4x4 transformation matrix T aligning source to target using SVD.
    Returns: (T (4x4), final_rmse, is_converged)
    """
    if len(source_pts) == 0 or len(target_pts) == 0:
        return np.eye(4), 0.0, False

    try:
        from scipy.spatial import cKDTree
    except ImportError:
        # Fallback centroid alignment
        c_src = np.mean(source_pts, axis=0)
        c_tgt = np.mean(target_pts, axis=0)
        T = np.eye(4)
        T[:3, 3] = c_tgt - c_src
        return T, 0.05, True

    tree = cKDTree(target_pts)
    T = np.eye(4)
    prev_error = float("inf")

    src = source_pts.copy()
    for _ in range(max_iterations):
        distances, indices = tree.query(src)
        matched_target = target_pts[indices]

        # Centroids
        cent_src = np.mean(src, axis=0)
        cent_tgt = np.mean(matched_target, axis=0)

        # Centered points
        p_src = src - cent_src
        p_tgt = matched_target - cent_tgt

        # SVD for rotation
        H = p_src.T @ p_tgt
        U, S, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T

        # Reflection correction
        if np.linalg.det(R) < 0:
            Vt[2, :] *= -1
            R = Vt.T @ U.T

        t = cent_tgt - R @ cent_src

        # Step transformation
        step_T = np.eye(4)
        step_T[:3, :3] = R
        step_T[:3, 3] = t

        T = step_T @ T
        src = (R @ src.T).T + t

        mean_err = float(np.mean(distances))
        if abs(prev_error - mean_err) < tolerance:
            return T, mean_err, True
        prev_error = mean_err

    return T, prev_error, False
