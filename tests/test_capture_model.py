import os
import tempfile
import json
import uuid
import pytest
import numpy as np

from core.domain.enums import (
    CoordinateSystem,
    ScaleSource,
    CaptureUploadStatus,
    CameraDistortionModel,
    CalibrationType,
)
from core.schemas.capture_manifest import (
    CaptureManifest,
    DeviceInfo,
    CameraCalibration,
    CalibrationMetadata,
    VideoFileMeta,
    IMUFileMeta,
    FrameTimingRecord,
    FrameTimestampsMeta,
    CaptureFiles,
    CoordinateSystemMeta,
    ScaleInformation,
    CaptureQualityMetrics,
    CoverageInformation,
)
from storage.naming import CaptureArtifactNaming
from core.validation.capture_validator import CaptureValidator
from core.packaging.capture_package import CapturePackage


def _create_mock_video_file(path: str, size: int = 20480) -> str:
    # Write a valid ISO Base Media header (e.g. '....ftypmp42....')
    header = b"\x00\x00\x00\x20ftypmp42\x00\x00\x00\x00isommp42"
    padding = b"\x00" * (size - len(header))
    with open(path, "wb") as f:
        f.write(header + padding)
    return path


def _create_mock_imu_file(path: str, size: int = 1024) -> str:
    content = "timestamp_ns,acc_x,acc_y,acc_z,gyr_x,gyr_y,gyr_z\n"
    content += "1000000000,0.0,9.81,0.0,0.0,0.0,0.0\n"
    content += "2000000000,0.0,9.81,0.0,0.0,0.0,0.0\n"
    content = content.ljust(size, " ")
    with open(path, "w") as f:
        f.write(content)
    return path


def _build_valid_manifest(
    temp_dir: str,
    vid_sha: str,
    imu_sha: str,
    vid_size: int = 20480,
    imu_size: int = 1024
) -> CaptureManifest:
    proj_id = uuid.uuid4()
    cap_id = uuid.uuid4()

    # Generate 60 frames (2 seconds at 30 fps)
    timing_records = []
    for i in range(60):
        t_sec = i * (1.0 / 30.0)
        timing_records.append(
            FrameTimingRecord(
                frame_index=i,
                relative_timestamp_sec=t_sec,
                monotonic_timestamp_ns=1_000_000_000 + int(t_sec * 1e9),
                pts_timestamp_ns=int(t_sec * 1e9),
                exposure_time_sec=0.016,
                iso_gain=100.0
            )
        )

    return CaptureManifest(
        manifest_version="2.0.0",
        capture_id=cap_id,
        project_id=proj_id,
        device_info=DeviceInfo(
            manufacturer="Apple",
            model="iPhone 15 Pro",
            os_name="iOS",
            os_version="17.5",
            app_version="2.0.0",
            thermal_state="nominal",
            hardware_id="A2849"
        ),
        camera_calibration=CameraCalibration(
            fx=1450.0,
            fy=1450.0,
            cx=960.0,
            cy=540.0,
            image_width=1920,
            image_height=1080,
            sensor_width_mm=6.4,
            sensor_height_mm=4.8,
            pixel_pitch_um=3.33,
            rolling_shutter_readout_sec=0.015,
            distortion_model=CameraDistortionModel.RADTAN,
            distortion_coefficients=[0.01, -0.005, 0.0, 0.0]
        ),
        calibration=CalibrationMetadata(
            calibration_type=CalibrationType.FACTORY,
            calibrated_at="2026-09-01T00:00:00Z",
            confidence_score=0.98,
            reprojection_error_px=0.45
        ),
        files=CaptureFiles(
            video=VideoFileMeta(
                filename="raw_video.mov",
                size_bytes=vid_size,
                sha256=vid_sha,
                duration_sec=2.0,
                frame_count=60,
                fps=30.0,
                codec="h264",
                bitrate_kbps=15000,
                color_space="BT.709",
                is_hdr=False
            ),
            imu=IMUFileMeta(
                filename="imu_samples.csv",
                size_bytes=imu_size,
                sha256=imu_sha,
                sample_count=200,
                sampling_rate_hz=100.0,
                start_timestamp_ns=900_000_000, # Starts before first frame
                end_timestamp_ns=3_100_000_000   # Ends after last frame
            ),
            timestamps=FrameTimestampsMeta(
                filename="frame_timestamps.json",
                sample_count=len(timing_records),
                records=timing_records
            )
        ),
        coordinate_system=CoordinateSystemMeta(
            convention=CoordinateSystem.OPENCV_RDF,
            gravity_aligned=True,
            gravity_vector=[0.0, 9.81, 0.0]
        ),
        scale_info=ScaleInformation(
            scale_factor=1.0,
            scale_source=ScaleSource.LIDAR_SPARSE,
            scale_uncertainty=0.01
        ),
        sop_version="vastu_sop_v2.0_indoor_continuous",
        metrics=CaptureQualityMetrics(
            dropped_frames=0,
            imu_packet_drops=0,
            average_lux=180.0,
            motion_blur_score=0.02,
            operator_speed_mps=0.5
        ),
        coverage=CoverageInformation(
            estimated_area_m2=40.0,
            estimated_path_length_m=12.0,
            keyframe_count=30,
            loop_closure_detected=True
        ),
        upload_status=CaptureUploadStatus.UPLOADED,
        created_at="2026-09-06T12:00:00Z"
    )


