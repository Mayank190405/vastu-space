"""
Test Suite for Stage 25: End-to-End Workflow Orchestrator
Covers:
1. Sequential execution of all 22 required pipeline stages
2. Observable monotonic 0-100% stage-level progress events
3. Error handling and early termination on injected stage failures
4. Acceptance Criterion: A new capture travels from mobile capture to published interactive digital twin
5. FastAPI control plane endpoints for orchestration and progress tracking
"""

import pytest
from fastapi.testclient import TestClient
from api.main import app
from core.orchestrator.workflow_engine import EndToEndWorkflowOrchestrator
from core.schemas.orchestrator import (
    WorkflowStage,
    WORKFLOW_STAGE_SEQUENCE,
    StageExecutionStatus,
    WorkflowProgressEvent,
    PublishedDigitalTwin,
    WorkflowJobStatus,
)


@pytest.fixture
def test_client():
    return TestClient(app)


def test_orchestrator_sequential_stage_execution():
    """Verify that all 22 mandated stages execute in exact sequence."""
    orchestrator = EndToEndWorkflowOrchestrator()
    job = orchestrator.run_pipeline(
        project_id="proj_alpha_01",
        capture_id="cap_delta_01",
        operator_id="op_tester_01"
    )

    assert job.status == StageExecutionStatus.COMPLETED
    assert job.overall_progress_pct == 100.0
    assert len(job.stage_history) == 44  # 22 stages * 2 events (STARTING + COMPLETED)

    # Verify stage execution order
    completed_events = [e for e in job.stage_history if e.status == StageExecutionStatus.COMPLETED]
    assert len(completed_events) == 22

    for idx, expected_stage in enumerate(WORKFLOW_STAGE_SEQUENCE):
        assert completed_events[idx].stage == expected_stage
        assert completed_events[idx].stage_index == idx + 1


def test_observable_progress_monotonicity():
    """Verify observable progress strictly increases from 0% to 100%."""
    observed_progress: list[float] = []
    observed_stages: list[WorkflowStage] = []

    def progress_callback(event: WorkflowProgressEvent):
        observed_progress.append(event.overall_progress_pct)
        observed_stages.append(event.stage)

    orchestrator = EndToEndWorkflowOrchestrator(progress_listener=progress_callback)
    job = orchestrator.run_pipeline()

    assert len(observed_progress) > 0
    assert observed_progress[0] == 0.0
    assert observed_progress[-1] == 100.0

    # Monotonicity check (non-decreasing)
    for i in range(1, len(observed_progress)):
        assert observed_progress[i] >= observed_progress[i - 1]

    # Check that all 22 stages were observed
    unique_stages = list(dict.fromkeys(observed_stages))
    assert len(unique_stages) == 22
    assert unique_stages == WORKFLOW_STAGE_SEQUENCE


def test_stage_failure_handling():
    """Verify pipeline halts immediately and marks job as FAILED when a stage throws an error."""
    orchestrator = EndToEndWorkflowOrchestrator()
    failure_stage = WorkflowStage.STRUCTURAL_RECONSTRUCTION

    job = orchestrator.run_pipeline(
        inject_failure_at_stage=failure_stage
    )

    assert job.status == StageExecutionStatus.FAILED
    assert job.failed_stage == failure_stage
    assert "Simulated execution failure" in job.error_message
    assert job.overall_progress_pct < 100.0
    assert job.published_twin is None

    # Subsequent stages should NOT have executed
    executed_stages = {e.stage for e in job.stage_history}
    assert WorkflowStage.WEB_VIEWER not in executed_stages
    assert WorkflowStage.NAVIGATION not in executed_stages


def test_acceptance_criterion_end_to_end_publish():
    """
    Acceptance Criterion:
    A new capture can travel from mobile capture to a published interactive digital twin
    through one orchestrated workflow without manual intervention.
    """
    orchestrator = EndToEndWorkflowOrchestrator()
    job = orchestrator.run_pipeline(
        project_id="proj_competition_01",
        capture_id="cap_arena_01",
        device_model="iPhone 15 Pro LiDAR"
    )

    assert job.status == StageExecutionStatus.COMPLETED
    assert job.overall_progress_pct == 100.0
    assert job.published_twin is not None

    twin = job.published_twin
    assert isinstance(twin, PublishedDigitalTwin)
    assert twin.model_version_id.startswith("mod_")
    assert "/dashboard/viewer" in twin.viewer_url
    assert "/delivery-manifest" in twin.delivery_manifest_url
    assert twin.visual_chunks_count > 0
    assert twin.collision_obstacles_count > 0
    assert twin.navigation_nodes_count > 0
    assert twin.pois_count > 0
    assert twin.quality_verdict == "PASS"


def test_api_orchestrated_job_endpoints(test_client):
    """Verify POST /api/v1/jobs/orchestrated and GET /api/v1/jobs/{job_id}/progress."""
    payload = {
        "project_id": "proj_api_test",
        "capture_id": "cap_api_test",
        "operator_id": "op_test_user",
        "device_model": "iPad Pro LiDAR",
        "async_mode": False
    }

    # 1. Start orchestrated pipeline synchronously
    response = test_client.post("/api/v1/jobs/orchestrated", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["status"] == "COMPLETED"
    assert data["overall_progress_pct"] == 100.0
    assert "published_twin" in data
    assert data["published_twin"]["visual_chunks_count"] > 0

    job_id = data["job_id"]

    # 2. Query progress endpoint
    progress_res = test_client.get(f"/api/v1/jobs/{job_id}/progress")
    assert progress_res.status_code == 200

    progress_data = progress_res.json()
    assert progress_data["job_id"] == job_id
    assert progress_data["status"] == "COMPLETED"
    assert progress_data["overall_progress_pct"] == 100.0
    assert len(progress_data["stage_history"]) == 44
