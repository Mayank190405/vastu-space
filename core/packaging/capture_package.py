"""
VĀSTU Core Packaging Engine: Standalone Capture Reproducibility
Guarantees that a capture can be bundled, exported, downloaded independently,
and completely reproduced from its manifest without relying on undocumented or external database state.
"""

import os
import tarfile
import json
from typing import Tuple, Optional
import uuid
from core.schemas.capture_manifest import CaptureManifest
from core.validation.capture_validator import CaptureValidator, CaptureValidationReport
from storage.naming import CaptureArtifactNaming

class CapturePackage:
    """
    Self-contained capture bundle format and offline reproducibility manager.
    """

    @classmethod
    def export_archive(cls, capture_dir: str, output_archive_path: str) -> str:
        """
        Bundles a validated capture folder into a compressed archive.
        """
        manifest_path = os.path.join(capture_dir, CaptureArtifactNaming.MANIFEST_FILENAME)
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Missing master manifest in {capture_dir}")

        os.makedirs(os.path.dirname(os.path.abspath(output_archive_path)), exist_ok=True)
        with tarfile.open(output_archive_path, "w:gz") as tar:
            for item in os.listdir(capture_dir):
                item_path = os.path.join(capture_dir, item)
                tar.add(item_path, arcname=item)

        return output_archive_path

    @classmethod
    def unpack_archive(cls, archive_path: str, destination_dir: str) -> CaptureManifest:
        """
        Extracts a capture archive to a destination folder and parses the master manifest.
        """
        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Archive file not found: {archive_path}")

        os.makedirs(destination_dir, exist_ok=True)
        with tarfile.open(archive_path, "r:gz") as tar:
            tar.extractall(path=destination_dir)

        manifest_path = os.path.join(destination_dir, CaptureArtifactNaming.MANIFEST_FILENAME)
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Extracted archive missing {CaptureArtifactNaming.MANIFEST_FILENAME}")

        with open(manifest_path, "r") as f:
            data = json.load(f)

        return CaptureManifest.model_validate(data)

    @classmethod
    def reproduce_from_directory(cls, capture_dir: str) -> Tuple[CaptureManifest, CaptureValidationReport]:
        """
        Authoritative reproducibility verification:
        Loads manifest.json from an independent local folder, runs full offline validation,
        and returns the manifest along with the validation report.
        """
        manifest_path = os.path.join(capture_dir, CaptureArtifactNaming.MANIFEST_FILENAME)
        if not os.path.exists(manifest_path):
            raise FileNotFoundError(f"Cannot reproduce capture: missing manifest at {manifest_path}")

        with open(manifest_path, "r") as f:
            data = json.load(f)

        manifest = CaptureManifest.model_validate(data)
        report = CaptureValidator.validate(manifest, base_dir_or_adapter=capture_dir)

        return manifest, report
