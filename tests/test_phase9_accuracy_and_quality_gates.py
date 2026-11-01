"""
VĀSTU Phase 9 Automated Quality & Accuracy Verification Suite:
Production-Ready Digital Twins, AI Optimization & Automated Quality Gates
Validates:
1. Pose Refinement Optimizer & Scale Consistency Validation (<= 3% deviation)
2. Normal-Guided Depth Fusion Optimizer (DSINE edge halo pruning)
3. Precision Architectural Geometry Optimizer (Wall fit RMS <= 1.5 cm, Corner dev <= 1.0 deg, Coverage >= 90%)
4. Gaussian Quality Optimizer (Floater pruning & held-out PSNR >= 28 dB / SSIM >= 0.88)
5. Multi-Tier SPZ Optimization Pipeline (Desktop 60 FPS vs Mobile 30 FPS tiers)
6. Cross-Session Room Alignment Validator & Doorway Threshold Gating
7. Automated Collision Penetration Regression (Zero wall penetrations, traversable doorways, furniture blocked)
8. Navmesh Graph Full Connectivity & ADA Accessibility
9. Quality Report Generator & Central Governance Publishing Locks
"""

import os
import sys
import json
import tempfile
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.reconstruction.pose_optimizer import PoseRefinementOptimizer
from core.reconstruction.depth_fusion_optimizer import DepthFusionOptimizer
from core.reconstruction.architectural_optimizer import ArchitecturalGeometryOptimizer
from core.reconstruction.gaussian_quality_optimizer import GaussianQualityOptimizer
from core.reconstruction.spz_optimization_pipeline import SPZOptimizationPipeline

from core.quality.pose_consistency_validator import PoseConsistencyValidator
from core.quality.geometry_accuracy_validator import GeometryAccuracyValidator
from core.quality.room_alignment_validator import RoomAlignmentValidator
from core.quality.navigation_validation_engine import NavigationValidationEngine
from core.quality.quality_report_generator import QualityReportGenerator
from core.quality.reconstruction_quality_evaluator import ReconstructionQualityEvaluator


# ==============================================================================
# 1. Pose Refinement & Consistency Gate
# ==============================================================================
def test_pose_refinement_and_consistency_gate():
    optimizer = PoseRefinementOptimizer(max_reprojection_rmse_px=1.8, scale_tolerance_ratio=0.03)
    validator = PoseConsistencyValidator(max_reprojection_rmse_px=1.8, max_scale_deviation_ratio=0.03)

    # Synthetic trajectory forming a loop: (0,0) -> (2,0) -> (2,2) -> (0,2) -> (0,0)
    poses = []
    coords = [
        [0.0, 0.0, 1.5], [1.0, 0.0, 1.5], [2.0, 0.0, 1.5],
        [2.0, 1.0, 1.5], [2.0, 2.0, 1.5],
        [1.0, 2.0, 1.5], [0.0, 2.0, 1.5],
        [0.0, 1.0, 1.5], [0.03, 0.02, 1.5] # Loop closure near start
    ]
    for idx, pt in enumerate(coords):
        poses.append({
            "timestamp": float(idx * 6.0), # Realistic 48-second room boundary walk
            "position": pt,
            "quaternion": [1.0, 0.0, 0.0, 0.0]
        })

    opt_res = optimizer.optimize_trajectory(poses, loop_closures=[(0, 8)])
    assert opt_res["status"] == "OPTIMIZED"
    assert opt_res["loop_closure_count"] >= 1
    assert opt_res["is_scale_consistent"] is True

    val_res = validator.validate_pose_optimization(opt_res)
    assert val_res["status"] == "PASSED"
    assert val_res["is_passed"] is True
    assert val_res["checks"]["meets_scale_preservation"] is True


# ==============================================================================
# 2. Depth Fusion & Normal-Guided Edge Pruning
# ==============================================================================
def test_depth_fusion_and_normal_pruning():
    optimizer = DepthFusionOptimizer(min_confidence_threshold=0.55)

    # 100x100 synthetic depth map with a sharp step discontinuity (halo artifact)
    depth = np.full((100, 100), 2.0, dtype=np.float32)
    depth[:, 50:] = 5.0 # Sharp 3-meter edge

    confidence = np.full((100, 100), 0.85, dtype=np.float32)
    confidence[90:, :] = 0.20 # Low confidence boundary

    # Normal map with back-face artifact on right side
    normals = np.zeros((100, 100, 3), dtype=np.float32)
    normals[:, :50] = [0.0, 0.0, -1.0] # Valid camera-facing
    normals[:, 50:] = [0.0, 0.0, 0.90] # Facing away from camera

    res = optimizer.filter_and_fuse_depth_maps([depth], [confidence], [normals])
    assert res["status"] == "OPTIMIZED"
    assert res["pruned_pixel_ratio"] > 0.40 # Successfully pruned edge halos and back-faces
    assert res["filtered_depth_maps"][0][95, 10] == 0.0 # Low confidence pruned


