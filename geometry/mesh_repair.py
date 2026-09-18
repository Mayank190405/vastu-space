"""
VĀSTU Pure Geometry Engine: Mesh Cleaning & Repair
Provides manifold verification, component filtering, and Poisson low-density artifact pruning.
"""

from typing import Tuple, Dict, Any
import numpy as np

def filter_mesh_density_threshold(
    vertices: np.ndarray,
    triangles: np.ndarray,
    densities: np.ndarray,
    quantile: float = 0.05
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Prunes low-density vertices from Poisson surface reconstruction artifacts.
    """
    if len(densities) == 0:
        return vertices, triangles

    thresh = float(np.quantile(densities, quantile))
    keep_mask = densities >= thresh

    # Remap vertices and triangles
    new_indices = np.full(len(vertices), -1, dtype=int)
    new_indices[keep_mask] = np.arange(np.sum(keep_mask))

    clean_verts = vertices[keep_mask]
    t_valid = np.all(keep_mask[triangles], axis=1)
    clean_tris = new_indices[triangles[t_valid]]

    return clean_verts, clean_tris

def validate_manifold_mesh(vertices: np.ndarray, triangles: np.ndarray) -> Dict[str, Any]:
    """
    Evaluates topological watertightness and non-manifold edges.
    """
    edge_counts: Dict[Tuple[int, int], int] = {}
    for tri in triangles:
        for i in range(3):
            u, v = int(tri[i]), int(tri[(i + 1) % 3])
            edge = (min(u, v), max(u, v))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1

    boundary_edges = sum(1 for c in edge_counts.values() if c == 1)
    non_manifold_edges = sum(1 for c in edge_counts.values() if c > 2)

    is_watertight = (boundary_edges == 0 and non_manifold_edges == 0)
    return {
        "vertex_count": len(vertices),
        "triangle_count": len(triangles),
        "boundary_edges": boundary_edges,
        "non_manifold_edges": non_manifold_edges,
        "is_watertight": is_watertight,
    }
