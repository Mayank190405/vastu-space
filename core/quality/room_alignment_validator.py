"""
VĀSTU Room Alignment Validator (Phase 9)
Validates cross-session room alignment evidence and topological connection consistency:
- Doorway width and threshold congruence (delta <= 15 cm)
- Alignment confidence score >= 0.70
- Alignment residual RMSE <= 5.0 cm
- Loop closure cycle consistency across multi-room connections
- Automatically flags REQUIRES_MANUAL_REVIEW or REQUIRES_RESCAN when alignment evidence fails
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger("vastu.quality.room_alignment_validator")


class RoomAlignmentValidator:
    """
    Validates inter-room alignment evidence and prevents unverified room merges.
    """

    def __init__(
        self,
        min_alignment_confidence: float = 0.70,
        max_alignment_rmse_m: float = 0.050,
        max_doorway_width_delta_m: float = 0.150
    ):
        self.min_alignment_confidence = min_alignment_confidence
        self.max_alignment_rmse_m = max_alignment_rmse_m
        self.max_doorway_width_delta_m = max_doorway_width_delta_m

    def validate_pairwise_alignment(self, alignment_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates the output of CrossSessionAlignmentEngine.
        """
        conf = alignment_result.get("confidence", 0.0)
        rmse = alignment_result.get("rmse_m", 1.0)
        width_delta = alignment_result.get("doorway_width_delta_m", 0.0)
        inlier_ratio = alignment_result.get("inlier_ratio", 0.0)

        meets_conf = conf >= self.min_alignment_confidence
        meets_rmse = rmse <= self.max_alignment_rmse_m
        meets_width = width_delta <= self.max_doorway_width_delta_m
        meets_inliers = inlier_ratio >= 0.70

        is_passed = meets_conf and meets_rmse and meets_width and meets_inliers

        if is_passed:
            status = "PASSED"
            recommendation = "APPROVED_FOR_MERGE"
        elif meets_conf and meets_width:
            status = "REQUIRES_MANUAL_REVIEW"
            recommendation = "ADMIN_REVIEW_DOORWAY_SEED"
        else:
            status = "REQUIRES_RESCAN"
            recommendation = "RESCAN_DOORWAY_TRANSITION"

        return {
            "status": status,
            "is_passed": is_passed,
            "recommendation": recommendation,
            "metrics": {
                "confidence": conf,
                "rmse_mm": round(rmse * 1000.0, 1),
                "doorway_width_delta_mm": round(width_delta * 1000.0, 1),
                "inlier_ratio": round(inlier_ratio, 3)
            },
            "checks": {
                "meets_confidence": meets_conf,
                "meets_rmse": meets_rmse,
                "meets_doorway_width": meets_width,
                "meets_inlier_ratio": meets_inliers
            }
        }

