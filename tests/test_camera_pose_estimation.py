"""
Unit & Integration Tests: Hierarchical Camera Pose Estimation (Stage 02)
Validates:
1. Hierarchical tracking fusion (Device VIO + Visual Tracking + Fallbacks)
2. Confidence and tracking source attribution for every pose
3. Anomaly detection: tracking loss, insufficient parallax, disconnected trajectories, high reprojection error, loop closure failure
4. Acceptance Criterion: Explicit identification of unreliable pose segments
5. Full SfMWorker lifecycle execution
"""

import os
import cv2
import json
import uuid
import pytest
import numpy as np

from core.schemas.camera_poses import (
    CameraPoses,
    TrackingSource,
    PoseAnomalyType
)
from core.tracking.tracker import VisualPoseTracker
from core.tracking.fusion import HierarchicalPoseEstimator
from workers.stages.stage02_sfm import SfMWorker
from workers.base import WorkerContext


def _create_textured_keyframe(shift_x: int = 0, shift_y: int = 0) -> np.ndarray:
    """Creates a rich textured image shifted by (shift_x, shift_y)."""
    np.random.seed(1337)
    base = np.random.randint(40, 220, (360, 480, 3), dtype=np.uint8)
    base = cv2.GaussianBlur(base, (3, 3), 0)
    cv2.circle(base, (240, 180), 40, (255, 0, 0), -1)
    cv2.rectangle(base, (100, 80), (180, 160), (0, 255, 0), -1)
    cv2.putText(base, "VASTU_SPATIAL_TWIN", (50, 300), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2)
    if shift_x != 0 or shift_y != 0:
        base = np.roll(base, shift_y, axis=0)
        base = np.roll(base, shift_x, axis=1)
    return base


def test_visual_pose_tracker_pair():
    tracker = VisualPoseTracker()
    img1 = _create_textured_keyframe(0, 0)
    img2 = _create_textured_keyframe(15, 5)

    kps1, des1 = tracker.extract_features(img1)
    kps2, des2 = tracker.extract_features(img2)

    K = np.array([
        [400.0, 0.0, 240.0],
        [0.0, 400.0, 180.0],
        [0.0, 0.0, 1.0]
    ])

    res = tracker.track_pair(kps1, des1, kps2, des2, K)
    assert res.success is True
    assert res.inliers_count >= 25
    assert res.reprojection_error_px < 2.5
    assert res.R_rel.shape == (3, 3)
    assert res.t_rel.shape == (3, 1)


def test_hierarchical_pose_fusion_with_device_vio():
    estimator = HierarchicalPoseEstimator()
    K = np.array([[400.0, 0.0, 240.0], [0.0, 400.0, 180.0], [0.0, 0.0, 1.0]])

    images = [_create_textured_keyframe(i * 12, 0) for i in range(4)]
    meta = [{"frame_index": i, "timestamp_ns": i * 100000000} for i in range(4)]

    # Provide VIO poses for all frames
    device_poses = [
        {
            "frame_index": i,
            "rotation_matrix": np.eye(3).tolist(),
            "translation_vector_m": [i * 0.20, 0.0, 0.0],
            "confidence": 0.95
        }
        for i in range(4)
    ]

    poses: CameraPoses = estimator.estimate_trajectory(
        keyframe_images=images,
        keyframe_metadata=meta,
        intrinsics_k=K,
        device_vio_poses=device_poses
    )

    assert len(poses.trajectory) == 4
    # Frame 0 is anchor; subsequent successfully fused frames should be FUSED_HYBRID
    for idx in range(1, 4):
        f = poses.trajectory[idx]
        assert f.tracking_source in (TrackingSource.FUSED_HYBRID, TrackingSource.SFM_BA)
        assert f.confidence > 0.50
        assert f.is_reliable is True
    assert poses.overall_confidence > 0.60


