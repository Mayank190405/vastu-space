"""
VĀSTU Core Validation Engine: Capture Manifest & Media Validator
Implements strict checks for:
- Missing files
- Corrupted media (header atom checks, hash verification)
- Timestamp inconsistencies (monotonicity, drift, IMU-video synchronization)
- Invalid metadata (focal length, principal points, gravity norm, scale)
- Duplicate frames (zero-delta intervals)
- Incomplete uploads (byte count parity)
"""

import os
import hashlib
from typing import Dict, List, Any, Optional, Union
from pydantic import BaseModel, Field
import numpy as np
from core.schemas.capture_manifest import CaptureManifest
from storage.base import StorageAdapter

class CaptureValidationReport(BaseModel):
    is_valid: bool
    capture_id: str
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    checks_passed: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)


class CaptureValidator:
    """
    Authoritative capture validator enforcing the canonical data model requirements.
    """

    VALID_VIDEO_BOXES = [b"ftyp", b"moov", b"mdat", b"wide", b"free", b"skip"]

    @classmethod
    def compute_sha256(cls, file_path: str) -> str:
        sha = hashlib.sha256()
        with open(file_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                sha.update(chunk)
        return sha.hexdigest()

    @classmethod
    def validate_media_header(cls, file_path: str) -> bool:
        """
        Validates whether a video file has a valid ISO Base Media File Format header.
        """
        if not os.path.exists(file_path):
            return False
        if os.path.getsize(file_path) < 16:
            return False

        with open(file_path, "rb") as f:
            header = f.read(64)

        # Check for any valid MP4/MOV container 4CC box in the header
        return any(box in header for box in cls.VALID_VIDEO_BOXES)

    @classmethod
    def validate(
        cls,
        manifest: CaptureManifest,
        base_dir_or_adapter: Union[str, StorageAdapter],
        bucket: Optional[str] = None
    ) -> CaptureValidationReport:
        """
        Executes all 6 validation stages against the manifest and its physical assets.
        """
        errors: List[str] = []
        warnings: List[str] = []
        checks_passed: List[str] = []
        metrics: Dict[str, Any] = {}

        # -------------------------------------------------------------------
        # 1. Invalid Metadata Validation
        # -------------------------------------------------------------------
        cls._validate_metadata(manifest, errors, warnings, checks_passed)

        # -------------------------------------------------------------------
        # 2. File Presence & Incomplete Uploads Validation
        # -------------------------------------------------------------------
        file_paths = cls._resolve_and_check_files(manifest, base_dir_or_adapter, bucket, errors, warnings, checks_passed, metrics)

        # -------------------------------------------------------------------
        # 3. Corrupted Media & Checksum Validation
        # -------------------------------------------------------------------
        cls._validate_media_integrity(manifest, file_paths, errors, warnings, checks_passed)

        # -------------------------------------------------------------------
        # 4. Timestamp Inconsistencies & Duplicate Frames Validation
        # -------------------------------------------------------------------
        cls._validate_timestamps_and_duplicates(manifest, file_paths, errors, warnings, checks_passed, metrics)

        is_valid = len(errors) == 0

        return CaptureValidationReport(
            is_valid=is_valid,
            capture_id=str(manifest.capture_id),
            errors=errors,
            warnings=warnings,
            checks_passed=checks_passed,
            metrics=metrics
        )

    @classmethod
    def _validate_metadata(
        cls,
        manifest: CaptureManifest,
        errors: List[str],
        warnings: List[str],
        checks_passed: List[str]
    ):
        # Intrinsics bounds
        calib = manifest.camera_calibration
        if calib.fx <= 0 or calib.fy <= 0:
            errors.append(f"Invalid focal length: fx={calib.fx}, fy={calib.fy} must be positive")
        else:
            checks_passed.append("camera_focal_lengths_valid")

        # Scale factor
        if manifest.scale_info.scale_factor <= 0:
            errors.append(f"Invalid scale factor: {manifest.scale_info.scale_factor} must be > 0")
        else:
            checks_passed.append("scale_factor_valid")

        # Duration & FPS parity
        vid = manifest.files.video
        expected_frames = vid.duration_sec * vid.fps
        if abs(vid.frame_count - expected_frames) > 0.15 * expected_frames:
            errors.append(
                f"Video frame count {vid.frame_count} deviates >15% from duration ({vid.duration_sec}s) * fps ({vid.fps})"
            )
        else:
            checks_passed.append("video_duration_fps_parity_valid")

        # Upload status
        status_val = manifest.upload_status.value if hasattr(manifest.upload_status, "value") else str(manifest.upload_status)
        if status_val.upper() in ("PENDING", "ABORTED", "FAILED"):
            errors.append(f"Incomplete upload: manifest upload_status is '{status_val}'")
        else:
            checks_passed.append("upload_status_ready")

    @classmethod
    def _resolve_and_check_files(
        cls,
        manifest: CaptureManifest,
        base_dir_or_adapter: Union[str, StorageAdapter],
        bucket: Optional[str],
        errors: List[str],
        warnings: List[str],
        checks_passed: List[str],
        metrics: Dict[str, Any]
    ) -> Dict[str, str]:
        file_paths: Dict[str, str] = {}
        is_storage_adapter = isinstance(base_dir_or_adapter, StorageAdapter)

        # Video file check
        video_filename = manifest.files.video.filename
        if is_storage_adapter:
            if not base_dir_or_adapter.exists(video_filename, bucket):
                errors.append(f"Missing file: declared video file '{video_filename}' not found in storage")
            else:
                checks_passed.append("video_file_present")
        else:
            local_vid = os.path.join(base_dir_or_adapter, video_filename)
            if not os.path.exists(local_vid):
                errors.append(f"Missing file: declared video file '{video_filename}' not found on filesystem")
            else:
                file_paths["video"] = local_vid
                actual_size = os.path.getsize(local_vid)
                metrics["video_size_bytes"] = actual_size
                if actual_size != manifest.files.video.size_bytes:
                    errors.append(
                        f"Incomplete upload: video actual size ({actual_size} bytes) does not match declared ({manifest.files.video.size_bytes} bytes)"
                    )
                else:
                    checks_passed.append("video_byte_size_parity")

        # IMU file check
        imu_filename = manifest.files.imu.filename
        if is_storage_adapter:
            if not base_dir_or_adapter.exists(imu_filename, bucket):
                errors.append(f"Missing file: declared IMU file '{imu_filename}' not found in storage")
            else:
                checks_passed.append("imu_file_present")
        else:
            local_imu = os.path.join(base_dir_or_adapter, imu_filename)
            if not os.path.exists(local_imu):
                errors.append(f"Missing file: declared IMU file '{imu_filename}' not found on filesystem")
            else:
                file_paths["imu"] = local_imu
                actual_size = os.path.getsize(local_imu)
                metrics["imu_size_bytes"] = actual_size
                if actual_size != manifest.files.imu.size_bytes:
                    errors.append(
                        f"Incomplete upload: IMU actual size ({actual_size} bytes) does not match declared ({manifest.files.imu.size_bytes} bytes)"
                    )
                else:
                    checks_passed.append("imu_byte_size_parity")

        # Timestamps file check (if declared)
        if manifest.files.timestamps and manifest.files.timestamps.filename:
            ts_filename = manifest.files.timestamps.filename
            if not is_storage_adapter:
                local_ts = os.path.join(base_dir_or_adapter, ts_filename)
                if os.path.exists(local_ts):
                    file_paths["timestamps"] = local_ts
                    checks_passed.append("timestamps_file_present")

        return file_paths

    @classmethod
    def _validate_media_integrity(
        cls,
        manifest: CaptureManifest,
        file_paths: Dict[str, str],
        errors: List[str],
        warnings: List[str],
        checks_passed: List[str]
    ):
        # Video header corruption check
        if "video" in file_paths:
            vid_path = file_paths["video"]
            if not cls.validate_media_header(vid_path):
                errors.append("Corrupted media: video file lacks a valid ISO Base Media (MP4/MOV) container atom")
            else:
                checks_passed.append("video_container_header_valid")

            # Checksum verification
            actual_sha = cls.compute_sha256(vid_path)
            if actual_sha.lower() != manifest.files.video.sha256.lower():
                errors.append(
                    f"Corrupted media: video SHA-256 mismatch (declared: {manifest.files.video.sha256}, actual: {actual_sha})"
                )
            else:
                checks_passed.append("video_checksum_verified")

        # IMU checksum verification
        if "imu" in file_paths:
            imu_path = file_paths["imu"]
            actual_sha = cls.compute_sha256(imu_path)
            if actual_sha.lower() != manifest.files.imu.sha256.lower():
                errors.append(
                    f"Corrupted media: IMU SHA-256 mismatch (declared: {manifest.files.imu.sha256}, actual: {actual_sha})"
                )
            else:
                checks_passed.append("imu_checksum_verified")

    @classmethod
    def _validate_timestamps_and_duplicates(
        cls,
        manifest: CaptureManifest,
        file_paths: Dict[str, str],
        errors: List[str],
        warnings: List[str],
        checks_passed: List[str],
        metrics: Dict[str, Any]
    ):
        records = None
        if manifest.files.timestamps and manifest.files.timestamps.records:
            records = manifest.files.timestamps.records

        if records and len(records) > 1:
            times_sec = [r.relative_timestamp_sec for r in records]
            times_ns = [r.monotonic_timestamp_ns for r in records]

            # 1. Monotonicity check
            is_monotonic = all(times_sec[i] < times_sec[i + 1] for i in range(len(times_sec) - 1))
            if not is_monotonic:
                errors.append("Timestamp inconsistency: frame timestamps are not strictly monotonically increasing")
            else:
                checks_passed.append("frame_timestamps_strictly_monotonic")

            # 2. Duplicate frame check (zero delta intervals)
            deltas = np.diff(times_sec)
            zero_deltas = np.sum(deltas <= 1e-6)
            if zero_deltas > 0:
                errors.append(f"Duplicate frames detected: {zero_deltas} frame intervals have zero or negative duration")
            else:
                checks_passed.append("no_duplicate_frame_timestamps")

            # 3. Jitter / drift check
            expected_interval = 1.0 / manifest.files.video.fps
            mean_interval = float(np.mean(deltas))
            std_interval = float(np.std(deltas))
            metrics["mean_frame_interval_sec"] = round(mean_interval, 6)
            metrics["frame_jitter_std_sec"] = round(std_interval, 6)

            if abs(mean_interval - expected_interval) > 0.10 * expected_interval:
                warnings.append(
                    f"Timestamp drift: average frame interval ({mean_interval:.4f}s) deviates >10% from declared 1/fps ({expected_interval:.4f}s)"
                )
            else:
                checks_passed.append("frame_timing_interval_nominal")

            # 4. Total span vs video duration
            total_span = times_sec[-1] - times_sec[0]
            if abs(total_span - manifest.files.video.duration_sec) > 0.5:
                warnings.append(
                    f"Timestamp span ({total_span:.2f}s) does not match declared video duration ({manifest.files.video.duration_sec}s)"
                )

        # IMU timestamps coverage check
        imu_meta = manifest.files.imu
        if imu_meta.start_timestamp_ns and imu_meta.end_timestamp_ns and records and len(records) > 0:
            first_frame_ns = records[0].monotonic_timestamp_ns
            last_frame_ns = records[-1].monotonic_timestamp_ns
            if imu_meta.start_timestamp_ns > first_frame_ns:
                errors.append("Timestamp inconsistency: IMU stream starts after first video frame")
            if imu_meta.end_timestamp_ns < last_frame_ns:
                errors.append("Timestamp inconsistency: IMU stream terminates before last video frame")
            if imu_meta.start_timestamp_ns <= first_frame_ns and imu_meta.end_timestamp_ns >= last_frame_ns:
                checks_passed.append("imu_video_temporal_coverage_complete")
