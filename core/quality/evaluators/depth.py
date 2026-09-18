"""
Depth Quality Evaluator:
Evaluates dense depth estimation and point cloud evidence:
- depth consistency: photometric and geometric multi-view agreement
- density: volumetric point density in points/m^3
- holes: percentage of surfaces with missing depth evidence
"""

from typing import Dict, Any, List, Tuple
from core.schemas.quality_engine import DepthQualityMetrics

class DepthQualityEvaluator:
    def __init__(
        self,
        min_consistency_ratio: float = 0.75,
        min_density_pts_per_m3: float = 400.0,
        max_hole_fraction: float = 0.12,
    ):
        self.min_consistency_ratio = min_consistency_ratio
        self.min_density_pts_per_m3 = min_density_pts_per_m3
        self.max_hole_fraction = max_hole_fraction

    def evaluate(self, depth_data: Dict[str, Any]) -> Tuple[DepthQualityMetrics, List[str], List[str]]:
        """
        Evaluates depth evidence quality.
        Returns (DepthQualityMetrics, hard_failures, warnings).
        """
        consistency = float(depth_data.get("consistency_ratio", 0.88))
        density = float(depth_data.get("density_pts_per_m3", 1250.0))
        holes = float(depth_data.get("hole_fraction", 0.04))

        issues = []
        hard_failures = []
        warnings = []

        if consistency < self.min_consistency_ratio:
            msg = f"Inconsistent multi-view depth observations (consistency: {consistency * 100:.1f}% < threshold: {self.min_consistency_ratio * 100:.1f}%)"
            issues.append(msg)
            if consistency < 0.50:
                hard_failures.append(f"[HARD_FAIL: DEPTH] {msg}")
            else:
                warnings.append(f"[WARN: DEPTH] {msg}")

        if density < self.min_density_pts_per_m3:
            msg = f"Insufficient dense point cloud density ({density:.0f} pts/m³ < minimum: {self.min_density_pts_per_m3:.0f} pts/m³)"
            issues.append(msg)
            if density < 150.0:
                hard_failures.append(f"[HARD_FAIL: DEPTH] {msg}")
            else:
                warnings.append(f"[WARN: DEPTH] {msg}")

        if holes > self.max_hole_fraction:
            msg = f"Excessive spatial coverage holes in dense geometry ({holes * 100:.1f}% > limit: {self.max_hole_fraction * 100:.1f}%)"
            issues.append(msg)
            if holes > 0.30:
                hard_failures.append(f"[HARD_FAIL: DEPTH] {msg}")
            else:
                warnings.append(f"[WARN: DEPTH] {msg}")

        metrics = DepthQualityMetrics(
            consistency_ratio=consistency,
            density_pts_per_m3=density,
            hole_fraction=holes,
            issues=issues
        )
        return metrics, hard_failures, warnings
