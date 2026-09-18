"""
Capture Quality Evaluator:
Evaluates raw capture telemetry:
- blur: sharpness of keyframes
- exposure: lighting balance (under/over exposure)
- coverage: completeness of spatial viewing
- overlap: visual overlap between consecutive keyframes
"""

from typing import Dict, Any, List, Tuple
from core.schemas.quality_engine import CaptureQualityMetrics

class CaptureQualityEvaluator:
    def __init__(
        self,
        min_blur_score: float = 0.70,
        min_exposure_score: float = 0.65,
        min_coverage_fraction: float = 0.80,
        min_overlap_ratio: float = 0.65,
    ):
        self.min_blur_score = min_blur_score
        self.min_exposure_score = min_exposure_score
        self.min_coverage_fraction = min_coverage_fraction
        self.min_overlap_ratio = min_overlap_ratio

    def evaluate(self, capture_data: Dict[str, Any]) -> Tuple[CaptureQualityMetrics, List[str], List[str]]:
        """
        Evaluates capture telemetry.
        Returns (CaptureQualityMetrics, hard_failures, warnings).
        """
        blur = float(capture_data.get("blur_score", 0.90))
        exposure = float(capture_data.get("exposure_score", 0.88))
        coverage = float(capture_data.get("coverage_fraction", 0.92))
        overlap = float(capture_data.get("overlap_ratio", 0.85))

        issues = []
        hard_failures = []
        warnings = []

        if blur < self.min_blur_score:
            msg = f"Severe keyframe blur detected (score: {blur:.2f} < threshold: {self.min_blur_score:.2f})"
            issues.append(msg)
            if blur < 0.50:
                hard_failures.append(f"[HARD_FAIL: CAPTURE] {msg}")
            else:
                warnings.append(f"[WARN: CAPTURE] {msg}")

        if exposure < self.min_exposure_score:
            msg = f"Poor exposure balance detected (score: {exposure:.2f} < threshold: {self.min_exposure_score:.2f})"
            issues.append(msg)
            warnings.append(f"[WARN: CAPTURE] {msg}")

        if coverage < self.min_coverage_fraction:
            msg = f"Insufficient visual coverage (observed: {coverage * 100:.1f}% < required: {self.min_coverage_fraction * 100:.1f}%)"
            issues.append(msg)
            if coverage < 0.60:
                hard_failures.append(f"[HARD_FAIL: CAPTURE] {msg}")
            else:
                warnings.append(f"[WARN: CAPTURE] {msg}")

        if overlap < self.min_overlap_ratio:
            msg = f"Low inter-frame overlap (ratio: {overlap:.2f} < required: {self.min_overlap_ratio:.2f})"
            issues.append(msg)
            if overlap < 0.40:
                hard_failures.append(f"[HARD_FAIL: CAPTURE] {msg}")
            else:
                warnings.append(f"[WARN: CAPTURE] {msg}")

        metrics = CaptureQualityMetrics(
            blur_score=blur,
            exposure_score=exposure,
            coverage_fraction=coverage,
            overlap_ratio=overlap,
            issues=issues
        )
        return metrics, hard_failures, warnings
