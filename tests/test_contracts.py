"""
VĀSTU Automated Contract Verification Tests
Validates all 13 canonical system contracts against strict Pydantic schemas.
"""

import uuid
import pytest
from pydantic import ValidationError
from core.schemas import (
    CaptureManifest,
    DeviceInfo,
    CameraCalibration,
    CaptureFiles,
    FrameMetadata,
    IMUSample,
    Vector3D,
    CameraPoses,
    CameraTrajectoryFrame,
    ReconstructionArtifact,
    ArtifactStats,
    SpatialCell,
    CellCoordinates,
    CellBounds,
    StructuralPlane,
    PlaneEquation,
    SemanticObject,
    OrientedBoundingBox,
    PointOfInterest,
    POICoordinates,
    NavigationGraph,
    NavigationNode,
    NavigationEdge,
    QualityReport,
    QualityScores,
    RescanRequest,
    RescanBoundingBox,
    OperatorGuidance,
    ModelVersion,
    ModelArtifactKeys,
)

def test_contract_1_capture_manifest_valid():
    manifest = CaptureManifest(
        capture_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        device_info=DeviceInfo(
            manufacturer="Apple",
            model="iPhone 15 Pro",
            os_name="iOS",
            os_version="17.4",
            app_version="1.0.0"
        ),
        camera_calibration=CameraCalibration(
            fx=1420.5,
            fy=1420.5,
            cx=960.0,
            cy=540.0,
            image_width=1920,
            image_height=1080
        ),
        files=CaptureFiles(
            video={
                "filename": "scan.mov",
                "size_bytes": 10485760,
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "duration_sec": 10.0,
                "frame_count": 600,
                "fps": 60.0,
                "codec": "hevc"
            },
            imu={
                "filename": "imu.csv",
                "size_bytes": 51200,
                "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "sample_count": 1000,
                "sampling_rate_hz": 100.0
            }
        ),
        metrics={"dropped_frames": 0, "imu_packet_drops": 0, "average_lux": 150.0},
        created_at="2026-09-06T15:00:00Z"
    )
    assert manifest.manifest_version == "1.0.0"

def test_contract_1_capture_manifest_invalid_duration():
    with pytest.raises(ValidationError):
        CaptureManifest(
            capture_id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            device_info=DeviceInfo(
                manufacturer="Apple", model="iPhone", os_name="iOS", os_version="17", app_version="1"
            ),
            camera_calibration=CameraCalibration(
                fx=1000, fy=1000, cx=500, cy=500, image_width=1000, image_height=1000
            ),
            files=CaptureFiles(
                video={
                    "filename": "s.mov", "size_bytes": 1024, "sha256": "abc", "duration_sec": 1.0, "frame_count": 10, "fps": 30.0
                },
                imu={"filename": "i.csv", "size_bytes": 10, "sha256": "abc", "sample_count": 10, "sampling_rate_hz": 10.0}
            ),
            metrics={"dropped_frames": 0, "imu_packet_drops": 0, "average_lux": 100.0},
            created_at="2026-09-06T15:00:00Z"
        )

def test_contract_2_frame_metadata():
    fm = FrameMetadata(
        frame_index=0,
        timestamp_ns=1000000,
        exposure_time_sec=0.016,
        iso=100,
        focal_length_px=1400.0,
        laplacian_blur_score=150.0,
        is_keyframe=True
    )
    assert fm.is_blurry is False

def test_contract_3_imu_samples():
    imu = IMUSample(
        timestamp_ns=1000000,
        accel_m_s2=Vector3D(x=0.0, y=9.81, z=0.0),
        gyro_rad_s=Vector3D(x=0.0, y=0.0, z=0.0)
    )
    assert imu.accel_m_s2.y == 9.81

def test_contract_4_camera_poses():
    poses = CameraPoses(
        camera_model="PINHOLE",
        intrinsics=[1400.0, 1400.0, 960.0, 540.0],
        trajectory=[
            CameraTrajectoryFrame(
                frame_index=0,
                timestamp_ns=1000,
                rotation_matrix=[[1,0,0],[0,1,0],[0,0,1]],
                translation_vector_m=[0,0,0],
                quaternion_xyzw=[0,0,0,1],
                camera_center_m=[0,0,0],
                reprojection_error_px=0.5,
                inlier_points_count=500
            )
        ]
    )
    assert len(poses.trajectory) == 1

