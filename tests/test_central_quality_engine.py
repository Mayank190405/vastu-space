"""
Test Suite: Central Quality Engine
Verifies:
1. Multi-subsystem quality evaluation across all 6 domains:
   - Capture: blur, exposure, coverage, overlap
   - Pose: reprojection error, tracking continuity, loop closure, pose confidence
   - Depth: depth consistency, density, holes
   - Geometry: plane confidence, corner integrity, disconnected geometry, phantom geometry, structural consistency
   - Semantics: object confidence, room confidence
   - Navigation: floor continuity, obstacle validity, route feasibility
2. Per-cell quality scoring and spatial confidence map generation.
3. Non-arbitrary decision making: Hard Failures block publication even if composite score is high.
4. Acceptance Criterion:
   The engine can explain WHY a reconstruction passed or failed with detailed root-cause narrative.
"""

import pytest
import uuid
from core.quality.engine import CentralQualityEngine
from core.quality.decision import QualityDecisionEngine
from core.quality.evaluators.capture import CaptureQualityEvaluator
from core.quality.evaluators.pose import PoseQualityEvaluator
from core.quality.evaluators.depth import DepthQualityEvaluator
from core.quality.evaluators.geometry import GeometryQualityEvaluator
from core.quality.evaluators.semantics import SemanticsQualityEvaluator
from core.quality.evaluators.navigation import NavigationQualityEvaluator
from core.schemas.quality_engine import CentralQualityEvaluation

def test_six_subsystem_evaluators_nominal_and_defects():
    """Validates each of the 6 evaluators on clean data vs detected defects."""
    # 1. Capture Evaluator
    cap_eval = CaptureQualityEvaluator()
    clean_cap, hf, warn = cap_eval.evaluate({"blur_score": 0.90, "exposure_score": 0.85, "coverage_fraction": 0.95, "overlap_ratio": 0.80})
    assert len(hf) == 0 and len(warn) == 0
    assert clean_cap.blur_score == 0.90

    blurry_cap, hf, warn = cap_eval.evaluate({"blur_score": 0.40, "exposure_score": 0.85, "coverage_fraction": 0.95, "overlap_ratio": 0.80})
    assert any("blur" in f.lower() for f in hf)

    # 2. Pose Evaluator
    pose_eval = PoseQualityEvaluator()
    clean_pose, hf, warn = pose_eval.evaluate({"reprojection_error_px": 0.80, "tracking_continuity_ratio": 0.99, "loop_closure_detected": True, "loop_closure_residual_m": 0.02, "mean_pose_confidence": 0.95})
    assert len(hf) == 0
    assert clean_pose.loop_closure_detected is True

    drifting_pose, hf, warn = pose_eval.evaluate({"reprojection_error_px": 3.20, "tracking_continuity_ratio": 0.70, "loop_closure_detected": False, "loop_closure_residual_m": 0.35, "mean_pose_confidence": 0.40})
    assert len(hf) >= 2  # Reprojection and tracking loss hard failures

    # 3. Depth Evaluator
    depth_eval = DepthQualityEvaluator()
    clean_depth, hf, warn = depth_eval.evaluate({"consistency_ratio": 0.90, "density_pts_per_m3": 1500.0, "hole_fraction": 0.02})
    assert len(hf) == 0

    holey_depth, hf, warn = depth_eval.evaluate({"consistency_ratio": 0.40, "density_pts_per_m3": 80.0, "hole_fraction": 0.35})
    assert any("hole" in f.lower() or "density" in f.lower() for f in hf)

    # 4. Geometry Evaluator
    geom_eval = GeometryQualityEvaluator()
    clean_geom, hf, warn = geom_eval.evaluate({"plane_confidence": 0.90, "corner_integrity_score": 0.92, "disconnected_geometry_count": 0, "phantom_geometry_count": 0, "structural_consistency_score": 0.94})
    assert len(hf) == 0

    phantom_geom, hf, warn = geom_eval.evaluate({"plane_confidence": 0.90, "corner_integrity_score": 0.92, "disconnected_geometry_count": 0, "phantom_geometry_count": 2, "structural_consistency_score": 0.94})
    assert any("phantom" in f.lower() for f in hf)

    # 5. Semantics Evaluator
    sem_eval = SemanticsQualityEvaluator()
    clean_sem, hf, warn = sem_eval.evaluate({"mean_object_confidence": 0.85, "room_confidence": 0.90, "unclassified_ratio": 0.08})
    assert len(hf) == 0

    low_sem, hf, warn = sem_eval.evaluate({"mean_object_confidence": 0.50, "room_confidence": 0.45, "unclassified_ratio": 0.45})
    assert any("room" in f.lower() or "confidence" in f.lower() for f in hf + warn)

    # 6. Navigation Evaluator
    nav_eval = NavigationQualityEvaluator()
    clean_nav, hf, warn = nav_eval.evaluate({"floor_continuity_ratio": 0.95, "obstacle_validity_ratio": 0.92, "route_feasibility_ratio": 1.00, "wheelchair_ada_compliant": True})
    assert len(hf) == 0

    broken_nav, hf, warn = nav_eval.evaluate({
        "floor_continuity_ratio": 0.95,
        "obstacle_validity_ratio": 0.92,
        "route_feasibility_ratio": 0.60,
        "disconnected_routes": ["Entrance -> Executive Suite"],
        "wheelchair_ada_compliant": False
    })
    assert any("disconnected" in f.lower() for f in hf)
    assert any("wheelchair" in w.lower() for w in warn)

