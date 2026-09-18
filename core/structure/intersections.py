"""
Architectural Plane Intersection Resolver:
Detects intersections, computes analytical sharp corner edges,
evaluates angle confidence, applies 90-degree architectural priors when supported by evidence,
and preserves genuine non-orthogonal architecture.
"""

from typing import Tuple, Optional, Dict, Any, List
import numpy as np

class PlaneIntersectionResolver:
    def __init__(
        self,
        orthogonal_tolerance_deg: float = 3.5,
        min_angle_confidence: float = 0.50,
        max_proximity_gap_m: float = 0.50
    ):
        """
        Args:
            orthogonal_tolerance_deg: Maximum deviation from 90 degrees to consider applying the 90-degree prior.
            min_angle_confidence: Minimum confidence required to snap to the 90-degree prior.
            max_proximity_gap_m: Maximum gap between plane inliers to consider them intersecting.
        """
        self.orthogonal_tolerance_deg = orthogonal_tolerance_deg
        self.min_angle_confidence = min_angle_confidence
        self.max_proximity_gap_m = max_proximity_gap_m

    def compute_dihedral_angle_deg(self, normal_a: np.ndarray, normal_b: np.ndarray) -> float:
        """Computes acute/right angle between two plane normals in degrees [0, 90]."""
        na = normal_a / (np.linalg.norm(normal_a) + 1e-9)
        nb = normal_b / (np.linalg.norm(normal_b) + 1e-9)
        cos_theta = float(np.clip(np.abs(np.dot(na, nb)), 0.0, 1.0))
        # The angle between perpendicular planes is 90 degrees (dot = 0 -> acos(0) = 90)
        # acos(abs(dot)) yields 90 when dot=0, and 0 when dot=1.
        angle_from_parallel = float(np.degrees(np.arccos(cos_theta)))
        return angle_from_parallel

    def compute_intersection_geometry(
        self,
        plane_eq_1: np.ndarray,
        plane_eq_2: np.ndarray,
        pts_1: np.ndarray,
        pts_2: np.ndarray
    ) -> Optional[Tuple[np.ndarray, np.ndarray, float]]:
        """
        Computes the 3D line segment of intersection between two planes bounded by the inliers.
        Returns:
            start_3d: [x, y, z] start of corner edge
            end_3d: [x, y, z] end of corner edge
            proximity_m: minimum distance between inliers near line
        """
        n1 = plane_eq_1[:3] / (np.linalg.norm(plane_eq_1[:3]) + 1e-9)
        n2 = plane_eq_2[:3] / (np.linalg.norm(plane_eq_2[:3]) + 1e-9)
        d1 = float(plane_eq_1[3]) / (np.linalg.norm(plane_eq_1[:3]) + 1e-9)
        d2 = float(plane_eq_2[3]) / (np.linalg.norm(plane_eq_2[:3]) + 1e-9)

        # Intersection direction
        line_dir = np.cross(n1, n2)
        dir_norm = np.linalg.norm(line_dir)
        if dir_norm < 1e-4:
            # Planes are parallel or coplanar
            return None

        line_dir = line_dir / dir_norm

        # Solve for origin point p0 on intersection line
        # A * p0 = b
        A = np.vstack([n1, n2, line_dir])
        b = np.array([-d1, -d2, 0.0])
        try:
            p0 = np.linalg.solve(A, b)
        except np.linalg.LinAlgError:
            return None

        # Check inlier proximity to intersection line
        if len(pts_1) == 0 or len(pts_2) == 0:
            return None

        # Project points onto line: t = dot(p - p0, line_dir)
        t1 = np.dot(pts_1 - p0, line_dir)
        t2 = np.dot(pts_2 - p0, line_dir)

        t1_min, t1_max = float(np.min(t1)), float(np.max(t1))
        t2_min, t2_max = float(np.min(t2)), float(np.max(t2))

        # Check overlapping span along the intersection axis
        overlap_min = max(t1_min, t2_min)
        overlap_max = min(t1_max, t2_max)

        if overlap_max < overlap_min:
            # No overlap along line direction; check if gap is within tolerance
            gap = overlap_min - overlap_max
            if gap > self.max_proximity_gap_m:
                return None
            t_start = (overlap_min + overlap_max) / 2.0 - 0.2
            t_end = (overlap_min + overlap_max) / 2.0 + 0.2
        else:
            t_start = overlap_min
            t_end = overlap_max

        # Ensure segment has length
        if abs(t_end - t_start) < 0.05:
            t_start -= 0.1
            t_end += 0.1

        start_3d = p0 + t_start * line_dir
        end_3d = p0 + t_end * line_dir

        # Measure proximity of closest points
        c1 = np.mean(pts_1, axis=0)
        c2 = np.mean(pts_2, axis=0)
        proximity_m = float(np.linalg.norm(c1 - c2))

        return start_3d, end_3d, proximity_m

    def resolve_intersection(
        self,
        plane_id_1: str,
        plane_id_2: str,
        plane_type_1: str,
        plane_type_2: str,
        plane_eq_1: np.ndarray,
        plane_eq_2: np.ndarray,
        pts_1: np.ndarray,
        pts_2: np.ndarray,
        conf_1: float,
        conf_2: float
    ) -> Optional[Dict[str, Any]]:
        """
        Resolves the intersection between two planes, applying the 90-degree prior only when
        supported by evidence, and preserving non-orthogonal architecture.
        """
        geom = self.compute_intersection_geometry(plane_eq_1, plane_eq_2, pts_1, pts_2)
        if geom is None:
            return None

        start_3d, end_3d, proximity_m = geom
        n1 = plane_eq_1[:3]
        n2 = plane_eq_2[:3]

        # Calculate actual dihedral intersection angle
        raw_angle = self.compute_dihedral_angle_deg(n1, n2)

        # Evaluate angle confidence based on plane confidences, inlier density, and parallax
        n1_u = n1 / (np.linalg.norm(n1) + 1e-9)
        n2_u = n2 / (np.linalg.norm(n2) + 1e-9)
        parallax = float(np.linalg.norm(np.cross(n1_u, n2_u)))
        
        # Base confidence from individual plane confidences and parallax
        angle_confidence = float(np.sqrt(conf_1 * conf_2) * parallax)
        angle_confidence = float(np.clip(angle_confidence, 0.0, 1.0))

        # Architectural prior decision logic
        delta_90 = abs(raw_angle - 90.0)
        is_orthogonal = False
        adjusted_angle = raw_angle

        # If it is close to 90 degrees within tolerance and has high confidence, snap to 90
        if delta_90 <= self.orthogonal_tolerance_deg and angle_confidence >= self.min_angle_confidence:
            is_orthogonal = True
            adjusted_angle = 90.0
        else:
            # Genuine non-orthogonal architecture (e.g., 45 deg, 60 deg, 120 deg, 135 deg)
            # or insufficient evidence: preserve true measured angle!
            is_orthogonal = False
            adjusted_angle = float(round(raw_angle, 2))

        # Determine junction type
        types = {plane_type_1, plane_type_2}
        if types == {"WALL"}:
            junction_type = "WALL_WALL"
        elif types == {"WALL", "FLOOR"}:
            junction_type = "WALL_FLOOR"
        elif types == {"WALL", "CEILING"}:
            junction_type = "WALL_CEILING"
        elif "WALL" in types:
            junction_type = "WALL_OTHER"
        else:
            junction_type = "OTHER"

        return {
            "edge_id": f"edge_{plane_id_1}__{plane_id_2}",
            "source_plane_id": plane_id_1,
            "target_plane_id": plane_id_2,
            "raw_angle_deg": float(round(raw_angle, 2)),
            "adjusted_angle_deg": float(round(adjusted_angle, 2)),
            "angle_confidence": float(round(angle_confidence, 4)),
            "is_orthogonal_prior_applied": is_orthogonal,
            "intersection_line_start": [float(round(v, 4)) for v in start_3d],
            "intersection_line_end": [float(round(v, 4)) for v in end_3d],
            "junction_type": junction_type
        }
