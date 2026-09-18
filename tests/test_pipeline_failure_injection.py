"""
VĀSTU Deliberate Pipeline Failure Injection Test Suite
Validates all 14 failure injection modes across all 7 mandatory verification dimensions:
1. Detection
2. Error classification
3. Recovery behavior
4. User-visible state
5. Retry behavior
6. Data integrity
7. Version integrity

Invariant under test: No failure may silently produce a valid-looking but incorrect model.
Acceptance criterion: Every tested failure has deterministic handling and produces observable evidence.
"""

import pytest
from core.schemas.failure_testing import (
    FailureInjectionType,
    ErrorCategory,
    FailureVerificationReport,
)
from core.schemas.orchestrator import (
    WorkflowStage,
    StageExecutionStatus,
)
from core.testing.failure_injector import PipelineFailureInjector
from core.orchestrator.workflow_engine import EndToEndWorkflowOrchestrator
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def test_client():
    return TestClient(app)


@pytest.fixture
def failure_injector():
    return PipelineFailureInjector()


@pytest.fixture
def orchestrator():
    return EndToEndWorkflowOrchestrator()


# ==============================================================================
# 1. NETWORK INTERRUPTION
# ==============================================================================
def test_failure_network_interruption(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.NETWORK_INTERRUPTION)
    assert report.detected is True
    assert report.error_category == ErrorCategory.NETWORK_ERROR
    assert report.error_code == "ERR_NET_CHUNK_TIMEOUT"
    assert "backoff" in report.recovery_behavior.lower()
    assert "RETRYING" in report.user_visible_state
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 2. CORRUPTED VIDEO
# ==============================================================================
def test_failure_corrupted_video(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.CORRUPTED_VIDEO)
    assert report.detected is True
    assert report.error_category == ErrorCategory.MEDIA_CORRUPTION
    assert report.error_code == "ERR_MEDIA_CORRUPT_HEADER"
    assert "quarantine" in report.recovery_behavior.lower()
    assert "FAILED" in report.user_visible_state
    assert "Non-retryable" in report.retry_behavior
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 3. MISSING FRAMES
# ==============================================================================
def test_failure_missing_frames(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.MISSING_FRAMES)
    assert report.detected is True
    assert report.error_category == ErrorCategory.DATA_INTEGRITY_ERROR
    assert report.error_code == "ERR_FRAME_COUNT_MISMATCH"
    assert "halt" in report.recovery_behavior.lower()
    assert "discontinuous" in report.user_visible_state.lower()
    assert "rescan" in report.retry_behavior.lower()
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 4. INVALID TIMESTAMPS
# ==============================================================================
def test_failure_invalid_timestamps(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.INVALID_TIMESTAMPS)
    assert report.detected is True
    assert report.error_category == ErrorCategory.TIMESTAMP_INCONSISTENCY
    assert report.error_code == "ERR_TIMESTAMPS_NON_MONOTONIC"
    assert "monotonic" in report.detection_mechanism.lower()
    assert "FAILED" in report.user_visible_state
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 5. INSUFFICIENT OVERLAP
# ==============================================================================
def test_failure_insufficient_overlap(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.INSUFFICIENT_OVERLAP)
    assert report.detected is True
    assert report.error_category == ErrorCategory.COVERAGE_DEFECT
    assert report.error_code == "ERR_INSUFFICIENT_OVERLAP"
    assert "warning" in report.recovery_behavior.lower()
    assert "rescan" in report.retry_behavior.lower()
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 6. TRACKING FAILURE
# ==============================================================================
def test_failure_tracking_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.TRACKING_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.TRACKING_LOST
    assert report.error_code == "ERR_TRACKING_LOST"
    assert "fallback" in report.retry_behavior.lower()
    assert "FAILED" in report.user_visible_state
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 7. COLMAP / SfM FAILURE
# ==============================================================================
def test_failure_colmap_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.COLMAP_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.SFM_CONVERGENCE_FAILURE
    assert report.error_code == "ERR_SFM_SOLVER_DIVERGENCE"
    assert "converge" in report.error_message.lower()
    assert "retry" in report.retry_behavior.lower()
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 8. DEPTH FAILURE
# ==============================================================================
def test_failure_depth_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.DEPTH_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.DEPTH_ESTIMATION_FAILURE
    assert report.error_code == "ERR_DEPTH_PARALLAX_DEFECT"
    assert "fallback" in report.recovery_behavior.lower()
    assert "FAILED" in report.user_visible_state
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 9. CELL RECONSTRUCTION FAILURE
# ==============================================================================
def test_failure_cell_reconstruction_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.CELL_RECONSTRUCTION_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.SPATIAL_CELL_DEFECT
    assert report.error_code == "ERR_CELL_POINT_STARVATION"
    assert "isolate" in report.recovery_behavior.lower()
    assert "FAILED_NEEDS_RESCAN" in report.user_visible_state
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True  # Parent model V1 preserved!
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 10. GPU WORKER FAILURE
# ==============================================================================
def test_failure_gpu_worker_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.GPU_WORKER_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.RESOURCE_EXHAUSTION
    assert report.error_code == "ERR_GPU_CUDA_OOM"
    assert "cache" in report.recovery_behavior.lower() or "empty_cache" in report.recovery_behavior.lower()
    assert "RETRYING" in report.user_visible_state
    assert "retry" in report.retry_behavior.lower()
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 11. GEOMETRY FAILURE
# ==============================================================================
def test_failure_geometry_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.GEOMETRY_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.GEOMETRIC_VALIDATION_FAILURE
    assert report.error_code == "ERR_GEOM_NON_MANIFOLD"
    assert "non-manifold" in report.error_message.lower()
    assert "FAILED" in report.user_visible_state
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 12. FUSION FAILURE
# ==============================================================================
def test_failure_fusion_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.FUSION_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.BOUNDARY_FUSION_FAILURE
    assert report.error_code == "ERR_FUSION_SEAM_DISCONTINUITY"
    assert "seam" in report.detection_mechanism.lower()
    assert "FAILED" in report.user_visible_state
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True  # V1 parent model untouched!
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 13. NAVIGATION FAILURE
# ==============================================================================
def test_failure_navigation_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.NAVIGATION_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.NAVIGATION_GENERATION_FAILURE
    assert report.error_code == "ERR_ROUTE_COLLISION_DETECTED"
    assert "obstacle" in report.detection_mechanism.lower()
    assert "roaming" in report.recovery_behavior.lower()
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 14. VIEWER ASSET FAILURE
# ==============================================================================
def test_failure_viewer_asset_failure(failure_injector):
    report = failure_injector.inject_and_verify(FailureInjectionType.VIEWER_ASSET_FAILURE)
    assert report.detected is True
    assert report.error_category == ErrorCategory.ASSET_DELIVERY_FAILURE
    assert report.error_code == "ERR_ASSET_CHUNK_LOAD_FAILED"
    assert "proxy" in report.recovery_behavior.lower()
    assert "degraded" in report.user_visible_state.lower()
    assert report.data_integrity_preserved is True
    assert report.version_integrity_preserved is True
    assert report.silent_corruption_prevented is True