def test_deterministic_naming():
    proj_id = uuid.uuid4()
    cap_id = uuid.uuid4()

    prefix = CaptureArtifactNaming.get_capture_prefix(proj_id, cap_id)
    assert prefix == f"captures/{proj_id}/{cap_id}"

    manifest_key = CaptureArtifactNaming.get_manifest_key(proj_id, cap_id)
    assert manifest_key == f"captures/{proj_id}/{cap_id}/manifest.json"

    video_key = CaptureArtifactNaming.get_video_key(proj_id, cap_id, "mp4")
    assert video_key == f"captures/{proj_id}/{cap_id}/raw_video.mp4"

    imu_key = CaptureArtifactNaming.get_imu_key(proj_id, cap_id, "parquet")
    assert imu_key == f"captures/{proj_id}/{cap_id}/imu_samples.parquet"

    parsed = CaptureArtifactNaming.parse_storage_key(manifest_key)
    assert parsed["project_id"] == str(proj_id)
    assert parsed["capture_id"] == str(cap_id)
    assert parsed["filename"] == "manifest.json"


def test_validation_valid_manifest_and_files():
    with tempfile.TemporaryDirectory() as temp_dir:
        vid_path = os.path.join(temp_dir, "raw_video.mov")
        _create_mock_video_file(vid_path, size=20480)
        vid_sha = CaptureValidator.compute_sha256(vid_path)

        imu_path = os.path.join(temp_dir, "imu_samples.csv")
        _create_mock_imu_file(imu_path, size=1024)
        imu_sha = CaptureValidator.compute_sha256(imu_path)

        manifest = _build_valid_manifest(temp_dir, vid_sha, imu_sha)

        report = CaptureValidator.validate(manifest, base_dir_or_adapter=temp_dir)
        assert report.is_valid is True
        assert len(report.errors) == 0
        assert "video_container_header_valid" in report.checks_passed
        assert "video_checksum_verified" in report.checks_passed
        assert "imu_video_temporal_coverage_complete" in report.checks_passed


def test_validation_missing_files():
    with tempfile.TemporaryDirectory() as temp_dir:
        manifest = _build_valid_manifest(temp_dir, "0" * 64, "0" * 64)
        # Directory is empty (no files)
        report = CaptureValidator.validate(manifest, base_dir_or_adapter=temp_dir)
        assert report.is_valid is False
        assert any("Missing file: declared video file" in e for e in report.errors)


def test_validation_corrupted_media_and_checksums():
    with tempfile.TemporaryDirectory() as temp_dir:
        vid_path = os.path.join(temp_dir, "raw_video.mov")
        # Write corrupted header (e.g. random text, not ISO box)
        with open(vid_path, "wb") as f:
            f.write(b"CORRUPTED_NOT_A_VIDEO_HEADER_1234567890".ljust(20480, b"\x00"))

        imu_path = os.path.join(temp_dir, "imu_samples.csv")
        _create_mock_imu_file(imu_path, size=1024)
        imu_sha = CaptureValidator.compute_sha256(imu_path)

        # Declare a fake SHA-256 for video
        manifest = _build_valid_manifest(temp_dir, "f" * 64, imu_sha)

        report = CaptureValidator.validate(manifest, base_dir_or_adapter=temp_dir)
        assert report.is_valid is False
        assert any("lacks a valid ISO Base Media" in e for e in report.errors)
        assert any("video SHA-256 mismatch" in e for e in report.errors)