def test_per_cell_scores_and_spatial_confidence_map():
    """Validates per-cell evaluation, rescan requirement flagging, and spatial confidence voxels."""
    engine = CentralQualityEngine()
    project_id = uuid.uuid4()

    cells_data = {
        "cell_A_entrance": {
            "score": 0.94,
            "center": [0.0, 0.0, 1.0],
            "modality": "LIDAR_RGB",
            "issues": []
        },
        "cell_B_lobby": {
            "score": 0.88,
            "center": [5.0, 0.0, 1.0],
            "modality": "STEREO_DEPTH",
            "issues": ["[WARN: DEPTH] Slight hole density in corner"]
        },
        "cell_C_stairs": {
            "score": 0.58,
            "center": [10.0, 3.0, 1.5],
            "modality": "ESTIMATED_DEPTH",
            "issues": ["[HARD_FAIL: CAPTURE] Severe motion blur", "[HARD_FAIL: DEPTH] Inconsistent depth"]
        }
    }

    eval_result = engine.evaluate(
        project_id=project_id,
        model_version_id="mod_test_v1",
        cells_data=cells_data
    )

    assert isinstance(eval_result, CentralQualityEvaluation)
    assert len(eval_result.per_cell_scores) == 3
    assert eval_result.per_cell_scores["cell_A_entrance"].verdict == "PASS"
    assert eval_result.per_cell_scores["cell_A_entrance"].rescan_required is False

    assert eval_result.per_cell_scores["cell_C_stairs"].verdict == "FAIL"
    assert eval_result.per_cell_scores["cell_C_stairs"].rescan_required is True

    assert len(eval_result.spatial_confidence_map) == 3
    assert eval_result.spatial_confidence_map[0].center_xyz == [0.0, 0.0, 1.0]
    assert eval_result.spatial_confidence_map[0].confidence == 0.94

