"""
VĀSTU Pure Geometry Engine Package
"""

from geometry.planes import fit_plane_ransac, compute_dihedral_angle_deg, compute_bounding_box
from geometry.normals import estimate_point_normals
from geometry.spatial_hash import SpatialHashGrid
from geometry.icp import align_point_clouds_icp, compute_overlap_volume_ratio
from geometry.mesh_repair import filter_mesh_density_threshold, validate_manifold_mesh

__all__ = [
    "fit_plane_ransac",
    "compute_dihedral_angle_deg",
    "compute_bounding_box",
    "estimate_point_normals",
    "SpatialHashGrid",
    "align_point_clouds_icp",
    "compute_overlap_volume_ratio",
    "filter_mesh_density_threshold",
    "validate_manifold_mesh",
]
