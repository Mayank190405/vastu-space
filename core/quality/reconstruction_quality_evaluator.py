"""
VĀSTU Reconstruction Quality Evaluator (Phase 9)
Master quality controller that orchestrates all automated validation gates:
- Pose consistency & scale drift validation
- Precision architectural geometry & metric tolerance evaluation
- Photorealistic Gaussian rendering quality verification
- Watertight collision and navigation validation
- Cross-session room alignment checks
- Emits certified Quality Reports and controls publishing gates
"""

import os
import json
import logging
from typing import Dict, Any, Optional

from core.quality.pose_consistency_validator import PoseConsistencyValidator
from core.quality.geometry_accuracy_validator import GeometryAccuracyValidator
from core.quality.room_alignment_validator import RoomAlignmentValidator
from core.quality.navigation_validation_engine import NavigationValidationEngine
from core.quality.quality_report_generator import QualityReportGenerator

logger = logging.getLogger("vastu.quality.reconstruction_quality_evaluator")


class ReconstructionQualityEvaluator:
    """
    Central quality gate enforcement engine for Phase 9 production certification.
    """

    def __init__(self):
        self.pose_val = PoseConsistencyValidator()
        self.geom_val = GeometryAccuracyValidator()
        self.align_val = RoomAlignmentValidator()
        self.nav_val = NavigationValidationEngine()
        self.report_gen = QualityReportGenerator()

    def evaluate_room(
        self,
        room_id: str,
        room_name: str,
        pose_result: Dict[str, Any],
        geometry_result: Dict[str, Any],
        gaussian_eval_result: Dict[str, Any],
        collision_data: list,
        doorways: list,
        alignment_result: Optional[Dict[str, Any]] = None,
        save_report_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Runs comprehensive quality validation on a reconstructed room.
        """
        # 1. Pose consistency check
        pose_check = self.pose_val.validate_pose_optimization(pose_result)

        # 2. Geometry accuracy check
        geom_check = self.geom_val.validate_geometry(geometry_result)

        # 3. Collision regression check
        collision_check = self.nav_val.run_collision_regression_suite(collision_data, doorways)

        # 4. Alignment check (if applicable)
        align_check = None
        if alignment_result:
            align_check = self.align_val.validate_pairwise_alignment(alignment_result)

        # 5. Generate certified report
        report = self.report_gen.generate_room_report(
            room_id=room_id,
            room_name=room_name,
            pose_validation=pose_check,
            geometry_validation=geom_check,
            gaussian_validation=gaussian_eval_result,
            collision_validation=collision_check,
            alignment_validation=align_check
        )

        if save_report_dir:
            os.makedirs(save_report_dir, exist_ok=True)
            report_path = os.path.join(save_report_dir, f"quality_report_{room_id}.json")
            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)

        return report