def test_validation_incomplete_upload():
    with tempfile.TemporaryDirectory() as temp_dir:
        vid_path = os.path.join(temp_dir, "raw_video.mov")
        _create_mock_video_file(vid_path, size=15000) # Declared is 20480
        vid_sha = CaptureValidator.compute_sha256(vid_path)

        imu_path = os.path.join(temp_dir, "imu_samples.csv")
        _create_mock_imu_file(imu_path, size=1024)
        imu_sha = CaptureValidator.compute_sha256(imu_path)

        manifest = _build_valid_manifest(temp_dir, vid_sha, imu_sha, vid_size=20480)

        report = CaptureValidator.validate(manifest, base_dir_or_adapter=temp_dir)
        assert report.is_valid is False
        assert any("Incomplete upload" in e for e in report.errors)


def test_validation_timestamp_inconsistencies_and_duplicates():
    with tempfile.TemporaryDirectory() as temp_dir:
        vid_path = os.path.join(temp_dir, "raw_video.mov")
        _create_mock_video_file(vid_path, size=20480)
        vid_sha = CaptureValidator.compute_sha256(vid_path)

        imu_path = os.path.join(temp_dir, "imu_samples.csv")
        _create_mock_imu_file(imu_path, size=1024)
        imu_sha = CaptureValidator.compute_sha256(imu_path)

        manifest = _build_valid_manifest(temp_dir, vid_sha, imu_sha)

        # Introduce non-monotonic timestamp and duplicate frame
        manifest.files.timestamps.records[5].relative_timestamp_sec = 0.05
        manifest.files.timestamps.records[6].relative_timestamp_sec = 0.05 # Duplicate zero-delta

        report = CaptureValidator.validate(manifest, base_dir_or_adapter=temp_dir)
        assert report.is_valid is False
        assert any("not strictly monotonically increasing" in e for e in report.errors)
        assert any("Duplicate frames detected" in e for e in report.errors)


def test_validation_invalid_metadata():
    with tempfile.TemporaryDirectory() as temp_dir:
        vid_path = os.path.join(temp_dir, "raw_video.mov")
        _create_mock_video_file(vid_path, size=20480)
        vid_sha = CaptureValidator.compute_sha256(vid_path)

        imu_path = os.path.join(temp_dir, "imu_samples.csv")
        _create_mock_imu_file(imu_path, size=1024)
        imu_sha = CaptureValidator.compute_sha256(imu_path)

        manifest = _build_valid_manifest(temp_dir, vid_sha, imu_sha)
        manifest.upload_status = CaptureUploadStatus.PENDING # Incomplete upload status

        report = CaptureValidator.validate(manifest, base_dir_or_adapter=temp_dir)
        assert report.is_valid is False
        assert any("manifest upload_status is 'PENDING'" in e for e in report.errors)


def test_self_contained_capture_reproducibility():
    """
    Verifies acceptance criterion:
    A capture can be exported, unpacked, and reproduced from its manifest
    without relying on undocumented external database state.
    """
    with tempfile.TemporaryDirectory() as source_dir, tempfile.TemporaryDirectory() as target_dir:
        vid_path = os.path.join(source_dir, "raw_video.mov")
        _create_mock_video_file(vid_path, size=20480)
        vid_sha = CaptureValidator.compute_sha256(vid_path)

        imu_path = os.path.join(source_dir, "imu_samples.csv")
        _create_mock_imu_file(imu_path, size=1024)
        imu_sha = CaptureValidator.compute_sha256(imu_path)

        manifest = _build_valid_manifest(source_dir, vid_sha, imu_sha)

        # Write master manifest.json into source directory
        manifest_path = os.path.join(source_dir, CaptureArtifactNaming.MANIFEST_FILENAME)
        with open(manifest_path, "w") as f:
            f.write(manifest.model_dump_json(indent=2))

        # Bundle into archive
        archive_path = os.path.join(source_dir, "bundle.tar.gz")
        CapturePackage.export_archive(source_dir, archive_path)
        assert os.path.exists(archive_path)

        # Unpack archive into independent target directory
        unpacked_manifest = CapturePackage.unpack_archive(archive_path, target_dir)
        assert str(unpacked_manifest.capture_id) == str(manifest.capture_id)

        # Reproduce capture solely from directory contents
        reproduced_manifest, report = CapturePackage.reproduce_from_directory(target_dir)
        assert reproduced_manifest.capture_id == manifest.capture_id
        assert report.is_valid is True
        assert len(report.errors) == 0
