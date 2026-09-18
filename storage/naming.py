"""
VĀSTU Storage Engine: Deterministic Artifact Naming
Defines authoritative, collision-free storage keys and paths for all capture assets.
"""

import os
import uuid
from typing import Dict, Any, Union

class CaptureArtifactNaming:
    """
    Hierarchical, deterministic storage key generator.
    Structure: captures/{project_id}/{capture_id}/{artifact_filename}
    """

    MANIFEST_FILENAME = "manifest.json"
    VIDEO_FILENAME_DEFAULT = "raw_video.mov"
    IMU_FILENAME_DEFAULT = "imu_samples.csv"
    TIMESTAMPS_FILENAME = "frame_timestamps.json"
    DEPTH_FILENAME = "sparse_depth.bin"
    VALIDATION_REPORT_FILENAME = "validation_report.json"
    PACKAGE_ARCHIVE_FILENAME = "capture_package.tar.gz"

    @classmethod
    def get_capture_prefix(cls, project_id: Union[uuid.UUID, str], capture_id: Union[uuid.UUID, str]) -> str:
        return f"captures/{str(project_id)}/{str(capture_id)}"

    @classmethod
    def get_manifest_key(cls, project_id: Union[uuid.UUID, str], capture_id: Union[uuid.UUID, str]) -> str:
        return f"{cls.get_capture_prefix(project_id, capture_id)}/{cls.MANIFEST_FILENAME}"

    @classmethod
    def get_video_key(
        cls,
        project_id: Union[uuid.UUID, str],
        capture_id: Union[uuid.UUID, str],
        extension: str = "mov"
    ) -> str:
        ext = extension.lstrip(".")
        return f"{cls.get_capture_prefix(project_id, capture_id)}/raw_video.{ext}"

    @classmethod
    def get_imu_key(
        cls,
        project_id: Union[uuid.UUID, str],
        capture_id: Union[uuid.UUID, str],
        extension: str = "csv"
    ) -> str:
        ext = extension.lstrip(".")
        return f"{cls.get_capture_prefix(project_id, capture_id)}/imu_samples.{ext}"

    @classmethod
    def get_timestamps_key(cls, project_id: Union[uuid.UUID, str], capture_id: Union[uuid.UUID, str]) -> str:
        return f"{cls.get_capture_prefix(project_id, capture_id)}/{cls.TIMESTAMPS_FILENAME}"

    @classmethod
    def get_depth_key(cls, project_id: Union[uuid.UUID, str], capture_id: Union[uuid.UUID, str]) -> str:
        return f"{cls.get_capture_prefix(project_id, capture_id)}/{cls.DEPTH_FILENAME}"

    @classmethod
    def get_validation_report_key(cls, project_id: Union[uuid.UUID, str], capture_id: Union[uuid.UUID, str]) -> str:
        return f"{cls.get_capture_prefix(project_id, capture_id)}/{cls.VALIDATION_REPORT_FILENAME}"

    @classmethod
    def get_package_archive_key(cls, project_id: Union[uuid.UUID, str], capture_id: Union[uuid.UUID, str]) -> str:
        return f"{cls.get_capture_prefix(project_id, capture_id)}/{cls.PACKAGE_ARCHIVE_FILENAME}"

    @classmethod
    def parse_storage_key(cls, key: str) -> Dict[str, str]:
        """
        Parses a storage key into constituent parts.
        Example: captures/abc/123/raw_video.mov -> {"project_id": "abc", "capture_id": "123", "filename": "raw_video.mov"}
        """
        clean_key = key.lstrip("/")
        parts = clean_key.split("/")
        if len(parts) >= 4 and parts[0] == "captures":
            return {
                "project_id": parts[1],
                "capture_id": parts[2],
                "filename": "/".join(parts[3:]),
            }
        raise ValueError(f"Invalid capture storage key: {key}")
