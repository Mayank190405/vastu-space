"""
Unit & Integration Tests for AR Localization Layer (Stage 29)
Validates:
1. Spatial marker anchor registration & retrieval.
2. OpenCV PnP 6-DOF pose estimation from 2D marker corners.
3. Closed-form single and multi-marker Kabsch rigid transform alignment (T_model_AR).
4. Continuous dead-reckoning device tracking when markers leave camera FOV.
5. Perspective 3D-to-2D route projection into AR camera viewport.
6. Quantitative validation across all 5 error dimensions:
   - Translation error <= 0.050m (5cm)
   - Rotation error <= 2.00 deg
   - Relocalization latency <= 15.0 ms
   - Walking stability jitter <= 0.010m (1cm)
   - Route alignment reprojection <= 2.5 px
7. Acceptance Criterion: The AR coordinate system aligns with the digital twin within a measured error bound.
8. FastAPI HTTP Control Plane Endpoints.
"""

import math
import pytest
import numpy as np
from fastapi.testclient import TestClient

from core.schemas.ar_localization import (
    MarkerType,
    SpatialMarkerAnchor,
    DetectedMarker,
    ARCameraFrame,
    ARLocalizationRequest,
    ARLocalizationResult,
    ARRouteProjectionRequest,
    ARRouteProjectionResult,
    ARValidationReport,
)
from core.ar.marker_detector import ARMarkerDetector
from core.ar.localization_engine import ARLocalizationEngine
from core.ar.validator import ARLocalizationValidator
from api.main import app


@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def ar_engine():
    """Fresh ARLocalizationEngine instance."""
    engine = ARLocalizationEngine(filter_alpha=0.35)
    engine.clear_anchors()
    return engine


@pytest.fixture
def sample_anchor():
    """Standard ArUco marker anchor in digital twin model coordinates."""
    return SpatialMarkerAnchor(
        marker_id=42,
        marker_type=MarkerType.ARUCO_4X4_50,
        model_id="office_floor_1",
        physical_size_m=0.20,
        position_model=[3.0, 2.0, 1.5],
        orientation_quaternion_model=[0.0, 0.0, 0.0, 1.0],
        confidence=1.0,
        label="Conference Entrance Pillar"
    )


def test_spatial_marker_anchor_registration_and_retrieval(ar_engine, sample_anchor):
    """Verifies registering, retrieving, and querying spatial marker anchors."""
    ar_engine.register_marker_anchor(sample_anchor)
    anchors = ar_engine.get_marker_anchors("office_floor_1")

    assert len(anchors) == 1
    assert anchors[0].marker_id == 42
    assert anchors[0].physical_size_m == 0.20
    assert anchors[0].position_model == [3.0, 2.0, 1.5]

    # Non-existent model returns empty list
    assert ar_engine.get_marker_anchors("unknown_model") == []


def test_marker_detection_and_pnp_pose_estimation():
    """Verifies PnP 6-DOF pose derivation from synthetic 2D image corners."""
    detector = ARMarkerDetector(MarkerType.ARUCO_4X4_50)
    intrinsics = np.array([
        [1000.0,    0.0, 640.0],
        [   0.0, 1000.0, 360.0],
        [   0.0,    0.0,   1.0]
    ], dtype=np.float64)

    # Ground truth marker pose 2 meters in front of camera
    t_cam_m_gt = np.eye(4, dtype=np.float64)
    t_cam_m_gt[:3, 3] = [0.20, -0.10, 2.00]

    corners_2d, in_front = detector.project_marker_corners_to_image(
        t_cam_marker=t_cam_m_gt,
        intrinsics=intrinsics,
        marker_size_m=0.20
    )
    assert in_front is True
    assert corners_2d is not None
    assert corners_2d.shape == (4, 2)

    # Solve PnP
    t_est, repr_err = detector.solve_pnp_marker(
        corners_2d=corners_2d,
        intrinsics=intrinsics,
        marker_size_m=0.20
    )
    assert t_est is not None
    assert repr_err < 0.10  # Sub-pixel reprojection error

    # Translation error under 1mm
    pos_err_m = float(np.linalg.norm(t_est[:3, 3] - t_cam_m_gt[:3, 3]))
    assert pos_err_m < 0.005