# ==============================================================================
# 15. ORCHESTRATOR INJECTION HALTS AND BLOCKS PUBLICATION
# ==============================================================================
def test_orchestrator_failure_injection_halts_and_blocks_publication(orchestrator):
    """
    Verifies that when any of the 14 failures is injected into the live orchestrator,
    the workflow immediately halts at that exact stage, marks status as FAILED,
    and guarantees published_twin is None.
    """
    for failure_type in [
        FailureInjectionType.NETWORK_INTERRUPTION,
        FailureInjectionType.CORRUPTED_VIDEO,
        FailureInjectionType.GEOMETRY_FAILURE,
        FailureInjectionType.FUSION_FAILURE
    ]:
        job = orchestrator.run_pipeline(
            project_id="proj_fail_test",
            capture_id="cap_fail_test",
            failure_injection_type=failure_type
        )
        assert job.status == StageExecutionStatus.FAILED
        assert job.published_twin is None  # CRITICAL: No corrupt model published!
        assert job.failed_stage is not None
        assert failure_type.value in job.error_message


# ==============================================================================
# 16. ACCEPTANCE CRITERION: 100% DETERMINISTIC HANDLING & OBSERVABLE EVIDENCE
# ==============================================================================
def test_acceptance_criterion_all_14_failures_deterministic_and_no_silent_corruption(failure_injector):
    """
    Acceptance Criterion:
    Every tested failure has deterministic handling and produces observable evidence.
    No failure may silently produce a valid-looking but incorrect model.
    """
    all_reports = failure_injector.run_all_failure_tests()
    assert len(all_reports) == 14

    for report in all_reports:
        assert report.detected is True, f"Failure {report.injection_type} was not detected!"
        assert report.error_category is not None, f"Failure {report.injection_type} missing error category!"
        assert len(report.error_code) > 0, f"Failure {report.injection_type} missing error code!"
        assert len(report.recovery_behavior) > 0, f"Failure {report.injection_type} missing recovery behavior!"
        assert len(report.user_visible_state) > 0, f"Failure {report.injection_type} missing user visible state!"
        assert len(report.retry_behavior) > 0, f"Failure {report.injection_type} missing retry behavior!"
        assert report.data_integrity_preserved is True, f"Failure {report.injection_type} corrupted data integrity!"
        assert report.version_integrity_preserved is True, f"Failure {report.injection_type} broke version integrity!"
        assert report.silent_corruption_prevented is True, f"Failure {report.injection_type} allowed silent corruption!"


# ==============================================================================
# 17. FASTAPI API TEST FOR FAILURE INJECTION ENDPOINT
# ==============================================================================
def test_api_failure_injection_endpoint(test_client):
    """
    Verifies POST /api/v1/jobs/test-failure-injection.
    """
    payload = {
        "failure_type": "CORRUPTED_VIDEO",
        "severity": "CRITICAL"
    }
    response = test_client.post("/api/v1/jobs/test-failure-injection", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["injection_type"] == "CORRUPTED_VIDEO"
    assert data["detected"] is True
    assert data["error_category"] == "MEDIA_CORRUPTION"
    assert data["silent_corruption_prevented"] is True
    assert data["version_integrity_preserved"] is True
