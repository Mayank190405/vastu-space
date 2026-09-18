"""
Central Quality Engine:
Coordinates multi-subsystem quality evaluation:
1. Capture (blur, exposure, coverage, overlap)
2. Pose (reprojection error, tracking continuity, loop closure, confidence)
3. Depth (consistency, density, holes)
4. Geometry (plane confidence, corners, disconnected walls, phantoms, structural consistency)
5. Semantics (object confidence, room confidence, unclassified ratio)
6. Navigation (floor continuity, obstacle validity, route reachability, ADA slopes)

Generates:
- Global composite quality score
- Per-cell scores and statuses
- Spatial confidence map
- Hard failure detection
- Warnings
- Recommended operational actions
- Narrative explaining WHY the reconstruction passed, warned, or failed
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from core.schemas.quality_engine import (
    CentralQualityEvaluation,
    CaptureQualityMetrics,
    PoseQualityMetrics,
    DepthQualityMetrics,
    GeometryQualityMetrics,
    SemanticsQualityMetrics,
    NavigationQualityMetrics,
    CellQualityRecord,
    SpatialConfidenceVoxel,
)
from core.quality.evaluators.capture import CaptureQualityEvaluator
from core.quality.evaluators.pose import PoseQualityEvaluator
from core.quality.evaluators.depth import DepthQualityEvaluator
from core.quality.evaluators.geometry import GeometryQualityEvaluator
from core.quality.evaluators.semantics import SemanticsQualityEvaluator
from core.quality.evaluators.navigation import NavigationQualityEvaluator
from core.quality.decision import QualityDecisionEngine

class CentralQualityEngine:
    # Subsystem weight distribution (sum = 1.0)
    WEIGHTS = {
        "capture": 0.15,
        "pose": 0.20,
        "depth": 0.15,
        "geometry": 0.20,
        "semantics": 0.10,
        "navigation": 0.20,
    }

    def __init__(
        self,
        capture_eval: Optional[CaptureQualityEvaluator] = None,
        pose_eval: Optional[PoseQualityEvaluator] = None,
        depth_eval: Optional[DepthQualityEvaluator] = None,
        geometry_eval: Optional[GeometryQualityEvaluator] = None,
        semantics_eval: Optional[SemanticsQualityEvaluator] = None,
        navigation_eval: Optional[NavigationQualityEvaluator] = None,
        decision_engine: Optional[QualityDecisionEngine] = None,
    ):
        self.capture_eval = capture_eval or CaptureQualityEvaluator()
        self.pose_eval = pose_eval or PoseQualityEvaluator()
        self.depth_eval = depth_eval or DepthQualityEvaluator()
        self.geometry_eval = geometry_eval or GeometryQualityEvaluator()
        self.semantics_eval = semantics_eval or SemanticsQualityEvaluator()
        self.navigation_eval = navigation_eval or NavigationQualityEvaluator()
        self.decision_engine = decision_engine or QualityDecisionEngine()

    def evaluate(
        self,
        project_id: uuid.UUID,
        model_version_id: str,
        capture_data: Optional[Dict[str, Any]] = None,
        pose_data: Optional[Dict[str, Any]] = None,
        depth_data: Optional[Dict[str, Any]] = None,
        geometry_data: Optional[Dict[str, Any]] = None,
        semantics_data: Optional[Dict[str, Any]] = None,
        navigation_data: Optional[Dict[str, Any]] = None,
        cells_data: Optional[Dict[str, Dict[str, Any]]] = None,
    ) -> CentralQualityEvaluation:
        """
        Executes end-to-end quality audit across all 6 dimensions.
        """
        capture_data = capture_data or {}
        pose_data = pose_data or {}
        depth_data = depth_data or {}
        geometry_data = geometry_data or {}
        semantics_data = semantics_data or {}
        navigation_data = navigation_data or {}
        cells_data = cells_data or {}

        all_hard_failures: List[str] = []
        all_warnings: List[str] = []

        # 1. Capture Subsystem
        cap_metrics, cap_hf, cap_warn = self.capture_eval.evaluate(capture_data)
        all_hard_failures.extend(cap_hf)
        all_warnings.extend(cap_warn)
        cap_score = (
            cap_metrics.blur_score * 0.30
            + cap_metrics.exposure_score * 0.20
            + cap_metrics.coverage_fraction * 0.30
            + cap_metrics.overlap_ratio * 0.20
        )

        # 2. Pose Subsystem
        pose_metrics, pose_hf, pose_warn = self.pose_eval.evaluate(pose_data)
        all_hard_failures.extend(pose_hf)
        all_warnings.extend(pose_warn)
        reproj_score = max(0.0, 1.0 - (pose_metrics.reprojection_error_px / 3.0))
        pose_score = (
            reproj_score * 0.30
            + pose_metrics.tracking_continuity_ratio * 0.30
            + (1.0 if pose_metrics.loop_closure_detected else 0.5) * 0.20
            + pose_metrics.mean_pose_confidence * 0.20
        )

        # 3. Depth Subsystem
        depth_metrics, depth_hf, depth_warn = self.depth_eval.evaluate(depth_data)
        all_hard_failures.extend(depth_hf)
        all_warnings.extend(depth_warn)
        density_score = min(1.0, depth_metrics.density_pts_per_m3 / 1000.0)
        depth_score = (
            depth_metrics.consistency_ratio * 0.40
            + density_score * 0.30
            + (1.0 - depth_metrics.hole_fraction) * 0.30
        )

        # 4. Geometry Subsystem
        geom_metrics, geom_hf, geom_warn = self.geometry_eval.evaluate(geometry_data)
        all_hard_failures.extend(geom_hf)
        all_warnings.extend(geom_warn)
        geom_score = (
            geom_metrics.plane_confidence * 0.30
            + geom_metrics.corner_integrity_score * 0.25
            + geom_metrics.structural_consistency_score * 0.35
            + (0.10 if geom_metrics.phantom_geometry_count == 0 else 0.0)
        )

        # 5. Semantics Subsystem
        sem_metrics, sem_hf, sem_warn = self.semantics_eval.evaluate(semantics_data)
        all_hard_failures.extend(sem_hf)
        all_warnings.extend(sem_warn)
        sem_score = (
            sem_metrics.mean_object_confidence * 0.40
            + sem_metrics.room_confidence * 0.40
            + (1.0 - sem_metrics.unclassified_ratio) * 0.20
        )

        # 6. Navigation Subsystem
        nav_metrics, nav_hf, nav_warn = self.navigation_eval.evaluate(navigation_data)
        all_hard_failures.extend(nav_hf)
        all_warnings.extend(nav_warn)
        nav_score = (
            nav_metrics.floor_continuity_ratio * 0.30
            + nav_metrics.obstacle_validity_ratio * 0.30
            + nav_metrics.route_feasibility_ratio * 0.40
        )

        subsystem_scores = {
            "capture": round(cap_score, 3),
            "pose": round(pose_score, 3),
            "depth": round(depth_score, 3),
            "geometry": round(geom_score, 3),
            "semantics": round(sem_score, 3),
            "navigation": round(nav_score, 3),
        }

        # Global Composite Score
        global_score = sum(
            subsystem_scores[sub] * self.WEIGHTS[sub] for sub in self.WEIGHTS
        )
        global_score = round(global_score, 3)

        # 7. Per-Cell Evaluation & Spatial Confidence Map
        per_cell_scores: Dict[str, CellQualityRecord] = {}
        per_cell_issues: Dict[str, List[str]] = {}
        spatial_confidence_map: List[SpatialConfidenceVoxel] = []

        if not cells_data:
            # Default single cell representing the overall model
            default_cell = "cell_root"
            cells_data = {
                default_cell: {
                    "score": global_score,
                    "center": [0.0, 0.0, 1.2],
                    "issues": all_hard_failures + all_warnings
                }
            }

        for cell_id, c_data in cells_data.items():
            c_score = float(c_data.get("score", global_score))
            c_issues = list(c_data.get("issues", []))
            per_cell_issues[cell_id] = c_issues

            c_verdict = "PASS" if c_score >= 0.75 and len([i for i in c_issues if "HARD_FAIL" in i]) == 0 else (
                "WARNING" if c_score >= 0.65 else "FAIL"
            )
            rescan_req = (c_verdict == "FAIL") or (c_score < 0.70)
            dominant = c_issues[0] if c_issues else None

            per_cell_scores[cell_id] = CellQualityRecord(
                cell_id=cell_id,
                score=round(c_score, 3),
                verdict=c_verdict,
                dominant_issue=dominant,
                rescan_required=rescan_req,
                metrics=c_data.get("metrics", {})
            )

            center = c_data.get("center", [0.0, 0.0, 1.0])
            spatial_confidence_map.append(
                SpatialConfidenceVoxel(
                    center_xyz=center,
                    confidence=round(c_score, 3),
                    primary_modality=c_data.get("modality", "MULTI_VIEW_DEPTH")
                )
            )

        # 8. Decision Verdict & Narrative Formulation
        verdict, recommended_actions, explanation = self.decision_engine.evaluate_verdict(
            global_score=global_score,
            subsystem_scores=subsystem_scores,
            hard_failures=all_hard_failures,
            warnings=all_warnings,
            per_cell_issues=per_cell_issues
        )

        return CentralQualityEvaluation(
            project_id=project_id,
            model_version_id=model_version_id,
            verdict=verdict,
            global_score=global_score,
            subsystem_scores=subsystem_scores,
            capture=cap_metrics,
            pose=pose_metrics,
            depth=depth_metrics,
            geometry=geom_metrics,
            semantics=sem_metrics,
            navigation=nav_metrics,
            per_cell_scores=per_cell_scores,
            spatial_confidence_map=spatial_confidence_map,
            hard_failures=all_hard_failures,
            warnings=all_warnings,
            recommended_actions=recommended_actions,
            explanation=explanation,
            created_at=datetime.now(timezone.utc).isoformat()
        )
