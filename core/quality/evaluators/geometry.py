"""
Geometry Quality Evaluator:
Evaluates structural architectural geometry:
- plane confidence: inlier fit ratio of dominant planes
- corner integrity: preservation of sharp architectural intersections
- disconnected geometry: presence of orphan or floating walls
- phantom geometry: presence of specular reflection phantoms (mirrors/glass)
- structural consistency: watertightness, perpendicularity, parallelism
"""

from typing import Dict, Any, List, Tuple
from core.schemas.quality_engine import GeometryQualityMetrics

class GeometryQualityEvaluator:
    def __init__(
        self,
        min_plane_confidence: float = 0.70,
        min_corner_integrity: float = 0.75,
        max_disconnected_count: int = 0,
        max_phantom_count: int = 0,
        min_structural_consistency: float = 0.75,
    ):
        self.min_plane_confidence = min_plane_confidence
        self.min_corner_integrity = min_corner_integrity
        self.max_disconnected_count = max_disconnected_count
        self.max_phantom_count = max_phantom_count
        self.min_structural_consistency = min_structural_consistency

    def evaluate(self, geometry_data: Dict[str, Any]) -> Tuple[GeometryQualityMetrics, List[str], List[str]]:
        """
        Evaluates structural geometry quality.
        Returns (GeometryQualityMetrics, hard_failures, warnings).
        """
        plane_conf = float(geometry_data.get("plane_confidence", 0.88))
        corner_integrity = float(geometry_data.get("corner_integrity_score", 0.90))
        disconnected = int(geometry_data.get("disconnected_geometry_count", 0))
        phantoms = int(geometry_data.get("phantom_geometry_count", 0))
        structural_cons = float(geometry_data.get("structural_consistency_score", 0.92))

        issues = []
        hard_failures = []
        warnings = []

        if plane_conf < self.min_plane_confidence:
            msg = f"Low plane fitting confidence ({plane_conf:.2f} < threshold: {self.min_plane_confidence:.2f})"
            issues.append(msg)
            warnings.append(f"[WARN: GEOMETRY] {msg}")

        if corner_integrity < self.min_corner_integrity:
            msg = f"Degraded corner integrity: architectural corners rounded ({corner_integrity:.2f} < {self.min_corner_integrity:.2f})"
            issues.append(msg)
            warnings.append(f"[WARN: GEOMETRY] {msg}")

        if disconnected > self.max_disconnected_count:
            msg = f"Detected {disconnected} orphan/disconnected structural walls lacking room junctions"
            issues.append(msg)
            if disconnected >= 3:
                hard_failures.append(f"[HARD_FAIL: GEOMETRY] {msg}")
            else:
                warnings.append(f"[WARN: GEOMETRY] {msg}")

        if phantoms > self.max_phantom_count:
            msg = f"Detected {phantoms} phantom specular reflection surface(s) without physical backing"
            issues.append(msg)
            hard_failures.append(f"[HARD_FAIL: GEOMETRY] {msg}")

        if structural_cons < self.min_structural_consistency:
            msg = f"Structural inconsistency: non-watertight room hull or misaligned walls ({structural_cons:.2f} < {self.min_structural_consistency:.2f})"
            issues.append(msg)
            if structural_cons < 0.55:
                hard_failures.append(f"[HARD_FAIL: GEOMETRY] {msg}")
            else:
                warnings.append(f"[WARN: GEOMETRY] {msg}")

        metrics = GeometryQualityMetrics(
            plane_confidence=plane_conf,
            corner_integrity_score=corner_integrity,
            disconnected_geometry_count=disconnected,
            phantom_geometry_count=phantoms,
            structural_consistency_score=structural_cons,
            issues=issues
        )
        return metrics, hard_failures, warnings
