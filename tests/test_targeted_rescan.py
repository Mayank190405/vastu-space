"""
Test Suite: Targeted Rescan Task Generation & Localized Reconstruction
Verifies:
1. Automated 10-step targeted rescan workflow:
   - Identify failure region & reason
   - Calculate required additional observations
   - Generate Contract 12 rescan task
   - Send to mobile & guide user with visual HUD + TTS
   - Upload delta data only
   - Reconstruct affected cells locally (ZERO global building re-run)
   - Validate cell boundaries & fuse into existing model
2. Contract 12 mandated fields:
   - cell_id, region, reason, priority, required_capture_action, expected_improvement
3. Acceptance Criterion:
   A local failure creates a specific, actionable rescan instead of a generic "scan again" message.
"""

import pytest
import uuid
import numpy as np

from core.schemas.rescan_request import RescanRequest, RescanRegion, RequiredCaptureAction, ExpectedImprovement
from core.quality.rescan_generator import TargetedRescanGenerator
from core.capture.rescan_guidance import MobileRescanCoordinator
from core.quality.targeted_integrator import TargetedCellIntegrator
from core.spatial.cell import SpatialCellModel
from core.spatial.lifecycle import SpatialCellLifecycleManager

def test_defect_specific_rescan_task_generation():
    """Validates that different QA failure modes produce customized capture patterns."""
    generator = TargetedRescanGenerator()
    project_id = uuid.uuid4()
    cell_id = "cell_meeting_room_2"
    region = {
        "center_xyz": [6.0, 4.0, 1.2],
        "min_xyz": [4.5, 2.5, 0.0],
        "max_xyz": [7.5, 5.5, 2.8],
        "room_id": "Meeting Room 2"
    }

    # 1. Hole defect -> Downward 45° corner pattern
    hole_task = generator.generate_rescan_task(
        project_id=project_id,
        cell_id=cell_id,
        region_bounds=region,
        defect_type="HOLE",
        detailed_reason="Surface gap detected in north-east corner wall base",
        current_metric_value=0.28,
        priority="HIGH"
    )
    assert hole_task.required_capture_action.capture_pattern == "CORNER_DOWNWARD_45"
    assert hole_task.required_capture_action.camera_pitch_deg == -45.0
    assert hole_task.expected_improvement.target_metric == "hole_fraction"
    assert hole_task.expected_improvement.target_value <= 0.05

    # 2. Low density defect -> Orbital sweep
    density_task = generator.generate_rescan_task(
        project_id=project_id,
        cell_id=cell_id,
        region_bounds=region,
        defect_type="LOW_DENSITY",
        detailed_reason="Point cloud density is 110 pts/m³ across conference table area",
        current_metric_value=110.0,
        priority="CRITICAL"
    )
    assert density_task.required_capture_action.capture_pattern == "ORBIT_SWEEP"
    assert density_task.required_capture_action.recommended_camera_distance_m == 1.5
    assert density_task.expected_improvement.target_metric == "point_density_pts_m3"
    assert density_task.expected_improvement.target_value >= 800.0

    # 3. Motion blur defect -> Standoff wall at slower speed
    blur_task = generator.generate_rescan_task(
        project_id=project_id,
        cell_id=cell_id,
        region_bounds=region,
        defect_type="BLUR",
        detailed_reason="Excessive camera rotational velocity during wall sweep",
        current_metric_value=0.42,
        priority="MEDIUM"
    )
    assert blur_task.required_capture_action.capture_pattern == "STANDOFF_WALL"
    assert blur_task.required_capture_action.camera_pitch_deg == 0.0
    assert blur_task.expected_improvement.target_metric == "blur_score"

def test_contract_12_mandated_fields_present():
    """Validates that all required fields are present and type-safe in Contract 12."""
    generator = TargetedRescanGenerator()
    task = generator.generate_rescan_task(
        project_id=uuid.uuid4(),
        cell_id="cell_corridor_north",
        region_bounds={"center_xyz": [0, 5, 1.2], "room_id": "Corridor"},
        defect_type="DISCONNECTED_WALL",
        detailed_reason="Wall corner junction unconstrained without floor junction",
        current_metric_value=1.0,
        priority="HIGH"
    )

    # Validate all 6 prompt requirements
    assert task.cell_id == "cell_corridor_north"
    assert isinstance(task.region, RescanRegion)
    assert len(task.reason) > 10
    assert task.priority in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert isinstance(task.required_capture_action, RequiredCaptureAction)
    assert isinstance(task.expected_improvement, ExpectedImprovement)

    # Validate numeric and structural bounds
    assert task.region.volume_m3 is not None and task.region.volume_m3 > 0
    assert len(task.required_capture_action.recommended_waypoints) >= 3
    assert task.expected_improvement.expected_confidence_gain > 0.0

def test_acceptance_criterion_actionable_guidance_vs_generic_message():
    """
    Acceptance Criterion:
    A local failure creates a specific, actionable rescan instead of a generic 'scan again' message.
    """
    generator = TargetedRescanGenerator()
    task = generator.generate_rescan_task(
        project_id=uuid.uuid4(),
        cell_id="cell_executive_corner",
        region_bounds={"center_xyz": [12.0, 8.0, 1.2], "room_id": "Executive Suite"},
        defect_type="SPECULAR_PHANTOM",
        detailed_reason="Mirror reflection created false floating geometry behind conference board",
        current_metric_value=2.0,
        priority="CRITICAL"
    )

    action = task.required_capture_action
    visual_text = action.visual_instruction
    audio_text = action.audio_tts_prompt

    # Negative check: Must NEVER contain lazy generic advice
    assert "scan again" not in visual_text.lower()
    assert "retake scan" not in visual_text.lower()
    assert "scan again" not in audio_text.lower()
    assert "retake scan" not in audio_text.lower()

    # Positive check: Must contain specific actionable metrics (angles, distances, physical action)
    assert "30°" in visual_text or "30" in visual_text or "oblique" in visual_text.lower() or "angle" in visual_text.lower()
    assert action.recommended_camera_distance_m > 0
    assert len(action.recommended_waypoints) > 0
    assert task.expected_improvement.current_value == 2.0
    assert task.expected_improvement.target_value == 0.0