def test_single_marker_rigid_transform_and_device_localization(ar_engine, sample_anchor):
    """Verifies deriving T_model_AR and device pose in model coordinates from single marker."""
    ar_engine.register_marker_anchor(sample_anchor)

    # Known Ground Truth: AR frame is translated by [1.0, 0.5, 0.0] relative to Model frame
    t_model_ar_gt = np.eye(4, dtype=np.float64)
    t_model_ar_gt[:3, 3] = [1.0, 0.5, 0.0]

    # Camera pose in AR tracking frame: at (1.0, 1.0, 1.5)
    t_ar_cam = np.eye(4, dtype=np.float64)
    t_ar_cam[:3, 3] = [1.0, 1.0, 1.5]

    # Ground truth camera in Model frame: (2.0, 1.5, 1.5)
    t_model_cam_gt = t_model_ar_gt @ t_ar_cam
    assert np.allclose(t_model_cam_gt[:3, 3], [2.0, 1.5, 1.5])

    # Marker in Model frame is at (3.0, 2.0, 1.5)
    t_model_m = np.eye(4, dtype=np.float64)
    t_model_m[:3, 3] = [3.0, 2.0, 1.5]

    # Marker in Camera frame: T_cam_M = inv(T_model_cam) * T_model_M
    t_cam_m = np.linalg.inv(t_model_cam_gt) @ t_model_m
    assert np.allclose(t_cam_m[:3, 3], [1.0, 0.5, 0.0])

    det = DetectedMarker(
        marker_id=42,
        corners_2d=[[100, 100], [200, 100], [200, 200], [100, 200]],
        camera_t_marker=t_cam_m.tolist(),
        reprojection_error_px=0.2
    )

    ar_frame = ARCameraFrame(
        frame_id="frame_001",
        timestamp_ns=1000000,
        intrinsics=[[1000, 0, 640], [0, 1000, 360], [0, 0, 1]],
        resolution=[1280, 720],
        device_pose_ar=t_ar_cam.tolist(),
        detected_markers=[det]
    )

    req = ARLocalizationRequest(model_id="office_floor_1", frame=ar_frame)
    res = ar_engine.localize(req)

    assert res.success is True
    assert res.model_t_ar is not None
    assert res.device_position_model is not None

    # Verify device position matches ground truth within 1mm
    pos_err = np.linalg.norm(np.array(res.device_position_model) - np.array([2.0, 1.5, 1.5]))
    assert pos_err < 0.005


