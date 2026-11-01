"""
VĀSTU v3.0 — Capture Package Schema v1.0 Unit Tests
====================================================
Tests Pydantic v2 contract enforcement for the zero-LiDAR capture package.
"""

import unittest
import numpy as np
from core.coordinates.conventions import CameraConvention, WorldConvention
from core.schemas.capture_package_v1 import (
    CaptureManifestV1,
    CameraPoseRecord,
    CameraIntrinsicsRecord,
    TrackingState,
    TrackingStateEvent,
    FloorAnchorObservation,
    FloorBoundaryObservation,
)


class TestCapturePackageSchema(unittest.TestCase):

    def test_valid_manifest(self):
        """Verify valid CaptureManifestV1 creates properly and serializes to dict."""
        manifest = CaptureManifestV1(
            session_id="session_test_123",
            device_model="iPhone14,2",
            frame_count=120,
            capture_start_ns=1700000000000000000,
            capture_end_ns=1700000030000000000,
            checksums={"manifest.json": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}
        )
        self.assertEqual(manifest.schema_version, "1.0.0")
        self.assertEqual(manifest.camera_convention, CameraConvention.ARKIT_RUB)
        self.assertEqual(manifest.world_convention, WorldConvention.RIGHT_HANDED_Y_UP)
        self.assertEqual(manifest.units, "meters")

        data = manifest.model_dump()
        self.assertEqual(data["session_id"], "session_test_123")
        self.assertEqual(data["frame_count"], 120)

    def test_manifest_timestamp_reversal_rejected(self):
        """Verify capture_end_ns < capture_start_ns is rejected."""
        with self.assertRaises(ValueError):
            CaptureManifestV1(
                session_id="session_invalid_ts",
                device_model="iPhone14,2",
                frame_count=10,
                capture_start_ns=2000,
                capture_end_ns=1000  # Invalid!
            )

    def test_valid_camera_pose_record(self):
        """Verify valid CameraPoseRecord with genuine orthonormal rotation matrix."""
        # Construct valid 4x4 matrix with 30 deg rotation around Y
        theta = np.radians(30.0)
        R = np.array([
            [np.cos(theta), 0.0, np.sin(theta)],
            [0.0,           1.0, 0.0],
            [-np.sin(theta), 0.0, np.cos(theta)]
        ])
        t = np.array([1.2, 0.5, -2.3])
        
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = t

        record = CameraPoseRecord(
            frame_id="frame_000001.jpg",
            timestamp_ns=1000000,
            T_world_camera=T.tolist(),
            image_width=1920,
            image_height=1080,
            tracking_state=TrackingState.NORMAL
        )
        self.assertEqual(record.frame_id, "frame_000001.jpg")
        self.assertEqual(record.tracking_state, TrackingState.NORMAL)

    def test_camera_pose_non_orthonormal_rejected(self):
        """Verify non-orthonormal rotation matrices are rejected."""
        # Non-orthogonal matrix (skewed)
        T = np.eye(4)
        T[0, 1] = 0.5  # Skew
        with self.assertRaises(ValueError):
            CameraPoseRecord(
                frame_id="frame_bad_rot.jpg",
                timestamp_ns=1000,
                T_world_camera=T.tolist(),
                image_width=1920,
                image_height=1080
            )

    def test_camera_pose_non_finite_rejected(self):
        """Verify NaN or Inf in translation is rejected."""
        T = np.eye(4)
        T[0, 3] = float("nan")
        with self.assertRaises(ValueError):
            CameraPoseRecord(
                frame_id="frame_nan.jpg",
                timestamp_ns=1000,
                T_world_camera=T.tolist(),
                image_width=1920,
                image_height=1080
            )

    def test_camera_intrinsics_validation(self):
        """Verify camera intrinsics checks valid principal point ranges."""
        # Valid intrinsics
        intrinsics = CameraIntrinsicsRecord(
            fx=1440.0,
            fy=1440.0,
            cx=960.0,
            cy=540.0,
            image_width=1920,
            image_height=1080
        )
        self.assertEqual(intrinsics.fx, 1440.0)

        # Invalid cx (far outside 0.25*W to 0.75*W)
        with self.assertRaises(ValueError):
            CameraIntrinsicsRecord(
                fx=1440.0,
                fy=1440.0,
                cx=100.0,  # 100 < 0.25*1920 (480)
                cy=540.0,
                image_width=1920,
                image_height=1080
            )

    def test_tracking_state_event(self):
        """Verify TrackingStateEvent serialization."""
        event = TrackingStateEvent(
            timestamp_ns=1500000000,
            previous_state=TrackingState.LIMITED_INITIALIZING,
            current_state=TrackingState.NORMAL,
            reason="Sufficient features detected"
        )
        self.assertEqual(event.current_state, TrackingState.NORMAL)
        self.assertEqual(event.previous_state, TrackingState.LIMITED_INITIALIZING)


if __name__ == "__main__":
    unittest.main()
