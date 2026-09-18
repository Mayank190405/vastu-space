"""
Phantom Geometry & Floating Surface Pruner:
Detects and removes mirror reflection phantoms, specular ghosting,
and floating surfaces disconnected from the structural room frame.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

class PhantomPruner:
    def __init__(
        self,
        min_plane_area_m2: float = 0.15,
        min_plane_inliers: int = 30,
        max_distance_to_structure_m: float = 0.45
    ):
        self.min_plane_area_m2 = min_plane_area_m2
        self.min_plane_inliers = min_plane_inliers
        self.max_distance_to_structure_m = max_distance_to_structure_m

    def prune_phantom_planes(
        self,
        planes: List[Dict[str, Any]]
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Filters out phantom planes (mirrors, specular reflections, slivers with negligible area).
        """
        valid_planes = []
        corrections = []

        for p in planes:
            p_id = p["structure_id"]
            area = p.get("surface_area_m2", 0.0)
            inliers = p.get("inlier_points_count", 0)
            conf = p.get("confidence", 1.0)
            ptype = p.get("plane_type", "OTHER")

            # Check for phantom / sliver criteria
            is_sliver = (area < self.min_plane_area_m2 and inliers < self.min_plane_inliers)
            is_low_conf_phantom = (conf < 0.25 and ptype == "OTHER")

            if is_sliver or is_low_conf_phantom:
                reason = "Sliver planar artifact" if is_sliver else "Low-confidence reflection phantom"
                corrections.append({
                    "correction_id": f"corr_prune_phantom_{p_id}",
                    "correction_type": "REMOVE_PHANTOM_GEOMETRY",
                    "target_id": p_id,
                    "delta_metric_value": float(round(area, 4)),
                    "delta_metric_unit": "m2",
                    "confidence": conf,
                    "description": f"Pruned phantom geometry '{p_id}' ({reason}, area: {area:.3f}m2, inliers: {inliers})"
                })
            else:
                valid_planes.append(p)

        return valid_planes, corrections

    def prune_floating_points_and_vertices(
        self,
        points: np.ndarray,
        structural_planes: List[Dict[str, Any]]
    ) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
        """
        Removes points or vertices that float disconnected in space without proximity to any structural plane.
        """
        corrections = []
        N = len(points)
        if N == 0 or len(structural_planes) == 0:
            return points, corrections

        # Compute minimum distance of each point to any structural plane
        min_distances = np.full(N, np.inf)

        for p in structural_planes:
            eq = np.array(p["plane_equation"] if isinstance(p["plane_equation"], list) else [
                p["plane_equation"].a, p["plane_equation"].b, p["plane_equation"].c, p["plane_equation"].d
            ])
            n = eq[:3] / (np.linalg.norm(eq[:3]) + 1e-9)
            d = eq[3] / (np.linalg.norm(eq[:3]) + 1e-9)
            dist_to_plane = np.abs(np.dot(points, n) + d)
            min_distances = np.minimum(min_distances, dist_to_plane)

        # Mask points that are too far from all structural planes (floating geometry)
        floating_mask = min_distances > self.max_distance_to_structure_m
        floating_count = int(np.sum(floating_mask))

        if floating_count > 0:
            clean_points = points[~floating_mask]
            corrections.append({
                "correction_id": "corr_prune_floating_surfaces",
                "correction_type": "REMOVE_FLOATING_SURFACE",
                "target_id": "pointcloud_evidence",
                "delta_metric_value": float(floating_count),
                "delta_metric_unit": "points",
                "confidence": 0.95,
                "description": f"Pruned {floating_count} floating vertices exceeding {self.max_distance_to_structure_m:.2f}m from any structural plane"
            })
            return clean_points, corrections
        else:
            return points, corrections