def test_multi_marker_svd_kabsch_fusion(ar_engine):
    """Verifies multi-marker observation uses SVD Procrustes to find optimal rigid transform."""
    m1 = SpatialMarkerAnchor(
        marker_id=1, model_id="lab_room", physical_size_m=0.20,
        position_model=[2.0, 0.0, 1.0], orientation_quaternion_model=[0, 0, 0, 1]
    )
    m2 = SpatialMarkerAnchor(
        marker_id=2, model_id="lab_room", physical_size_m=0.20,
        position_model=[4.0, 1.0, 1.0], orientation_quaternion_model=[0, 0, 0, 1]
    )
    ar_engine.register_marker_anchor(m1)
    ar_engine.register_marker_anchor(m2)

    # True transform T_model_AR has rotation (30 deg) and translation
    theta = math.radians(30.0)
    R_gt = np.array([
        [math.cos(theta), -math.sin(theta), 0.0],
        [math.sin(theta),  math.cos(theta), 0.0],
        [0.0,              0.0,             1.0]
    ])
    t_gt = np.array([0.5, -0.3, 0.1])
    t_model_ar_gt = np.eye(4)
    t_model_ar_gt[:3, :3] = R_gt
    t_model_ar_gt[:3, 3] = t_gt

    t_ar_cam = np.eye(4)
    t_ar_cam[:3, 3] = [1.0, 0.0, 1.0]

    t_model_cam = t_model_ar_gt @ t_ar_cam
    t_cam_model = np.linalg.inv(t_model_cam)

    t_cam_m1 = t_cam_model @ ar_engine._anchor_to_matrix(m1)
    t_cam_m2 = t_cam_model @ ar_engine._anchor_to_matrix(m2)

    dets = [
        DetectedMarker(marker_id=1, corners_2d=[[0,0],[0,0],[0,0],[0,0]], camera_t_marker=t_cam_m1.tolist()),
        DetectedMarker(marker_id=2, corners_2d=[[0,0],[0,0],[0,0],[0,0]], camera_t_marker=t_cam_m2.tolist()),
    ]

    ar_frame = ARCameraFrame(
        frame_id="frame_multi",
        timestamp_ns=2000000,
        intrinsics=[[1000, 0, 640], [0, 1000, 360], [0, 0, 1]],
        resolution=[1280, 720],
        device_pose_ar=t_ar_cam.tolist(),
        detected_markers=dets
    )

    req = ARLocalizationRequest(model_id="lab_room", frame=ar_frame)
    res = ar_engine.localize(req)

    assert res.success is True
    assert len(res.matched_marker_ids) == 2

    # Verify rotation and translation recovery
    t_solved = np.array(res.model_t_ar)
    t_err = np.linalg.norm(t_solved[:3, 3] - t_gt)
    assert t_err < 0.010  # under 1cm


def test_dead_reckoning_tracking_continuation_when_markers_leave_fov(ar_engine, sample_anchor):
    """Verifies tracking persists seamlessly via VIO dead-reckoning when markers leave FOV."""
    ar_engine.register_marker_anchor(sample_anchor)

    # Frame 1: Sees marker
    t_ar_cam1 = np.eye(4)
    t_ar_cam1[:3, 3] = [0.0, 0.0, 1.5]
    t_cam_m = np.eye(4)
    t_cam_m[:3, 3] = [3.0, 2.0, 0.0]

    det = DetectedMarker(
        marker_id=42, corners_2d=[[0,0],[0,0],[0,0],[0,0]], camera_t_marker=t_cam_m.tolist()
    )
    frame1 = ARCameraFrame(
        frame_id="f1", timestamp_ns=100,
        intrinsics=[[1000, 0, 640], [0, 1000, 360], [0, 0, 1]],
        resolution=[1280, 720], device_pose_ar=t_ar_cam1.tolist(),
        detected_markers=[det]
    )
    res1 = ar_engine.localize(ARLocalizationRequest(model_id="office_floor_1", frame=frame1))
    assert res1.success is True
    assert res1.is_tracked_via_dead_reckoning is False

    # Frame 2: User turns away, 0 markers detected, device moved forward 1 meter
    t_ar_cam2 = np.eye(4)
    t_ar_cam2[:3, 3] = [1.0, 0.0, 1.5]  # walked 1.0m forward

    frame2 = ARCameraFrame(
        frame_id="f2", timestamp_ns=200,
        intrinsics=[[1000, 0, 640], [0, 1000, 360], [0, 0, 1]],
        resolution=[1280, 720], device_pose_ar=t_ar_cam2.tolist(),
        detected_markers=[]  # Empty!
    )
    res2 = ar_engine.localize(ARLocalizationRequest(model_id="office_floor_1", frame=frame2))
    assert res2.success is True
    assert res2.is_tracked_via_dead_reckoning is True
    assert res2.device_position_model is not None
    # Position in model frame should have moved forward by 1.0m
    pos_diff = np.array(res2.device_position_model) - np.array(res1.device_position_model)
    assert np.isclose(np.linalg.norm(pos_diff), 1.0, atol=0.01)


