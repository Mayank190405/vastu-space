"""
VĀSTU Pure Geometry Engine: Plane Fitting & Structural Extraction
Provides robust RANSAC plane fitting, bounding box calculations, and corner line analysis.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np

def fit_plane_ransac(
    points: np.ndarray,
    distance_threshold: float = 0.03,
    ransac_n: int = 3,
    num_iterations: int = 1000
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Fits a plane ax + by + cz + d = 0 using RANSAC.
    Returns:
        plane_model: [a, b, c, d] where norm(a,b,c) == 1.0
        inlier_indices: indices of inlier points
    """
    if len(points) < 3:
        return np.array([0.0, 1.0, 0.0, 0.0]), np.array([], dtype=int)

    best_inliers = []
    best_plane = np.array([0.0, 1.0, 0.0, 0.0])

    N = len(points)
    for _ in range(num_iterations):
        idx = np.random.choice(N, ransac_n, replace=False)
        p1, p2, p3 = points[idx[0]], points[idx[1]], points[idx[2]]

        v1 = p2 - p1
        v2 = p3 - p1
        normal = np.cross(v1, v2)
        norm_len = np.linalg.norm(normal)
        if norm_len < 1e-6:
            continue

        normal = normal / norm_len
        d = -float(np.dot(normal, p1))

        distances = np.abs(np.dot(points, normal) + d)
        inliers = np.where(distances < distance_threshold)[0]

        if len(inliers) > len(best_inliers):
            best_inliers = inliers
            best_plane = np.array([normal[0], normal[1], normal[2], d])

    return best_plane, np.asarray(best_inliers)

def compute_dihedral_angle_deg(normal_a: np.ndarray, normal_b: np.ndarray) -> float:
    """Computes the dihedral angle between two surface normal vectors in degrees."""
    cos_theta = float(np.dot(normal_a, normal_b))
    cos_theta = np.clip(cos_theta, -1.0, 1.0)
    rad = np.arccos(cos_theta)
    return float(np.degrees(rad))

def compute_bounding_box(points: np.ndarray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Returns (min_xyz, max_xyz, center_xyz).
    """
    if len(points) == 0:
        return np.zeros(3), np.zeros(3), np.zeros(3)
    min_xyz = np.min(points, axis=0)
    max_xyz = np.max(points, axis=0)
    center_xyz = (min_xyz + max_xyz) / 2.0
    return min_xyz, max_xyz, center_xyz
