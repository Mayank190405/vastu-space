"""
Semantics Quality Evaluator:
Evaluates 3D semantic understanding:
- object confidence: mean detection confidence of semantic objects
- room confidence: certainty of room partitioning and containment
- unclassified ratio: fraction of spatial elements lacking semantic classification
"""

from typing import Dict, Any, List, Tuple
from core.schemas.quality_engine import SemanticsQualityMetrics

class SemanticsQualityEvaluator:
    def __init__(
        self,
        min_object_confidence: float = 0.70,
        min_room_confidence: float = 0.75,
        max_unclassified_ratio: float = 0.35,
    ):
        self.min_object_confidence = min_object_confidence
        self.min_room_confidence = min_room_confidence
        self.max_unclassified_ratio = max_unclassified_ratio

    def evaluate(self, semantics_data: Dict[str, Any]) -> Tuple[SemanticsQualityMetrics, List[str], List[str]]:
        """
        Evaluates semantic quality.
        Returns (SemanticsQualityMetrics, hard_failures, warnings).
        """
        obj_conf = float(semantics_data.get("mean_object_confidence", 0.88))
        room_conf = float(semantics_data.get("room_confidence", 0.92))
        unclassified = float(semantics_data.get("unclassified_ratio", 0.10))

        issues = []
        hard_failures = []
        warnings = []

        if obj_conf < self.min_object_confidence:
            msg = f"Low semantic object detection confidence ({obj_conf:.2f} < threshold: {self.min_object_confidence:.2f})"
            issues.append(msg)
            warnings.append(f"[WARN: SEMANTICS] {msg}")

        if room_conf < self.min_room_confidence:
            msg = f"Ambiguous room boundary partition confidence ({room_conf:.2f} < threshold: {self.min_room_confidence:.2f})"
            issues.append(msg)
            if room_conf < 0.50:
                hard_failures.append(f"[HARD_FAIL: SEMANTICS] {msg}")
            else:
                warnings.append(f"[WARN: SEMANTICS] {msg}")

        if unclassified > self.max_unclassified_ratio:
            msg = f"High unclassified spatial volume ({unclassified * 100:.1f}% > limit: {self.max_unclassified_ratio * 100:.1f}%)"
            issues.append(msg)
            warnings.append(f"[WARN: SEMANTICS] {msg}")

        metrics = SemanticsQualityMetrics(
            mean_object_confidence=obj_conf,
            room_confidence=room_conf,
            unclassified_ratio=unclassified,
            issues=issues
        )
        return metrics, hard_failures, warnings
