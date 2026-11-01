"""
VĀSTU v3.0 — Capture Package Validator Unit Tests
=================================================
Validates full capture package directory checking and ingestion adapter.
"""

import unittest
import os
import json
import shutil
import tempfile
import numpy as np

from core.validation.capture_package_validator import CapturePackageValidator, CapturePackageIngestAdapter
from core.coordinates.conventions import CameraConvention, WorldConvention


class TestCapturePackageValidator(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="vastu_pkg_test_")
        self.frames_dir = os.path.join(self.test_dir, "frames")
        self.calib_dir = os.path.join(self.test_dir, "calibration")
        self.tracking_dir = os.path.join(self.test_dir, "tracking")
        os.makedirs(self.frames_dir, exist_ok=True)
        os.makedirs(self.calib_dir, exist_ok=True)
        os.makedirs(self.tracking_dir, exist_ok=True)

        # Write manifest.json
        manifest = {
            "schema_version": "1.0.0",
            "session_id": "session_val_001",
            "device_model": "iPhone14,2",
            "camera_convention": "ARKIT_RUB",
            "world_convention": "RIGHT_HANDED_Y_UP",
            "units": "meters",
            "image_orientation": "portrait",
            "calibration_id": "calib_001",
            "frame_count": 3,
            "capture_start_ns": 1000000000,
            "capture_end_ns": 1100000000,
            "checksums": {}
        }
        with open(os.path.join(self.test_dir, "manifest.json"), "w") as f:
            json.dump(manifest, f)

        # Write camera_intrinsics.json
        intrinsics = {
            "calibration_id": "calib_001",
            "fx": 1440.0,
            "fy": 1440.0,
            "cx": 960.0,
            "cy": 540.0,
            "image_width": 1920,
            "image_height": 1080
        }
        with open(os.path.join(self.calib_dir, "camera_intrinsics.json"), "w") as f:
            json.dump(intrinsics, f)

        # Write 3 frames and camera_poses.jsonl
        poses = []
        for i in range(3):
            fname = f"frame_{i:06d}.jpg"
            # Create dummy image file
            with open(os.path.join(self.frames_dir, fname), "wb") as f:
                f.write(b"\xff\xd8\xff\xe0dummy_jpeg")

            pose = {
                "frame_id": fname,
                "timestamp_ns": 1000000000 + i * 33333333,
                "T_world_camera": [
                    [1.0, 0.0, 0.0, float(i) * 0.1],
                    [0.0, 1.0, 0.0, 1.4],
                    [0.0, 0.0, 1.0, 0.0],
                    [0.0, 0.0, 0.0, 1.0]
                ],
                "intrinsics_id": "calib_001",
                "image_width": 1920,
                "image_height": 1080,
                "tracking_state": "NORMAL"
            }
            poses.append(pose)

        with open(os.path.join(self.tracking_dir, "camera_poses.jsonl"), "w") as f:
            for p in poses:
                f.write(json.dumps(p) + "\n")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_valid_package_passes(self):
        """Verify complete and valid package passes validation."""
        val = CapturePackageValidator.validate(self.test_dir)
        self.assertTrue(val.is_valid)
        self.assertEqual(val.frame_count, 3)
        self.assertEqual(val.session_id, "session_val_001")
        self.assertEqual(len(val.errors), 0)

    def test_missing_manifest_fails(self):
        """Verify package without manifest.json is rejected."""
        os.remove(os.path.join(self.test_dir, "manifest.json"))
        val = CapturePackageValidator.validate(self.test_dir)
        self.assertFalse(val.is_valid)
        self.assertTrue(any(e.code == "MISSING_MANIFEST" for e in val.errors))

    def test_non_monotonic_timestamp_fails(self):
        """Verify timestamp step backwards is caught and rejected."""
        # Overwrite poses with non-monotonic timestamps
        with open(os.path.join(self.tracking_dir, "camera_poses.jsonl"), "w") as f:
            f.write(json.dumps({
                "frame_id": "frame_000000.jpg",
                "timestamp_ns": 2000000,
                "T_world_camera": np.eye(4).tolist(),
                "image_width": 1920,
                "image_height": 1080
            }) + "\n")
            f.write(json.dumps({
                "frame_id": "frame_000001.jpg",
                "timestamp_ns": 1000000,  # Regressive timestamp!
                "T_world_camera": np.eye(4).tolist(),
                "image_width": 1920,
                "image_height": 1080
            }) + "\n")

        val = CapturePackageValidator.validate(self.test_dir)
        self.assertFalse(val.is_valid)
        self.assertTrue(any(e.code == "NON_MONOTONIC_TIMESTAMP" for e in val.errors))

    def test_missing_image_file_fails(self):
        """Verify pose referencing non-existent image fails validation."""
        os.remove(os.path.join(self.frames_dir, "frame_000001.jpg"))
        val = CapturePackageValidator.validate(self.test_dir)
        self.assertFalse(val.is_valid)
        self.assertTrue(any(e.code == "MISSING_FRAME_IMAGE" for e in val.errors))

    def test_ingestion_adapter(self):
        """Verify IngestAdapter produces OpenCV format poses for existing backend."""
        target_dir = os.path.join(self.test_dir, "ingested_output")
        res = CapturePackageIngestAdapter.convert_to_worker_format(self.test_dir, target_dir)

        self.assertEqual(res["frame_count"], 3)
        self.assertTrue(os.path.exists(res["poses_json"]))
        self.assertTrue(os.path.exists(os.path.join(target_dir, "camera_calibration.json")))

        with open(res["poses_json"]) as f:
            poses = json.load(f)
            self.assertEqual(len(poses), 3)
            # In ARKit, identity was Eye(3).
            # Converted to OpenCV, R must have [1, -1, -1] diagonal!
            R_cv = np.array(poses[0]["R"])
            self.assertTrue(np.allclose(R_cv, np.diag([1.0, -1.0, -1.0])))


if __name__ == "__main__":
    unittest.main()