def test_localized_cell_reconstruction_and_fusion_bypasses_global_rebuild():
    """
    Validates end-to-end steps 5-10:
    - Mobile dispatch & delta upload
    - Reconstructing ONLY the affected cell (bypassing global building rebuild)
    - Boundary validation and seamless model fusion
    """
    # 1. Setup spatial lifecycle with 3 cells
    cell_a = SpatialCellModel(
        cell_id="cell_entrance",
        coordinates=(0, 0, 0),
        origin_world=np.array([0.0, 0.0, 0.0]),
        cell_size_m=4.0
    )
    cell_a.points_world = np.random.rand(200, 3) * 4.0
    cell_a.colors = np.ones((200, 3), dtype=np.uint8) * 180
    cell_a.normals = np.zeros((200, 3))
    cell_a.confidences = np.ones(200) * 0.95

    cell_b_failing = SpatialCellModel(
        cell_id="cell_lobby_failing",
        coordinates=(1, 0, 0),
        origin_world=np.array([4.0, 0.0, 0.0]),
        cell_size_m=4.0
    )
    cell_b_failing.points_world = np.random.rand(40, 3) * 4.0 + np.array([4.0, 0.0, 0.0])
    cell_b_failing.colors = np.ones((40, 3), dtype=np.uint8) * 120
    cell_b_failing.normals = np.zeros((40, 3))
    cell_b_failing.confidences = np.ones(40) * 0.35  # Low confidence

    cell_c = SpatialCellModel(
        cell_id="cell_corridor",
        coordinates=(2, 0, 0),
        origin_world=np.array([8.0, 0.0, 0.0]),
        cell_size_m=4.0
    )
    cell_c.points_world = np.random.rand(250, 3) * 4.0 + np.array([8.0, 0.0, 0.0])
    cell_c.colors = np.ones((250, 3), dtype=np.uint8) * 190
    cell_c.normals = np.zeros((250, 3))
    cell_c.confidences = np.ones(250) * 0.92

    lifecycle = SpatialCellLifecycleManager({
        "cell_entrance": cell_a,
        "cell_lobby_failing": cell_b_failing,
        "cell_corridor": cell_c
    })

    # Initial states
    initial_ver_a = cell_a.version
    initial_ver_c = cell_c.version
    initial_val_b = lifecycle.validate_cell("cell_lobby_failing")
    assert initial_val_b["is_low_confidence"] is True

    # 2. Generate rescan task for Cell B
    generator = TargetedRescanGenerator()
    task = generator.generate_rescan_task(
        project_id=uuid.uuid4(),
        cell_id="cell_lobby_failing",
        region_bounds={"center_xyz": [6.0, 2.0, 1.2], "room_id": "Main Lobby"},
        defect_type="LOW_DENSITY",
        detailed_reason="Sparse point cloud density (40 pts)",
        current_metric_value=40.0,
        priority="HIGH"
    )

    # 3. Mobile Dispatch & Delta Guidance
    mobile = MobileRescanCoordinator()
    rx = mobile.receive_rescan_task(task)
    assert rx["status"] == "TASK_RECEIVED"

    hud = mobile.start_guided_capture(task.request_id)
    assert "screen_visual_prompt" in hud
    assert "audio_tts_utterance" in hud

    # Simulate mobile capturing localized delta frames for Cell B
    delta_pts = np.random.rand(300, 3) * 4.0 + np.array([4.0, 0.0, 0.0])
    delta_package = mobile.package_delta_upload(
        request_id=task.request_id,
        captured_frames=[{"frame_id": f"f_{i}"} for i in range(50)],
        local_imu_samples=[{"t": i * 0.01} for i in range(100)],
        point_cloud_patch=delta_pts.tolist()
    )
    assert delta_package["is_isolated_delta"] is True
    assert delta_package["target_cell_id"] == "cell_lobby_failing"

    # 4. Integrate Targeted Rescan Delta
    integrator = TargetedCellIntegrator(lifecycle)
    res = integrator.integrate_rescan_delta(
        rescan_task=task,
        delta_package=delta_package,
        new_points_world=delta_pts,
        new_colors=np.ones((len(delta_pts), 3), dtype=np.uint8) * 220,
        new_normals=np.zeros((len(delta_pts), 3)),
        new_confidences=np.ones(len(delta_pts)) * 0.94
    )

    # 5. Assertions:
    assert res["status"] == "SUCCESS"
    assert res["reconstructed_cell"] == "cell_lobby_failing"
    assert res["global_reconstruction_bypassed"] is True
    assert res["boundary_validation"]["continuous"] is True

    # Cell B version was bumped and quality improved
    updated_cell_b = lifecycle.get_cell("cell_lobby_failing")
    assert updated_cell_b.version > 1
    assert len(updated_cell_b.points_world) == 300
    assert res["post_rescan_quality"]["is_low_confidence"] is False

    # Unaffected Cells A and C were NOT modified or re-run
    assert cell_a.version == initial_ver_a
    assert cell_c.version == initial_ver_c