def test_hard_failures_block_publication_regardless_of_high_score():
    """
    Verifies policy: Do not use one arbitrary numerical score as the sole publication decision.
    Even if global score is high (e.g. 0.84), a critical hard failure (e.g. disconnected route)
    must unconditionally force the verdict to FAIL.
    """
    engine = CentralQualityEngine()
    project_id = uuid.uuid4()

    # High capture, pose, depth, geometry, semantics, but a critical navigation disconnect
    evaluation = engine.evaluate(
        project_id=project_id,
        model_version_id="high_score_failing_model",
        capture_data={"blur_score": 0.95, "exposure_score": 0.92, "coverage_fraction": 0.96, "overlap_ratio": 0.90},
        pose_data={"reprojection_error_px": 0.85, "tracking_continuity_ratio": 0.99, "loop_closure_detected": True, "loop_closure_residual_m": 0.02, "mean_pose_confidence": 0.95},
        depth_data={"consistency_ratio": 0.92, "density_pts_per_m3": 1800.0, "hole_fraction": 0.02},
        geometry_data={"plane_confidence": 0.92, "corner_integrity_score": 0.95, "disconnected_geometry_count": 0, "phantom_geometry_count": 0, "structural_consistency_score": 0.94},
        semantics_data={"mean_object_confidence": 0.90, "room_confidence": 0.95, "unclassified_ratio": 0.05},
        navigation_data={
            "floor_continuity_ratio": 0.95,
            "obstacle_validity_ratio": 0.90,
            "route_feasibility_ratio": 0.50,
            "disconnected_routes": ["Entrance cannot reach Main Conference Room"],
            "wheelchair_ada_compliant": True
        }
    )

    # Composite numerical score is high (~0.87)
    assert evaluation.global_score >= 0.80
    # But verdict MUST be FAIL because of the Hard Failure
    assert evaluation.verdict == "FAIL"
    assert len(evaluation.hard_failures) > 0
    assert any("NAVIGATION" in hf for hf in evaluation.hard_failures)

def test_acceptance_criterion_engine_explains_why_reconstruction_passed_or_failed():
    """
    Acceptance Criterion:
    The engine can explain WHY a reconstruction passed or failed.
    Verifies that the generated explanation narrative explicitly states
    root causes, specific failed metrics, and recommended actions.
    """
    engine = CentralQualityEngine()
    project_id = uuid.uuid4()

    # Case 1: Failed model with phantom geometry & navigation disconnect
    failed_eval = engine.evaluate(
        project_id=project_id,
        model_version_id="model_failing_001",
        geometry_data={"phantom_geometry_count": 2, "plane_confidence": 0.85},
        navigation_data={"route_feasibility_ratio": 0.55, "disconnected_routes": ["Main Atrium -> Meeting Room B"]}
    )
    assert failed_eval.verdict == "FAIL"
    explanation = failed_eval.explanation
    
    # Must explain WHY:
    assert "FAIL" in explanation
    assert "critical hard failure" in explanation.lower()
    assert "phantom" in explanation.lower()
    assert "disconnected" in explanation.lower()
    assert len(failed_eval.recommended_actions) >= 1
    assert any("phantom" in act.lower() or "corridor" in act.lower() for act in failed_eval.recommended_actions)

    # Case 2: Clean model with PASS verdict
    passed_eval = engine.evaluate(
        project_id=project_id,
        model_version_id="model_passing_001",
        capture_data={"blur_score": 0.92, "exposure_score": 0.90, "coverage_fraction": 0.95, "overlap_ratio": 0.88},
        pose_data={"reprojection_error_px": 0.90, "tracking_continuity_ratio": 0.99, "loop_closure_detected": True, "loop_closure_residual_m": 0.02, "mean_pose_confidence": 0.94},
        depth_data={"consistency_ratio": 0.90, "density_pts_per_m3": 1400.0, "hole_fraction": 0.03},
        geometry_data={"plane_confidence": 0.90, "corner_integrity_score": 0.92, "disconnected_geometry_count": 0, "phantom_geometry_count": 0, "structural_consistency_score": 0.92},
        semantics_data={"mean_object_confidence": 0.88, "room_confidence": 0.92, "unclassified_ratio": 0.08},
        navigation_data={"floor_continuity_ratio": 0.96, "obstacle_validity_ratio": 0.94, "route_feasibility_ratio": 1.00, "wheelchair_ada_compliant": True}
    )
    assert passed_eval.verdict == "PASS"
    pass_explanation = passed_eval.explanation
    assert "PASS" in pass_explanation
    assert "zero hard failures" in pass_explanation.lower()
    assert "approved for production" in passed_eval.recommended_actions[0].lower()
