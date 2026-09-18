"""
Wall Thickness Estimator:
Detects parallel interior/exterior wall surfaces and computes measurable wall thickness.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np

class WallThicknessEstimator:
    def __init__(
        self,
        min_thickness_m: float = 0.08,
        max_thickness_m: float = 0.50,
        parallel_tolerance_deg: float = 5.0,
        nominal_single_sided_thickness_m: float = 0.15
    ):
        self.min_thickness_m = min_thickness_m
        self.max_thickness_m = max_thickness_m
        self.cos_parallel_thresh = np.cos(np.radians(parallel_tolerance_deg))
        self.nominal_single_sided_thickness_m = nominal_single_sided_thickness_m

    def estimate_thickness_between_planes(
        self,
        plane_eq_1: np.ndarray,
        plane_eq_2: np.ndarray,
        pts_1: np.ndarray,
        pts_2: np.ndarray
    ) -> Optional[Tuple[float, float, str]]:
        """
        Estimates the perpendicular thickness between two wall planes if they form a parallel pair.
        Returns:
            thickness_m: Estimated physical wall thickness in meters
            confidence: Confidence in the estimation [0.0, 1.0]
            configuration: 'OPPOSITE_FACING' or 'SAME_FACING'
        """
        n1 = plane_eq_1[:3] / (np.linalg.norm(plane_eq_1[:3]) + 1e-9)
        n2 = plane_eq_2[:3] / (np.linalg.norm(plane_eq_2[:3]) + 1e-9)
        d1 = float(plane_eq_1[3]) / (np.linalg.norm(plane_eq_1[:3]) + 1e-9)
        d2 = float(plane_eq_2[3]) / (np.linalg.norm(plane_eq_2[:3]) + 1e-9)

        dot_norm = float(np.dot(n1, n2))

        # Check for opposite facing parallel planes (n1 ~ -n2)
        if dot_norm <= -self.cos_parallel_thresh:
            config = "OPPOSITE_FACING"
            # Distance between n*x + d1 = 0 and -n*x + d2 = 0
            # d1 = -n*x1, d2 = n*x2 -> thickness = |d1 + d2|
            thickness = abs(d1 + d2)
        elif dot_norm >= self.cos_parallel_thresh:
            config = "SAME_FACING"
            thickness = abs(d1 - d2)
        else:
            return None

        if not (self.min_thickness_m <= thickness <= self.max_thickness_m):
            return None

        # Check spatial overlap using centroids
        c1 = np.mean(pts_1, axis=0) if len(pts_1) > 0 else np.zeros(3)
        c2 = np.mean(pts_2, axis=0) if len(pts_2) > 0 else np.zeros(3)

        # Distance between centroids along the tangent plane
        disp = c2 - c1
        tangent_disp = disp - np.dot(disp, n1) * n1
        tangent_dist = float(np.linalg.norm(tangent_disp))

        # If planes are far apart laterally, they don't form the same wall
        if tangent_dist > 3.0:
            return None

        overlap_factor = float(np.exp(-tangent_dist / 2.0))
        parallel_factor = abs(dot_norm)
        confidence = float(np.clip(overlap_factor * parallel_factor, 0.0, 1.0))

        return float(round(thickness, 4)), float(round(confidence, 4)), config

    def estimate_wall_thicknesses(
        self,
        walls: List[Dict[str, Any]],
        wall_points: Dict[str, np.ndarray]
    ) -> List[Dict[str, Any]]:
        """
        Analyzes a set of wall planes and estimates thicknesses for paired surfaces.
        """
        results = []
        paired_wall_ids = set()

        num_walls = len(walls)
        for i in range(num_walls):
            w1 = walls[i]
            id1 = w1["structure_id"]
            if id1 in paired_wall_ids:
                continue

            eq1 = np.array(w1["plane_equation"])
            pts1 = wall_points.get(id1, np.empty((0, 3)))

            best_pair = None
            best_conf = 0.0

            for j in range(i + 1, num_walls):
                w2 = walls[j]
                id2 = w2["structure_id"]
                if id2 in paired_wall_ids:
                    continue

                eq2 = np.array(w2["plane_equation"])
                pts2 = wall_points.get(id2, np.empty((0, 3)))

                res = self.estimate_thickness_between_planes(eq1, eq2, pts1, pts2)
                if res is not None:
                    thick, conf, cfg = res
                    if conf > best_conf:
                        best_conf = conf
                        best_pair = (id2, thick, conf, cfg)

            if best_pair is not None and best_conf >= 0.5:
                id2, thick, conf, cfg = best_pair
                paired_wall_ids.add(id1)
                paired_wall_ids.add(id2)
                results.append({
                    "wall_id_1": id1,
                    "wall_id_2": id2,
                    "thickness_m": thick,
                    "confidence": conf,
                    "configuration": cfg,
                    "is_double_sided": True
                })
            else:
                # Single-sided wall observed
                results.append({
                    "wall_id_1": id1,
                    "wall_id_2": None,
                    "thickness_m": self.nominal_single_sided_thickness_m,
                    "confidence": 0.5,
                    "configuration": "SINGLE_SIDED_NOMINAL",
                    "is_double_sided": False
                })

        return results