# ==============================================================================
# 3. Precision Architectural Geometry Targets
# ==============================================================================
def test_precision_architectural_geometry_targets():
    opt = ArchitecturalGeometryOptimizer(
        max_wall_rmse_m=0.015,
        max_corner_ortho_dev_deg=1.0,
        max_dimension_error_m=0.030,
        min_structural_coverage_ratio=0.90
    )
    val = GeometryAccuracyValidator()

    # Room 1: High-precision rectangular room (4.0m x 5.0m)
    rect_room = {
        "room_id": "room_rect",
        "room_name": "Living Room",
        "boundary_polygon_2d": [[-2.0, -2.5], [2.0, -2.5], [2.0, 2.5], [-2.0, 2.5]],
        "ceiling_height_m": 2.80,
        "walls": [
            {"wall_id": "w1", "length_m": 4.0},
            {"wall_id": "w2", "length_m": 5.0},
            {"wall_id": "w3", "length_m": 4.0},
            {"wall_id": "w4", "length_m": 5.0}
        ],
        "doorways": [{"id": "d1", "width_m": 0.90, "height_m": 2.10}],
        "quality_report": {"perimeter_m": 18.0, "area_sqm": 20.0}
    }

    gt_rect = {"width_m": 4.0, "length_m": 5.0, "height_m": 2.80}
    res_rect = opt.optimize_room_geometry(rect_room, gt_rect)
    assert res_rect["status"] == "PASSED"
    assert res_rect["metrics"]["wall_fit_rmse_cm"] <= 1.5
    assert res_rect["metrics"]["corner_ortho_dev_deg"] <= 1.0
    assert res_rect["metrics"]["dimension_error_cm"] <= 3.0
    assert res_rect["metrics"]["structural_coverage_pct"] >= 90.0

    val_rect = val.validate_geometry(res_rect)
    assert val_rect["status"] == "PASSED"
    assert val_rect["is_passed"] is True

    # Room 2: Irregular L-shaped room (6 vertices) - verify irregular geometry is preserved without false penalty
    l_poly = [[0, 0], [5, 0], [5, 2], [2, 2], [2, 4], [0, 4]]
    l_room = {
        "room_id": "room_l",
        "room_name": "L-Suite",
        "boundary_polygon_2d": l_poly,
        "ceiling_height_m": 2.80,
        "walls": [
            {"wall_id": f"w_{i}", "length_m": 2.0} for i in range(6)
        ],
        "doorways": [{"id": "d1", "width_m": 0.90, "height_m": 2.10}],
        "quality_report": {"perimeter_m": 18.0, "area_sqm": 14.0}
    }
    res_l = opt.optimize_room_geometry(l_room)
    assert res_l["is_irregular_layout"] is True
    val_l = val.validate_geometry(res_l)
    assert val_l["is_irregular_layout"] is True


# ==============================================================================
# 4. Gaussian Splatting Quality & Held-Out View
# ==============================================================================
def test_gaussian_quality_and_held_out_view():
    opt = GaussianQualityOptimizer(target_min_psnr_db=28.0, target_min_ssim=0.88)

    # Initial splats containing valid points + floating noise + low-opacity artifacts
    positions = np.array([
        [0.0, 0.0, 1.0],
        [1.0, 1.0, 1.0],
        [100.0, 100.0, 50.0], # Distant floater
        [0.5, 0.5, 0.5]
    ], dtype=np.float32)

    scales = np.full((4, 3), -3.0, dtype=np.float32)
    scales[2] = 2.0 # Huge scale on floater
    rotations = np.zeros((4, 4), dtype=np.float32)
    rotations[:, 0] = 1.0

    opacities = np.array([[2.5], [2.0], [0.1], [-5.0]], dtype=np.float32) # last is low opacity
    sh_dc = np.full((4, 3), 0.5, dtype=np.float32)

    gaussians = {
        "positions": positions,
        "scales": scales,
        "rotations": rotations,
        "opacities": opacities,
        "sh_dc": sh_dc
    }

    prune_res = opt.optimize_and_prune_splats(gaussians, room_bounds=([-5, -5, 0], [5, 5, 3]))
    assert prune_res["status"] == "OPTIMIZED"
    assert prune_res["pruned_floaters_count"] == 2
    assert prune_res["optimized_splat_count"] == 2

    # Held-out view evaluation
    gt_frame = np.full((120, 160, 3), 180, dtype=np.uint8)
    rendered_frame = np.full((120, 160, 3), 182, dtype=np.uint8) # Slight noise
    eval_res = opt.evaluate_held_out_view(gt_frame, rendered_frame)
    assert eval_res["psnr_db"] >= 35.0
    assert eval_res["ssim"] >= 0.90
    assert eval_res["is_photorealistic"] is True


