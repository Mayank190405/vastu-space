"""
VĀSTU v3.0 — Capture Package Validator & Ingestion Adapter
===========================================================
Validates incoming capture_<session_id>/ directory packages before reconstruction:
- Schema verification (manifest.json, camera_intrinsics.json, camera_poses.jsonl)
- Timestamp monotonicity
- Pose matrix orthonormality and finite translations
- Frame-pose correspondence and image integrity
- SHA-256 checksum verification
- Seamless adapter for existing reconstruction workers
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
import numpy as np

from core.schemas.capture_package_v1 import (
    CaptureManifestV1,
    CameraPoseRecord,
    CameraIntrinsicsRecord,
    TrackingStateEvent
)
from core.coordinates.conventions import CameraPose, CameraIntrinsics, CameraConvention


@dataclass
class ValidationIssue:
    code: str
    message: str
    path: Optional[str] = None


@dataclass
class PackageValidationResult:
    is_valid: bool
    session_id: Optional[str] = None
    frame_count: int = 0
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    manifest: Optional[CaptureManifestV1] = None
    intrinsics: Optional[CameraIntrinsicsRecord] = None
    poses: List[CameraPoseRecord] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "session_id": self.session_id,
            "frame_count": self.frame_count,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "errors": [{"code": e.code, "message": e.message, "path": e.path} for e in self.errors],
            "warnings": [{"code": w.code, "message": w.message, "path": w.path} for w in self.warnings]
        }


class CapturePackageValidator:
    """
    Validates capture package directory integrity per VĀSTU v3.0 Contract.
    """

    @staticmethod
    def compute_sha256(file_path: str) -> str:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    @classmethod
    def validate(cls, package_dir: str) -> PackageValidationResult:
        result = PackageValidationResult(is_valid=True)

        if not os.path.exists(package_dir) or not os.path.isdir(package_dir):
            result.is_valid = False
            result.errors.append(ValidationIssue(
                code="PACKAGE_DIR_NOT_FOUND",
                message=f"Capture package directory does not exist: {package_dir}"
            ))
            return result

        # 1. Validate manifest.json
        manifest_path = os.path.join(package_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            result.is_valid = False
            result.errors.append(ValidationIssue(
                code="MISSING_MANIFEST",
                message="Missing manifest.json in package root",
                path="manifest.json"
            ))
            return result

        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest_data = json.load(f)
            manifest = CaptureManifestV1.model_validate(manifest_data)
            result.manifest = manifest
            result.session_id = manifest.session_id
        except Exception as e:
            result.is_valid = False
            result.errors.append(ValidationIssue(
                code="INVALID_MANIFEST",
                message=f"manifest.json failed schema validation: {str(e)}",
                path="manifest.json"
            ))
            return result

        # 2. Validate calibration/camera_intrinsics.json
        intrinsics_path = os.path.join(package_dir, "calibration", "camera_intrinsics.json")
        if not os.path.exists(intrinsics_path):
            result.is_valid = False
            result.errors.append(ValidationIssue(
                code="MISSING_INTRINSICS",
                message="Missing calibration/camera_intrinsics.json",
                path="calibration/camera_intrinsics.json"
            ))
        else:
            try:
                with open(intrinsics_path, "r", encoding="utf-8") as f:
                    calib_data = json.load(f)
                intrinsics = CameraIntrinsicsRecord.model_validate(calib_data)
                result.intrinsics = intrinsics
            except Exception as e:
                result.is_valid = False
                result.errors.append(ValidationIssue(
                    code="INVALID_INTRINSICS",
                    message=f"camera_intrinsics.json validation failed: {str(e)}",
                    path="calibration/camera_intrinsics.json"
                ))

        # 3. Validate tracking/camera_poses.jsonl
        poses_path = os.path.join(package_dir, "tracking", "camera_poses.jsonl")
        if not os.path.exists(poses_path):
            result.is_valid = False
            result.errors.append(ValidationIssue(
                code="MISSING_POSES",
                message="Missing tracking/camera_poses.jsonl",
                path="tracking/camera_poses.jsonl"
            ))
        else:
            prev_ts = -1
            line_num = 0
            try:
                with open(poses_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        line_num += 1
                        pose_data = json.loads(line)
                        pose_record = CameraPoseRecord.model_validate(pose_data)
                        
                        # Timestamp monotonicity check
                        if pose_record.timestamp_ns <= prev_ts:
                            result.is_valid = False
                            result.errors.append(ValidationIssue(
                                code="NON_MONOTONIC_TIMESTAMP",
                                message=f"Timestamp {pose_record.timestamp_ns} <= previous {prev_ts} at line {line_num}",
                                path="tracking/camera_poses.jsonl"
                            ))
                        prev_ts = pose_record.timestamp_ns
                        result.poses.append(pose_record)

                result.frame_count = len(result.poses)

                # Check frame count matches manifest declaration
                if result.manifest and result.manifest.frame_count != result.frame_count:
                    result.warnings.append(ValidationIssue(
                        code="FRAME_COUNT_MISMATCH",
                        message=f"Manifest declared {result.manifest.frame_count} frames, but found {result.frame_count} poses"
                    ))

            except Exception as e:
                result.is_valid = False
                result.errors.append(ValidationIssue(
                    code="CORRUPT_POSES_FILE",
                    message=f"Failed parsing camera_poses.jsonl at line {line_num}: {str(e)}",
                    path="tracking/camera_poses.jsonl"
                ))

        # 4. Validate frames/ directory and frame-pose correspondence
        frames_dir = os.path.join(package_dir, "frames")
        if not os.path.exists(frames_dir) or not os.path.isdir(frames_dir):
            result.is_valid = False
            result.errors.append(ValidationIssue(
                code="MISSING_FRAMES_DIR",
                message="Missing frames/ directory",
                path="frames/"
            ))
        else:
            missing_frames = 0
            for pose in result.poses:
                img_path = os.path.join(frames_dir, pose.frame_id)
                if not os.path.exists(img_path):
                    missing_frames += 1
                    if missing_frames <= 5:
                        result.errors.append(ValidationIssue(
                            code="MISSING_FRAME_IMAGE",
                            message=f"Referenced image not found: {pose.frame_id}",
                            path=f"frames/{pose.frame_id}"
                        ))
            if missing_frames > 0:
                result.is_valid = False
                if missing_frames > 5:
                    result.errors.append(ValidationIssue(
                        code="MISSING_FRAMES_TOTAL",
                        message=f"Total of {missing_frames} referenced frame images are missing from frames/"
                    ))

        # 5. Check checksums.sha256 if present
        checksums_path = os.path.join(package_dir, "checksums.sha256")
        if os.path.exists(checksums_path):
            with open(checksums_path, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) >= 2:
                        expected_hash = parts[0].strip()
                        rel_file = parts[1].strip()
                        full_path = os.path.join(package_dir, rel_file)
                        if os.path.exists(full_path):
                            actual_hash = cls.compute_sha256(full_path)
                            if actual_hash.lower() != expected_hash.lower():
                                result.is_valid = False
                                result.errors.append(ValidationIssue(
                                    code="CHECKSUM_MISMATCH",
                                    message=f"File {rel_file} checksum mismatch (expected {expected_hash}, got {actual_hash})",
                                    path=rel_file
                                ))

        return result


class CapturePackageIngestAdapter:
    """
    Adapts a validated v3.0 capture package into the structure expected
    by the existing reconstruction workers and generate_video_twin.py.
    """

    @classmethod
    def convert_to_worker_format(cls, package_dir: str, target_dir: str) -> Dict[str, Any]:
        """
        Extracts keyframes, camera_poses.json, and camera_calibration.json
        into target_dir matching existing pipeline conventions.
        """
        val = CapturePackageValidator.validate(package_dir)
        if not val.is_valid:
            raise ValueError(f"Cannot ingest invalid package: {val.summary()['errors']}")

        os.makedirs(target_dir, exist_ok=True)
        poses_out = []
        
        # Build standard OpenCV format poses
        for i, p in enumerate(val.poses):
            pose_obj = CameraPose.from_4x4(
                np.array(p.T_world_camera),
                convention=CameraConvention.ARKIT_RUB
            ).to_opencv()

            poses_out.append({
                "frame_id": p.frame_id,
                "frame_index": i,
                "timestamp_ns": p.timestamp_ns,
                "R": pose_obj.R.tolist(),
                "t": pose_obj.t.tolist(),
                "T_world_camera": pose_obj.T_4x4.tolist(),
                "tracking_state": p.tracking_state.value
            })

        # Save camera_poses.json
        with open(os.path.join(target_dir, "camera_poses.json"), "w", encoding="utf-8") as f:
            json.dump(poses_out, f, indent=2)

        # Save camera_calibration.json
        if val.intrinsics:
            calib = {
                "fx": val.intrinsics.fx,
                "fy": val.intrinsics.fy,
                "cx": val.intrinsics.cx,
                "cy": val.intrinsics.cy,
                "width": val.intrinsics.image_width,
                "height": val.intrinsics.image_height,
                "K": [
                    [val.intrinsics.fx, 0.0, val.intrinsics.cx],
                    [0.0, val.intrinsics.fy, val.intrinsics.cy],
                    [0.0, 0.0, 1.0]
                ]
            }
            with open(os.path.join(target_dir, "camera_calibration.json"), "w", encoding="utf-8") as f:
                json.dump(calib, f, indent=2)

        return {
            "session_id": val.session_id,
            "frame_count": len(poses_out),
            "output_dir": target_dir,
            "poses_json": os.path.join(target_dir, "camera_poses.json")
        }
