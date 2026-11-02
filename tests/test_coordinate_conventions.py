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

    def test_camera_to_world_vs_world_to_camera_inversion(self):
        """
        Verify exact mathematical consistency between Camera-to-World (T_wc)
        and World-to-Camera (T_cw) extrinsics.
        P_c = R_cw @ P_w + t_cw  <==>  P_w = R_wc @ P_c + t_wc
        T_wc @ T_cw = I_4x4
        """
        # Test across various orientations and translations
        angles = [(0.1, -0.2, 0.3), (-0.4, 0.5, -0.1), (0.0, 0.0, 0.0)]
        translations = [np.array([1.2, -0.5, 3.4]), np.array([0.0, 0.0, 0.0]), np.array([-2.1, 1.8, -0.9])]

        for (rx, ry, rz), t in zip(angles, translations):
            Rx = np.array([[1, 0, 0], [0, np.cos(rx), -np.sin(rx)], [0, np.sin(rx), np.cos(rx)]])
            Ry = np.array([[np.cos(ry), 0, np.sin(ry)], [0, 1, 0], [-np.sin(ry), 0, np.cos(ry)]])
            Rz = np.array([[np.cos(rz), -np.sin(rz), 0], [np.sin(rz), np.cos(rz), 0], [0, 0, 1]])
            R = Rz @ Ry @ Rx

            pose = CameraPose(R_world_camera=R, t_world_camera=t, convention=CameraConvention.OPENCV_RDF)
            R_cw, t_cw = pose.world_to_camera_transform()

            # Verify inverse matrices
            self.assertTrue(np.allclose(R_cw, R.T, atol=1e-12))
            self.assertTrue(np.allclose(t_cw, -R.T @ t, atol=1e-12))

            # 4x4 matrix product must equal Identity
            T_wc = pose.T_4x4
            T_cw = pose.T_cw_4x4
            self.assertTrue(np.allclose(T_wc @ T_cw, np.eye(4), atol=1e-12))
            self.assertTrue(np.allclose(T_cw @ T_wc, np.eye(4), atol=1e-12))

            # Camera center in world coordinates
            cam_center_from_cw = -R_cw.T @ t_cw
            self.assertTrue(np.allclose(pose.camera_center_world, cam_center_from_cw, atol=1e-12))
            self.assertTrue(np.allclose(pose.camera_center_world, t, atol=1e-12))

            # Point roundtrip transformation
            np.random.seed(99)
            for _ in range(10):
                P_w = np.random.uniform(-5.0, 5.0, size=3)
                P_c = R_cw @ P_w + t_cw
                P_w_rec = R @ P_c + t
                self.assertTrue(np.allclose(P_w, P_w_rec, atol=1e-12))

    def test_handedness_and_determinants(self):
        """
        Verify that all camera and world transformations are proper rigid rotations
        in SO(3) with determinant +1.0 (no left-handed reflections or mirrored axes).
        """
        R_random = quaternion_to_rotation_matrix([0.3826834, 0.0, 0.0, 0.9238795])
        pose = CameraPose(R_world_camera=R_random, t_world_camera=[1.0, 2.0, 3.0], convention=CameraConvention.ARKIT_RUB)

        # Determinant of R_wc must be exactly +1
        self.assertTrue(np.isclose(np.linalg.det(pose.R), 1.0, atol=1e-10))

        # Determinant of R_cw must be exactly +1
        R_cw, _ = pose.world_to_camera_transform()
        self.assertTrue(np.isclose(np.linalg.det(R_cw), 1.0, atol=1e-10))

        # Converting to OpenCV RDF must preserve determinant +1
        pose_cv = pose.to_opencv()
        self.assertTrue(np.isclose(np.linalg.det(pose_cv.R), 1.0, atol=1e-10))

        # Converting back to ARKit RUB must preserve determinant +1
        pose_arkit = pose_cv.to_arkit()
        self.assertTrue(np.isclose(np.linalg.det(pose_arkit.R), 1.0, atol=1e-10))

    def test_arkit_rub_to_opencv_rdf_conversions(self):
        """
        Verify standard axis mapping between ARKit (RUB) and OpenCV (RDF):
        ARKit:  +X right, +Y up,   -Z forward
        OpenCV: +X right, +Y down, +Z forward
        """
        pose_arkit = CameraPose(
            R_world_camera=np.eye(3),
            t_world_camera=np.array([0.0, 0.0, 0.0]),
            convention=CameraConvention.ARKIT_RUB
        )
        pose_cv = pose_arkit.to_opencv()

        # ARKit optical axis forward is [0, 0, -1] in camera space
        optical_axis_arkit = pose_arkit.optical_axis_world
        self.assertTrue(np.allclose(optical_axis_arkit, [0.0, 0.0, -1.0]))

        # OpenCV optical axis forward is [0, 0, 1] in camera space
        optical_axis_cv = pose_cv.optical_axis_world
        self.assertTrue(np.allclose(optical_axis_cv, [0.0, 0.0, -1.0]))  # In world space both point into the same direction!

        # Check conversion matrix mapping
        v_arkit = np.array([1.5, 2.5, -3.5])
        v_cv = C_OPENCV_FROM_ARKIT @ v_arkit
        self.assertTrue(np.allclose(v_cv, [1.5, -2.5, 3.5]))

    def test_matrix_multiplication_order_and_pose_composition(self):
        """
        Verify relative pose composition order:
        T_w_cam2 = T_w_cam1 @ T_cam1_cam2
        """
        pose1 = CameraPose(
            R_world_camera=quaternion_to_rotation_matrix([0.0, 0.1, 0.0, 0.9949874]),
            t_world_camera=np.array([1.0, 0.5, 2.0]),
            convention=CameraConvention.OPENCV_RDF
        )
        # Relative camera motion: move forward by 0.5m (+Z in OpenCV) and yaw right
        R_rel = quaternion_to_rotation_matrix([0.0, 0.05, 0.0, 0.9987492])
        t_rel = np.array([0.05, 0.0, 0.50])
        T_rel = np.eye(4)
        T_rel[:3, :3] = R_rel
        T_rel[:3, 3] = t_rel

        T_cam2_world = pose1.T_4x4 @ T_rel
        pose2 = CameraPose.from_4x4(T_cam2_world, convention=CameraConvention.OPENCV_RDF)

        # Expected world position of camera 2
        expected_pos = pose1.R @ t_rel + pose1.t
        self.assertTrue(np.allclose(pose2.camera_center_world, expected_pos, atol=1e-12))

    def test_intrinsics_bounds_validation(self):
        """Verify CameraIntrinsics.validate_bounds correctly flags valid vs degenerate intrinsics."""
        # 1. Valid smartphone camera intrinsics
        valid_intr = CameraIntrinsics(fx=720.0, fy=720.0, cx=480.0, cy=360.0, width=960, height=720)
        report = valid_intr.validate_bounds()
        self.assertTrue(report["is_valid"])
        self.assertTrue(report["is_focal_plausible"])
        self.assertTrue(report["is_center_plausible"])
        self.assertTrue(report["is_square_pixel"])

        # 2. Implausible telephoto focal length (fx = 2500 for a 960x720 image)
        tele_intr = CameraIntrinsics(fx=2500.0, fy=2500.0, cx=480.0, cy=360.0, width=960, height=720)
        report_tele = tele_intr.validate_bounds()
        self.assertFalse(report_tele["is_valid"])
        self.assertFalse(report_tele["is_focal_plausible"])

        # 3. Off-center principal point (cx shifted by 30% from center)
        bad_center = CameraIntrinsics(fx=720.0, fy=720.0, cx=200.0, cy=360.0, width=960, height=720)
        report_center = bad_center.validate_bounds()
        self.assertFalse(report_center["is_valid"])
        self.assertFalse(report_center["is_center_plausible"])


if __name__ == "__main__":
    unittest.main()