def test_tracking_loss_and_unreliable_segment_detection():
    """
    Simulates complete tracking failure: blank textureless image sequence with no VIO.
    Verifies that the system identifies unreliable pose segments rather than silently
    producing a complete-looking trajectory.
    """
    estimator = HierarchicalPoseEstimator()
    K = np.array([[400.0, 0.0, 240.0], [0.0, 400.0, 180.0], [0.0, 0.0, 1.0]])

    # First two frames are textured, next two are blank (tracking loss)
    img0 = _create_textured_keyframe(0, 0)
    img1 = _create_textured_keyframe(10, 0)
    img2_blank = np.zeros((360, 480, 3), dtype=np.uint8)
    img3_blank = np.zeros((360, 480, 3), dtype=np.uint8)

    images = [img0, img1, img2_blank, img3_blank]
    meta = [{"frame_index": i, "timestamp_ns": i * 100000000} for i in range(4)]

    poses: CameraPoses = estimator.estimate_trajectory(
        keyframe_images=images,
        keyframe_metadata=meta,
        intrinsics_k=K,
        device_vio_poses=None  # No VIO available!
    )

    assert len(poses.trajectory) == 4

    # Frame 2 & 3 must detect TRACKING_LOSS and be marked unreliable
    f2 = poses.trajectory[2]
    assert f2.is_reliable is False
    assert PoseAnomalyType.TRACKING_LOSS.value in f2.anomaly_flags
    assert f2.tracking_source == TrackingSource.ESTIMATED_INTERPOLATION
    assert f2.confidence < 0.20

    # System MUST explicitly identify unreliable pose segments
    assert len(poses.unreliable_segments) > 0
    segment = poses.unreliable_segments[0]
    assert segment.anomaly_type == PoseAnomalyType.TRACKING_LOSS
    assert "Degraded tracking" in segment.reason


def test_loop_closure_failure_detection():
    """
    Simulates a loop trajectory returning to origin, but with synthetic drift > 0.5m.
    Verifies detection of LOOP_CLOSURE_MISMATCH.
    """
    estimator = HierarchicalPoseEstimator(loop_closure_threshold_m=0.30)
    K = np.array([[400.0, 0.0, 240.0], [0.0, 400.0, 180.0], [0.0, 0.0, 1.0]])

    # 6 frames: 0..4 moving, frame 5 returns to same image as frame 0!
    images = [
        _create_textured_keyframe(0, 0),
        _create_textured_keyframe(15, 0),
        _create_textured_keyframe(30, 0),
        _create_textured_keyframe(45, 0),
        _create_textured_keyframe(60, 0),
        _create_textured_keyframe(0, 0)  # Identical to frame 0 -> visual match!
    ]
    meta = [{"frame_index": i, "timestamp_ns": i * 100000000} for i in range(6)]

    # Because frames were stepped forward by 15px each, frame 5 visual matches frame 0,
    # but accumulated odometry position is > 0.5m away from origin (0, 0, 0)!
    poses: CameraPoses = estimator.estimate_trajectory(
        keyframe_images=images,
        keyframe_metadata=meta,
        intrinsics_k=K,
        device_vio_poses=None
    )

    assert poses.loop_closure_detected is True
    assert poses.loop_closure_residual_m is not None
    assert poses.loop_closure_residual_m > 0.30

    # Last frame should have LOOP_CLOSURE_MISMATCH flag
    last_frame = poses.trajectory[-1]
    assert PoseAnomalyType.LOOP_CLOSURE_MISMATCH.value in last_frame.anomaly_flags
    assert last_frame.is_reliable is False


def test_sfm_worker_lifecycle(tmp_path):
    # Setup keyframes directory with synthetic frames
    keyframes_dir = tmp_path / "01_keyframes"
    os.makedirs(keyframes_dir, exist_ok=True)

    metadata = []
    for i in range(3):
        img_file = f"frame_{i:05d}.jpg"
        img_path = keyframes_dir / img_file
        cv2.imwrite(str(img_path), _create_textured_keyframe(i * 12, 0))
        metadata.append({
            "frame_index": i,
            "timestamp_ns": i * 100000000,
            "is_keyframe": True,
            "file_path": str(img_path)
        })

    with open(keyframes_dir / "frame_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)

    ctx = WorkerContext(
        job_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        work_dir=str(tmp_path),
        params={}
    )

    worker = SfMWorker()
    result = worker.execute(ctx)

    assert result.status.value == "SUCCESS"
    assert "camera_poses" in result.artifacts
    poses_path = result.artifacts["camera_poses"]
    assert os.path.exists(poses_path)

    with open(poses_path, "r") as f:
        saved_poses = json.load(f)

    assert "trajectory" in saved_poses
    assert "intrinsics" in saved_poses
    assert "overall_confidence" in saved_poses
    assert len(saved_poses["trajectory"]) == 3
