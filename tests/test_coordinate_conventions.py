"""
VĀSTU v3.0 — S5 Coordinate Conventions & Reprojection Tests
===========================================================
Rigorous validation suite for S5 Spike (unittest & pytest compatible):
- Quaternion & matrix conversion accuracy (< 1e-6)
- ARKit (-Z forward, +Y up) vs OpenCV (+Z forward, +Y down) consistency
- Forward projection & backprojection roundtrips (< 1.0 pixel, synthetic error < 1e-4)
- No mirrored or inverted axis artifacts
"""

import unittest
import numpy as np
from core.coordinates.conventions import (
    CameraConvention,
    WorldConvention,
    CameraIntrinsics,
    CameraPose,
    rotation_matrix_to_quaternion,
    quaternion_to_rotation_matrix,
    C_OPENCV_FROM_ARKIT,
    C_ARKIT_FROM_OPENCV
)


class TestCoordinateConventions(unittest.TestCase):

    def test_axis_conversion_matrices(self):
        """Verify C_OPENCV_FROM_ARKIT properties."""
        # Matrix must be diagonal [1, -1, -1]
        self.assertTrue(np.allclose(C_OPENCV_FROM_ARKIT, np.diag([1.0, -1.0, -1.0])))
        # Self-inverse: C @ C = I
        self.assertTrue(np.allclose(C_OPENCV_FROM_ARKIT @ C_OPENCV_FROM_ARKIT, np.eye(3)))
        # Determinant must be +1 (proper rigid rotation, not a reflection/mirroring!)
        self.assertTrue(np.isclose(np.linalg.det(C_OPENCV_FROM_ARKIT), 1.0))

    def test_quaternion_matrix_roundtrip(self):
        """Verify lossless conversion between unit quaternions and rotation matrices."""
        test_angles = [
            (0.0, 0.0, 0.0),
            (0.2, -0.3, 0.5),
            (np.pi / 4, -np.pi / 6, np.pi / 3),
            (-0.8, 1.2, -0.4)
        ]
        for rx, ry, rz in test_angles:
            Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
            Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
            Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
            R_orig = Rz @ Ry @ Rx

            q = rotation_matrix_to_quaternion(R_orig)
            self.assertTrue(np.isclose(np.linalg.norm(q), 1.0))

            R_reconstructed = quaternion_to_rotation_matrix(q)
            self.assertTrue(np.allclose(R_orig, R_reconstructed, atol=1e-6))

    def test_camera_intrinsics_rescaling(self):
        """Verify camera intrinsics rescaling preserves normalized coordinates."""
        intrinsics = CameraIntrinsics(fx=1440.0, fy=1440.0, cx=960.0, cy=540.0, width=1920, height=1080)
        scaled = intrinsics.rescale(1200, 675)

        self.assertEqual(scaled.width, 1200)
        self.assertEqual(scaled.height, 675)
        self.assertTrue(np.isclose(scaled.fx, 1440.0 * (1200 / 1920)))
        self.assertTrue(np.isclose(scaled.fy, 1440.0 * (675 / 1080)))
        self.assertTrue(np.isclose(scaled.cx, 960.0 * (1200 / 1920)))
        self.assertTrue(np.isclose(scaled.cy, 540.0 * (675 / 1080)))

    def test_arkit_opencv_consistency(self):
        """Verify ARKit camera pointing at world point projects to same pixel as OpenCV camera."""
        intrinsics = CameraIntrinsics(fx=1000.0, fy=1000.0, cx=640.0, cy=360.0, width=1280, height=720)

        P_world = np.array([0.5, 0.2, -3.0])

        pose_arkit = CameraPose(
            R_world_camera=np.eye(3),
            t_world_camera=np.array([0.0, 0.0, 0.0]),
            convention=CameraConvention.ARKIT_RUB
        )

        pose_cv = pose_arkit.to_opencv()
        self.assertEqual(pose_cv.convention, CameraConvention.OPENCV_RDF)

        uv_arkit, z_arkit = pose_arkit.project_point(P_world, intrinsics)
        uv_cv, z_cv = pose_cv.project_point(P_world, intrinsics)

        # Projections must be identical
        self.assertTrue(np.allclose(uv_arkit, uv_cv, atol=1e-9))
        self.assertTrue(np.isclose(z_arkit, 3.0, atol=1e-9))
        self.assertTrue(np.isclose(z_cv, 3.0, atol=1e-9))

    def test_synthetic_reprojection_accuracy(self):
        """
        Mandatory Spike S5 Requirement:
        Forward projection and backprojection roundtrip must satisfy synthetic error < 1.0 pixel (actual < 1e-4 px).
        """
        intrinsics = CameraIntrinsics(fx=1050.0, fy=1050.0, cx=960.0, cy=540.0, width=1920, height=1080)

        pitch = np.radians(-15.0)
        yaw = np.radians(35.0)
        Rx = np.array([[1, 0, 0], [0, np.cos(pitch), -np.sin(pitch)], [0, np.sin(pitch), np.cos(pitch)]])
        Ry = np.array([[np.cos(yaw), 0, np.sin(yaw)], [0, 1, 0], [-np.sin(yaw), 0, np.cos(yaw)]])
        R_wc = Ry @ Rx
        t_wc = np.array([1.5, 1.4, 2.0])

        pose = CameraPose(R_world_camera=R_wc, t_world_camera=t_wc, convention=CameraConvention.ARKIT_RUB)

        np.random.seed(42)
        for _ in range(50):
            u_orig = np.random.uniform(50.0, 1870.0)
            v_orig = np.random.uniform(50.0, 1030.0)
            depth_orig = np.random.uniform(0.8, 5.0)

            # Backproject to 3D world space
            P_world = pose.backproject_pixel(u_orig, v_orig, depth_orig, intrinsics)

            # Reproject back to 2D image space
            uv_reprojected, depth_reprojected = pose.project_point(P_world, intrinsics)

            pixel_error = np.linalg.norm(np.array([u_orig, v_orig]) - uv_reprojected)
            depth_error = abs(depth_orig - depth_reprojected)

            self.assertLess(pixel_error, 1e-4, f"Pixel error too high: {pixel_error} px")
            self.assertLess(depth_error, 1e-6, f"Depth error too high: {depth_error} m")

    def test_points_behind_camera_rejected(self):
        """Verify points behind camera trigger an explicit error rather than invalid negative projection."""
        intrinsics = CameraIntrinsics(fx=1000.0, fy=1000.0, cx=500.0, cy=500.0, width=1000, height=1000)
        pose = CameraPose(R_world_camera=np.eye(3), t_world_camera=np.zeros(3), convention=CameraConvention.ARKIT_RUB)

        # In ARKit, forward is -Z. A point at +Z is BEHIND the camera.
        P_behind = np.array([0.0, 0.0, 5.0])
        with self.assertRaises(ValueError):
            pose.project_point(P_behind, intrinsics)


if __name__ == "__main__":
    unittest.main()