# ==============================================================================
# 5. Multi-Tier SPZ Optimization Pipeline
# ==============================================================================
def test_spz_optimization_pipeline():
    pipe = SPZOptimizationPipeline()
    points = np.random.uniform(-2, 2, (1500, 3)).astype(np.float32)
    scales = np.full((1500, 3), -3.0, dtype=np.float32)
    rotations = np.zeros((1500, 4), dtype=np.float32)
    rotations[:, 0] = 1.0
    opacities = np.random.uniform(0.5, 3.0, (1500, 1)).astype(np.float32)
    sh_dc = np.random.uniform(-0.5, 0.5, (1500, 3)).astype(np.float32)

    gaussians = {
        "positions": points,
        "scales": scales,
        "rotations": rotations,
        "opacities": opacities,
        "sh_dc": sh_dc
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        res = pipe.build_multi_tier_spz(gaussians, tmpdir, "facility")
        assert os.path.exists(res["desktop_tier"]["path"])
        assert os.path.exists(res["mobile_tier"]["path"])
        assert res["mobile_tier"]["splat_count"] < res["desktop_tier"]["splat_count"]
        assert res["mobile_tier"]["file_size_bytes"] < res["desktop_tier"]["file_size_bytes"]
        assert res["size_reduction_ratio"] >= 0.35


# ==============================================================================
# 6. Room Alignment Validator & Governance
# ==============================================================================
def test_room_alignment_validator():
    validator = RoomAlignmentValidator(
        min_alignment_confidence=0.70,
        max_alignment_rmse_m=0.050,
        max_doorway_width_delta_m=0.150
    )

    # Valid Alignment
    good_alignment = {
        "confidence": 0.92,
        "rmse_m": 0.018,
        "doorway_width_delta_m": 0.02,
        "inlier_ratio": 0.88
    }
    good_res = validator.validate_pairwise_alignment(good_alignment)
    assert good_res["status"] == "PASSED"
    assert good_res["recommendation"] == "APPROVED_FOR_MERGE"

    # Ambiguous Alignment -> Manual Review
    review_alignment = {
        "confidence": 0.72,
        "rmse_m": 0.065, # slightly high RMSE
        "doorway_width_delta_m": 0.05,
        "inlier_ratio": 0.65
    }
    review_res = validator.validate_pairwise_alignment(review_alignment)
    assert review_res["status"] == "REQUIRES_MANUAL_REVIEW"

    # Severe Mismatch -> Rescan Trigger
    bad_alignment = {
        "confidence": 0.35,
        "rmse_m": 0.180,
        "doorway_width_delta_m": 0.45, # Door mismatch
        "inlier_ratio": 0.30
    }
    bad_res = validator.validate_pairwise_alignment(bad_alignment)
    assert bad_res["status"] == "REQUIRES_RESCAN"
    assert bad_res["recommendation"] == "RESCAN_DOORWAY_TRANSITION"


# ==============================================================================
# 7. Automated Collision Penetration & Navmesh Connectivity
# ==============================================================================
def test_collision_penetration_and_navmesh_connectivity():
    engine = NavigationValidationEngine(player_radius_m=0.35)

    room_col = [{
        "room_id": "r1",
        "walkable_boundary_polygon_2d": [[-2, -2], [2, -2], [2, 2], [-2, 2]],
        "wall_colliders": [
            {"collider_id": "w1", "p0": [-2, -2], "p1": [2, -2], "thickness_m": 0.15},
            {"collider_id": "w2", "p0": [2, -2], "p1": [2, 2], "thickness_m": 0.15},
            {"collider_id": "w3", "p0": [2, 2], "p1": [-2, 2], "thickness_m": 0.15},
            {"collider_id": "w4", "p0": [-2, 2], "p1": [-2, -2], "thickness_m": 0.15}
        ],
        "furniture_colliders": [
            {"collider_id": "bed1", "center_3d": [0, 0, 0.5], "dimensions_m": [1.5, 1.8, 0.9]}
        ]
    }]

    doorways = [{"doorway_id": "door1", "width_m": 0.90}]

    col_res = engine.run_collision_regression_suite(room_col, doorways)
    assert col_res["status"] == "PASSED"
    assert col_res["is_collision_watertight"] is True
    assert col_res["is_doorway_traversable"] is True
    assert len(col_res["penetration_failures"]) == 0

    # NavMesh Graph Connectivity
    navmesh = {
        "nodes": [
            {"node_id": "n1", "is_accessible": True},
            {"node_id": "n2", "is_accessible": True},
            {"node_id": "d1", "is_accessible": True}
        ],
        "edges": [
            {"source_node": "n1", "target_node": "d1", "is_doorway": True},
            {"source_node": "d1", "target_node": "n2", "is_doorway": True}
        ]
    }
    nav_res = engine.validate_navmesh_connectivity(navmesh)
    assert nav_res["status"] == "PASSED"
    assert nav_res["is_connected"] is True


# ==============================================================================
# 8. End-to-End Quality Report & Publishing Lock Gates
# ==============================================================================
def test_end_to_end_quality_report_and_publishing_locks():
    evaluator = ReconstructionQualityEvaluator()

    pose_res = {"mean_reprojection_rmse_px": 0.95, "scale_consistency_ratio": 0.012, "drift_rate_m_per_min": 0.015, "drift_correction_m": 0.01}
    geom_res = {
        "metrics": {"wall_fit_rmse_cm": 1.2, "corner_ortho_dev_deg": 0.6, "dimension_error_cm": 1.5, "structural_coverage_pct": 96.5},
        "is_irregular_layout": False
    }
    gaussian_res = {"psnr_db": 31.4, "ssim": 0.91, "is_photorealistic": True}
    col_data = [{
        "room_id": "test_room",
        "walkable_boundary_polygon_2d": [[-2, -2], [2, -2], [2, 2], [-2, 2]],
        "wall_colliders": [{"collider_id": "w1", "p0": [-2, -2], "p1": [2, -2], "thickness_m": 0.15}],
        "furniture_colliders": []
    }]
    doors = [{"doorway_id": "d1", "width_m": 0.90}]
    align_res = {"confidence": 0.90, "rmse_m": 0.018, "doorway_width_delta_m": 0.02, "inlier_ratio": 0.85}

    with tempfile.TemporaryDirectory() as tmpdir:
        report = evaluator.evaluate_room(
            room_id="room_gold",
            room_name="Executive Lounge",
            pose_result=pose_res,
            geometry_result=geom_res,
            gaussian_eval_result=gaussian_res,
            collision_data=col_data,
            doorways=doors,
            alignment_result=align_res,
            save_report_dir=tmpdir
        )

        assert report["verdict"] == "PASSED"
        assert report["can_publish"] is True
        assert report["composite_score"] >= 90.0
        assert os.path.exists(os.path.join(tmpdir, "quality_report_room_gold.json"))

        # Test Publishing Lock Gate: Corrupted / Defective Room MUST be blocked
        bad_geom_res = {
            "metrics": {"wall_fit_rmse_cm": 4.5, "corner_ortho_dev_deg": 5.0, "dimension_error_cm": 12.0, "structural_coverage_pct": 65.0},
            "is_irregular_layout": False
        }
        bad_report = evaluator.evaluate_room(
            room_id="room_broken",
            room_name="Defective Scan",
            pose_result=pose_res,
            geometry_result=bad_geom_res,
            gaussian_eval_result=gaussian_res,
            collision_data=col_data,
            doorways=doors,
            alignment_result=align_res
        )
        assert bad_report["verdict"] == "REQUIRES_RESCAN"
        assert bad_report["can_publish"] is False  # Strictly blocked from automatic publication!


if __name__ == "__main__":
    tests = [
        test_pose_refinement_and_consistency_gate,
        test_depth_fusion_and_normal_pruning,
        test_precision_architectural_geometry_targets,
        test_gaussian_quality_and_held_out_view,
        test_spz_optimization_pipeline,
        test_room_alignment_validator,
        test_collision_penetration_and_navmesh_connectivity,
        test_end_to_end_quality_report_and_publishing_locks
    ]
    passed = 0
    print("=" * 65)
    print("🚀 Running VĀSTU Phase 9 Accuracy, Optimization & Quality Gates Suite")
    print("=" * 65)
    for t in tests:
        try:
            t()
            passed += 1
            print(f"  ✅ PASS: {t.__name__}")
        except Exception as e:
            print(f"  ❌ FAIL: {t.__name__}: {e}")
            import traceback
            traceback.print_exc()

    print("=" * 65)
    print(f"📊 Results: {passed}/{len(tests)} Phase 9 quality verification tests passed")
    print("=" * 65)
    if passed != len(tests):
        exit(1)
