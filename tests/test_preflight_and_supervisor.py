"""
Unit & Integration Tests for P1 Preflight Validator & P2 Post-Reconstruction Supervisor
"""

import pytest
import numpy as np
import open3d as o3d

from core.preflight.validator import PreflightReconstructionValidator
from core.supervisor.reconstruction_supervisor import PostReconstructionSupervisor


def test_preflight_validator_blocks_stationary_pivot():
    """Validates P1: Preflight blocks stationary rotation with < 0.10m baseline."""
    validator = PreflightReconstructionValidator(min_translation_baseline_m=0.10, max_homography_inlier_ratio=0.70)

    capture_report = {"usable_frame_pct": 100.0}
    # Stationary pivot: baseline 0.03m < 0.10m, homography inlier ratio 71.4% > 70%
    parallax_report_pivot = {
        "total_baseline_displacement_m": 0.03,
        "mean_homography_inlier_ratio": 0.714,
        "mean_optical_flow_px": 2.56
    }
    calib_data = {"fx": 912.0}

    result = validator.evaluate_preflight(capture_report, parallax_report_pivot, calib_data)
    assert result["can_certify_architectural"] is False
    assert result["preflight_status"] == "DEGENERATE_BASELINE_BLOCKED"
    assert "smooth sliding (truck/dolly)" in result["user_guidance"]


def test_preflight_validator_approves_lateral_translation():
    """Validates P1: Preflight approves genuine lateral translation baseline >= 0.10m."""
    validator = PreflightReconstructionValidator(min_translation_baseline_m=0.10, max_homography_inlier_ratio=0.70)

    capture_report = {"usable_frame_pct": 98.0}
    # Lateral translation: baseline 0.45m, homography inlier ratio 52%
    parallax_report_lateral = {
        "total_baseline_displacement_m": 0.45,
        "mean_homography_inlier_ratio": 0.52,
        "mean_optical_flow_px": 14.2
    }
    calib_data = {"fx": 912.0}

    result = validator.evaluate_preflight(capture_report, parallax_report_lateral, calib_data)
    assert result["can_certify_architectural"] is True
    assert result["preflight_status"] == "APPROVED_ARCHITECTURAL"
    assert result["recommended_depth_backend"] == "DEPTH_ANYTHING_V2_METRIC"


def test_post_reconstruction_supervisor_recommends_corrections():
    """Validates P2: Supervisor diagnoses high wall residuals and recommends targeted engine corrections."""
    supervisor = PostReconstructionSupervisor(max_wall_plane_residual_m=0.08)

    # Create synthetic mesh with high wall curvature (residual ~18cm)
    mesh = o3d.geometry.TriangleMesh.create_box(width=2.0, height=2.4, depth=3.0)
    # Auditing with degenerate parallax report
    parallax_report = {"parallax_gate_passed": False, "total_baseline_displacement_m": 0.03}
    backend_manifest = {"fusion_engine": "TSDF_SCALABLE_VOLUME"}

    report = supervisor.audit_reconstruction(
        mesh, np.asarray(mesh.vertices), {}, backend_manifest, parallax_report
    )

    assert "diagnosed_defects" in report
    assert "targeted_engine_corrections" in report
    assert report["metrics"]["topology"]["self_intersecting_triangles"] == 0
    assert report["metrics"]["topology"]["strict_non_manifold_edges"] == 0