def test_contract_5_reconstruction_artifact():
    art = ReconstructionArtifact(
        artifact_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        model_format="GLB",
        lod_level="LOD0",
        s3_bucket="vastu-artifacts",
        s3_key="models/model.glb",
        file_size_bytes=1024000,
        sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        stats=ArtifactStats(
            vertex_count=50000,
            triangle_count=100000,
            bounding_box_min=[-5,-5,-5],
            bounding_box_max=[5,5,5]
        ),
        created_at="2026-09-06T15:00:00Z"
    )
    assert art.stats.triangle_count == 100000

def test_contract_6_spatial_cell():
    cell = SpatialCell(
        cell_id="cell_001_002_003",
        model_id=uuid.uuid4(),
        coordinates=CellCoordinates(cx=1, cy=2, cz=3),
        cell_size_m=1.0,
        bounds=CellBounds(min_xyz=[1,2,3], max_xyz=[2,3,4], center_xyz=[1.5,2.5,3.5]),
        quality_score=0.92
    )
    assert cell.is_low_confidence is False

def test_contract_7_structural_geometry():
    plane = StructuralPlane(
        structure_id="wall_01",
        plane_type="WALL",
        plane_equation=PlaneEquation(a=1, b=0, c=0, d=-2),
        normal_vector=[1, 0, 0],
        inlier_points_count=5000,
        surface_area_m2=12.5
    )
    assert plane.plane_type == "WALL"

def test_contract_8_semantic_object():
    obj = SemanticObject(
        object_id="extinguisher_01",
        class_name="fire_extinguisher",
        confidence=0.95,
        oriented_bounding_box=OrientedBoundingBox(
            center=[1, 1, 1],
            extent_dx_dy_dz=[0.2, 0.6, 0.2],
            rotation_quaternion=[0, 0, 0, 1]
        )
    )
    assert obj.confidence == 0.95

def test_contract_9_poi():
    poi = PointOfInterest(
        project_id=uuid.uuid4(),
        title="Fire Alarm",
        coordinates_m=POICoordinates(x=1.2, y=1.5, z=-0.5)
    )
    assert poi.title == "Fire Alarm"

def test_contract_10_navigation_graph():
    graph = NavigationGraph(
        project_id=uuid.uuid4(),
        nodes=[NavigationNode(id="n1", position=[0, 0, 0])],
        edges=[NavigationEdge(id="e1", from_node="n1", to_node="n1", distance_meters=1.0)]
    )
    assert len(graph.nodes) == 1

def test_contract_11_quality_report():
    qr = QualityReport(
        job_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        verdict="PASS",
        scores=QualityScores(
            overall=0.9,
            geometry_watertightness=0.9,
            tracking_vio_drift=0.9,
            spatial_coverage=0.9,
            texture_sharpness=0.9,
            semantic_consistency=0.9,
            cell_continuity=0.9,
            navigation_connectivity=1.0
        )
    )
    assert qr.verdict == "PASS"

def test_contract_12_rescan_request():
    rr = RescanRequest(
        request_id="rescan_123",
        project_id=uuid.uuid4(),
        target_cells=["cell_1"],
        reason="Holes detected",
        target_bounding_box=RescanBoundingBox(min_xyz=[0,0,0], max_xyz=[1,1,1], center_xyz=[0.5,0.5,0.5]),
        operator_guidance=OperatorGuidance(audio_tts_prompt="Rescan corner"),
        created_at="2026-09-06T15:00:00Z"
    )
    assert rr.status == "PENDING"

def test_contract_13_model_version():
    mv = ModelVersion(
        model_version_id="v1.0.0",
        project_id=uuid.uuid4(),
        semver="1.0.0",
        change_type="INITIAL_RECONSTRUCTION",
        summary_of_changes="Initial twin release",
        artifacts=ModelArtifactKeys(lod0_glb_s3_key="models/lod0.glb"),
        created_at="2026-09-06T15:00:00Z"
    )
    assert mv.semver == "1.0.0"
