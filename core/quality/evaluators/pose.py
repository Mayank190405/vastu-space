"""
Pose Quality Evaluator:
Evaluates camera tracking and trajectory integrity:
- reprojection error: geometric bundle adjustment residual
- tracking continuity: trajectory breaks and tracking losses
- loop closure: loop closure detection and residual drift
- pose confidence: mean confidence across estimated camera poses
"""

from typing import Dict, Any, List, Tuple
from core.schemas.quality_engine import PoseQualityMetrics

class PoseQualityEvaluator:
    def __init__(
        self,
        max_reprojection_error_px: float = 1.50,
        min_tracking_continuity: float = 0.95,
        max_loop_closure_residual_m: float = 0.08,
        min_pose_confidence: float = 0.75,
    ):
        self.max_reprojection_error_px = max_reprojection_error_px
        self.min_tracking_continuity = min_tracking_continuity
        self.max_loop_closure_residual_m = max_loop_closure_residual_m
        self.min_pose_confidence = min_pose_confidence

    def evaluate(self, pose_data: Dict[str, Any]) -> Tuple[PoseQualityMetrics, List[str], List[str]]:
        """
        Evaluates pose trajectory.
        Returns (PoseQualityMetrics, hard_failures, warnings).
        """
        reproj = float(pose_data.get("reprojection_error_px", 0.95))
        continuity = float(pose_data.get("tracking_continuity_ratio", 0.98))
        loop_closed = bool(pose_data.get("loop_closure_detected", True))
        loop_residual = float(pose_data.get("loop_closure_residual_m", 0.03))
        confidence = float(pose_data.get("mean_pose_confidence", 0.92))

        issues = []
        hard_failures = []
        warnings = []

        if reproj > self.max_reprojection_error_px:
            msg = f"High reprojection error ({reproj:.2f}px > threshold: {self.max_reprojection_error_px:.2f}px)"
            issues.append(msg)
            if reproj > 2.50:
                hard_failures.append(f"[HARD_FAIL: POSE] {msg}")
            else:
                warnings.append(f"[WARN: POSE] {msg}")

        if continuity < self.min_tracking_continuity:
            msg = f"Trajectory tracking loss detected (continuity: {continuity * 100:.1f}% < threshold: {self.min_tracking_continuity * 100:.1f}%)"
            issues.append(msg)
            if continuity < 0.85:
                hard_failures.append(f"[HARD_FAIL: POSE] {msg}")
            else:
                warnings.append(f"[WARN: POSE] {msg}")

        if not loop_closed:
            msg = "No loop closure established across trajectory; accumulated drift uncorrected"
            issues.append(msg)
            warnings.append(f"[WARN: POSE] {msg}")
        elif loop_residual > self.max_loop_closure_residual_m:
            msg = f"Excessive loop closure drift residual ({loop_residual * 1000:.1f}mm > {self.max_loop_closure_residual_m * 1000:.1f}mm)"
            issues.append(msg)
            if loop_residual > 0.20:
                hard_failures.append(f"[HARD_FAIL: POSE] {msg}")
            else:
                warnings.append(f"[WARN: POSE] {msg}")

        if confidence < self.min_pose_confidence:
            msg = f"Low pose estimation confidence (mean: {confidence:.2f} < threshold: {self.min_pose_confidence:.2f})"
            issues.append(msg)
            if confidence < 0.50:
                hard_failures.append(f"[HARD_FAIL: POSE] {msg}")
            else:
                warnings.append(f"[WARN: POSE] {msg}")

        metrics = PoseQualityMetrics(
            reprojection_error_px=reproj,
            tracking_continuity_ratio=continuity,
            loop_closure_detected=loop_closed,
            loop_closure_residual_m=loop_residual,
            mean_pose_confidence=confidence,
            issues=issues
        )
        return metrics, hard_failures, warnings