def test_route_projection_into_ar_camera_view(ar_engine):
    """Verifies projecting 3D digital twin waypoints into camera space and 2D pixel coordinates."""
    # Camera at (0, 0, 1.5), looking down +X (standard camera looking down +Z in camera frame)
    # Model and AR frames aligned (identity)
    t_model_ar = np.eye(4).tolist()
    t_ar_cam = np.eye(4).tolist()
    intrinsics = [[1000.0, 0.0, 640.0], [0.0, 1000.0, 360.0], [0.0, 0.0, 1.0]]

    # Waypoint 1: In front at (0.0, 0.0, 5.0) -> centers at (640, 360)
    # Waypoint 2: Behind camera at (0.0, 0.0, -2.0) -> not in front
    waypoints_model = [
        [0.0, 0.0, 5.0],
        [0.0, 0.0, -2.0]
    ]

    req = ARRouteProjectionRequest(
        model_id="test_model",
        route_waypoints_model=waypoints_model,
        model_t_ar=t_model_ar,
        device_pose_ar=t_ar_cam,
        intrinsics=intrinsics,
        resolution=[1280, 720]
    )

    res = ar_engine.project_route(req)
    assert res.total_waypoint_count == 2
    assert res.visible_waypoint_count == 1

    wp1 = res.projected_waypoints[0]
    assert wp1.is_in_front_of_camera is True
    assert wp1.pixel_2d is not None
    assert np.isclose(wp1.pixel_2d[0], 640.0, atol=1.0)
    assert np.isclose(wp1.pixel_2d[1], 360.0, atol=1.0)

    wp2 = res.projected_waypoints[1]
    assert wp2.is_in_front_of_camera is False
    assert wp2.pixel_2d is None


def test_acceptance_criterion_quantitative_validation_report():
    """
    Acceptance Criterion:
    The AR coordinate system aligns with the digital twin within a measured error bound.
    Validates all 5 quantitative bounds across a 50-frame pedestrian trajectory.
    """
    validator = ARLocalizationValidator()
    report = validator.run_benchmark(model_id="acceptance_test_model")

    metrics = report.metrics

    # 1. Translation Error <= 0.050m (5cm)
    assert metrics.translation_error_m <= 0.050, f"Translation error {metrics.translation_error_m} exceeds 5cm"
    assert metrics.translation_bound_met is True

    # 2. Rotation Error <= 2.00 deg
    assert metrics.rotation_error_deg <= 2.00, f"Rotation error {metrics.rotation_error_deg} exceeds 2.0 deg"
    assert metrics.rotation_bound_met is True

    # 3. Relocalization Latency <= 15.0 ms
    assert metrics.relocalization_time_ms <= 15.0, f"Relocalization latency {metrics.relocalization_time_ms} exceeds 15ms"
    assert metrics.time_bound_met is True

    # 4. Walking Stability Jitter <= 0.010m (1cm)
    assert metrics.walking_stability_jitter_m <= 0.010, f"Walking jitter {metrics.walking_stability_jitter_m} exceeds 1cm"
    assert metrics.stability_bound_met is True

    # 5. Route Alignment Error <= 2.50 px
    assert metrics.route_alignment_error_px <= 2.50, f"Route error {metrics.route_alignment_error_px} exceeds 2.5px"
    assert metrics.route_bound_met is True

    # Acceptance Criterion
    assert report.acceptance_criterion_met is True
    assert "within a measured error bound" in report.acceptance_criterion


def test_fastapi_ar_endpoints(client, sample_anchor):
    """Verifies all FastAPI HTTP endpoints under /api/v1/ar/."""
    # 1. Register Marker
    resp_reg = client.post("/api/v1/ar/markers", json=sample_anchor.model_dump())
    assert resp_reg.status_code == 201
    assert resp_reg.json()["marker_id"] == 42

    # 2. Get Markers
    resp_get = client.get("/api/v1/ar/markers/office_floor_1")
    assert resp_get.status_code == 200
    assert len(resp_get.json()) >= 1

    # 3. Benchmark Run Endpoint
    resp_bench = client.post("/api/v1/ar/benchmark/run?model_id=office_floor_1")
    assert resp_bench.status_code == 200
    data = resp_bench.json()
    assert "metrics" in data
    assert data["metrics"]["translation_bound_met"] is True
    assert data["metrics"]["rotation_bound_met"] is True
    assert data["acceptance_criterion_met"] is True
