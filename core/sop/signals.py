"""
VĀSTU Capture SOP Engine: Live Quality Signals
Evaluates real-time measurable sensor telemetry against numeric quality thresholds.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class QualitySignalType(str, Enum):
    EXCESSIVE_MOTION = "EXCESSIVE_MOTION"
    BLUR = "BLUR"
    INSUFFICIENT_OVERLAP = "INSUFFICIENT_OVERLAP"
    POOR_LIGHTING = "POOR_LIGHTING"
    LOW_FEATURE_DENSITY = "LOW_FEATURE_DENSITY"
    INADEQUATE_COVERAGE = "INADEQUATE_COVERAGE"
    TRACKING_DEGRADATION = "TRACKING_DEGRADATION"


class LiveTelemetrySnapshot(BaseModel):
    linear_velocity_mps: float = 0.40
    angular_velocity_radps: float = 0.25
    blur_laplacian_variance: float = 250.0
    motion_blur_score: float = 0.05
    inter_frame_rotation_deg: float = 3.5
    inter_frame_translation_m: float = 0.08
    ambient_lux: float = 180.0
    glare_saturation_fraction: float = 0.02
    tracked_feature_count: int = 240
    unobserved_area_fraction: float = 0.10
    tracking_inlier_count: int = 150
    reprojection_error_px: float = 0.85
    is_tracking_lost: bool = False


class QualitySignalEvaluation(BaseModel):
    signal_type: QualitySignalType
    triggered: bool
    severity: str  # "CRITICAL", "WARNING", "INFO"
    measured_value: float
    threshold_value: float
    instruction: str


class QualitySignalEvaluator:
    """
    Evaluates measurable telemetry conditions against strict quality thresholds.
    """

    # Deterministic Numeric Thresholds
    MAX_LINEAR_VELOCITY_MPS = 0.80
    MAX_ANGULAR_VELOCITY_RADPS = 1.20
    MIN_LAPLACIAN_VARIANCE = 100.0
    MAX_MOTION_BLUR_SCORE = 0.40
    MAX_ROTATION_DELTA_DEG = 15.0
    MAX_TRANSLATION_DELTA_M = 0.60
    MIN_AMBIENT_LUX = 30.0
    MAX_AMBIENT_LUX = 2000.0
    MAX_GLARE_FRACTION = 0.15
    MIN_FEATURE_COUNT = 80
    MAX_UNOBSERVED_FRACTION = 0.30
    MIN_TRACKING_INLIERS = 30
    MAX_REPROJECTION_ERROR_PX = 2.50

    @classmethod
    def evaluate(cls, telemetry: LiveTelemetrySnapshot) -> List[QualitySignalEvaluation]:
        results = []

        # 1. Excessive Motion
        is_fast_linear = telemetry.linear_velocity_mps > cls.MAX_LINEAR_VELOCITY_MPS
        is_fast_angular = telemetry.angular_velocity_radps > cls.MAX_ANGULAR_VELOCITY_RADPS
        if is_fast_linear or is_fast_angular:
            val = max(telemetry.linear_velocity_mps, telemetry.angular_velocity_radps)
            results.append(
                QualitySignalEvaluation(
                    signal_type=QualitySignalType.EXCESSIVE_MOTION,
                    triggered=True,
                    severity="WARNING",
                    measured_value=round(val, 2),
                    threshold_value=cls.MAX_LINEAR_VELOCITY_MPS,
                    instruction="Slow down. Move camera more steadily."
                )
            )

        # 2. Blur
        is_blurry = (telemetry.blur_laplacian_variance < cls.MIN_LAPLACIAN_VARIANCE or
                     telemetry.motion_blur_score > cls.MAX_MOTION_BLUR_SCORE)
        if is_blurry:
            results.append(
                QualitySignalEvaluation(
                    signal_type=QualitySignalType.BLUR,
                    triggered=True,
                    severity="WARNING",
                    measured_value=round(telemetry.blur_laplacian_variance, 1),
                    threshold_value=cls.MIN_LAPLACIAN_VARIANCE,
                    instruction="Image blur detected. Hold camera steady."
                )
            )

        # 3. Insufficient Overlap
        is_low_overlap = (telemetry.inter_frame_rotation_deg > cls.MAX_ROTATION_DELTA_DEG or
                          telemetry.inter_frame_translation_m > cls.MAX_TRANSLATION_DELTA_M)
        if is_low_overlap:
            results.append(
                QualitySignalEvaluation(
                    signal_type=QualitySignalType.INSUFFICIENT_OVERLAP,
                    triggered=True,
                    severity="WARNING",
                    measured_value=round(telemetry.inter_frame_rotation_deg, 1),
                    threshold_value=cls.MAX_ROTATION_DELTA_DEG,
                    instruction="Move more gradually to maintain view overlap."
                )
            )

        # 4. Poor Lighting
        if telemetry.ambient_lux < cls.MIN_AMBIENT_LUX:
            results.append(
                QualitySignalEvaluation(
                    signal_type=QualitySignalType.POOR_LIGHTING,
                    triggered=True,
                    severity="WARNING",
                    measured_value=round(telemetry.ambient_lux, 1),
                    threshold_value=cls.MIN_AMBIENT_LUX,
                    instruction="Lighting too low. Turn on room lights."
                )
            )
        elif telemetry.ambient_lux > cls.MAX_AMBIENT_LUX and telemetry.glare_saturation_fraction > cls.MAX_GLARE_FRACTION:
            results.append(
                QualitySignalEvaluation(
                    signal_type=QualitySignalType.POOR_LIGHTING,
                    triggered=True,
                    severity="WARNING",
                    measured_value=round(telemetry.glare_saturation_fraction, 2),
                    threshold_value=cls.MAX_GLARE_FRACTION,
                    instruction="Direct glare detected. Angle camera away from direct bright light."
                )
            )

        # 5. Low Feature Density
        if telemetry.tracked_feature_count < cls.MIN_FEATURE_COUNT:
            results.append(
                QualitySignalEvaluation(
                    signal_type=QualitySignalType.LOW_FEATURE_DENSITY,
                    triggered=True,
                    severity="GUIDANCE",
                    measured_value=float(telemetry.tracked_feature_count),
                    threshold_value=float(cls.MIN_FEATURE_COUNT),
                    instruction="Low texture area. Frame more furniture, doorway jambs, or baseboards."
                )
            )

        # 6. Inadequate Coverage
        if telemetry.unobserved_area_fraction > cls.MAX_UNOBSERVED_FRACTION:
            results.append(
                QualitySignalEvaluation(
                    signal_type=QualitySignalType.INADEQUATE_COVERAGE,
                    triggered=True,
                    severity="GUIDANCE",
                    measured_value=round(telemetry.unobserved_area_fraction, 2),
                    threshold_value=cls.MAX_UNOBSERVED_FRACTION,
                    instruction="Coverage incomplete. Sweep remaining unvisited areas."
                )
            )

        # 7. Tracking Degradation
        is_tracking_bad = (telemetry.is_tracking_lost or
                           telemetry.tracking_inlier_count < cls.MIN_TRACKING_INLIERS or
                           telemetry.reprojection_error_px > cls.MAX_REPROJECTION_ERROR_PX)
        if is_tracking_bad:
            severity = "CRITICAL" if telemetry.is_tracking_lost else "WARNING"
            results.append(
                QualitySignalEvaluation(
                    signal_type=QualitySignalType.TRACKING_DEGRADATION,
                    triggered=True,
                    severity=severity,
                    measured_value=round(telemetry.reprojection_error_px, 2),
                    threshold_value=cls.MAX_REPROJECTION_ERROR_PX,
                    instruction="Tracking unstable. Aim camera toward previously scanned features."
                )
            )

        return results
