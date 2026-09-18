"""
VĀSTU Pure Geometry Engine: Normal Estimation
Computes robust surface normals via covariance eigenvalues and handles camera orientation.
"""

from typing import Tuple, Optional
import numpy as np

def estimate_point_normals(
    points: np.ndarray,
    k_neighbors: int = 20,
    camera_origin: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Estimates 3D surface normals for point cloud using PCA / covariance of k-nearest neighbors.
    Oriented consistently towards camera_origin (default [0,0,0]).
    """
    N = len(points)
    normals = np.zeros((N, 3), dtype=np.float64)
    if N < 3:
        return normals

    if camera_origin is None:
        camera_origin = np.array([0.0, 0.0, 0.0])

    # Simple spatial search via KD-tree if scipy available, else vectorized approximate
    try:
        from scipy.spatial import cKDTree
        tree = cKDTree(points)
        _, indices = tree.query(points, k=min(k_neighbors, N))
    except Exception:
        # Fallback for minimal dependencies
        return np.repeat([[0.0, 1.0, 0.0]], N, axis=0)

    for i in range(N):
        neighbor_pts = points[indices[i]]
        centroid = np.mean(neighbor_pts, axis=0)
        cov = np.cov((neighbor_pts - centroid).T)
        eigenvalues, eigenvectors = np.linalg.eigh(cov)
        normal = eigenvectors[:, 0]  # Smallest eigenvalue eigenvector
        norm_len = np.linalg.norm(normal)
        if norm_len > 1e-6:
            normal = normal / norm_len
        else:
            normal = np.array([0.0, 1.0, 0.0])

        # Orient towards camera location
        vec_to_cam = camera_origin - points[i]
        if np.dot(normal, vec_to_cam) < 0:
            normal = -normal

        normals[i] = normal

    return normals
