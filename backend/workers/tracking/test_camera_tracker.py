#!/usr/bin/env python3
"""
Unit tests for Camera Tracking and Pose Estimation (Point 18)
"""

import os
import json
import shutil
import unittest
import numpy as np
import cv2

from camera_tracker import CameraTracker, rotation_matrix_to_quaternion

class TestCameraTracker(unittest.TestCase):
    def setUp(self):
        self.test_dir = "/tmp/vastu_test_tracking"
        self.preprocessing_dir = os.path.join(self.test_dir, "preprocessing")
        self.keyframes_dir = os.path.join(self.preprocessing_dir, "keyframes")
        self.output_dir = os.path.join(self.test_dir, "tracking_output")

        os.makedirs(self.keyframes_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Create synthetic textured keyframes simulating camera motion
        # Generate 5 textured images with overlapping patterns shifted horizontally
        np.random.seed(42)
        base_texture = np.random.randint(0, 256, (600, 800, 3), dtype=np.uint8)
        # Add rich geometric grid lines and circles for robust SIFT keypoints
        for y in range(0, 600, 30):
            cv2.line(base_texture, (0, y), (800, y), (255, 255, 255), 2)
        for x in range(0, 800, 30):
            cv2.line(base_texture, (x, 0), (x, 600), (0, 255, 0), 2)
        for r in range(20, 200, 30):
            cv2.circle(base_texture, (400, 300), r, (0, 0, 255), 2)

        self.keyframe_files = []
        keyframes_metadata = []

        for i in range(4):
            # Shift texture by 25px per frame to simulate panning
            shifted = np.roll(base_texture, shift=i * 25, axis=1)
            # Crop to standard 480x640
            frame = shifted[50:530, 50:690]
            fname = f"keyframe_{i:04d}.jpg"
            fpath = os.path.join(self.keyframes_dir, fname)
            cv2.imwrite(fpath, frame)
            self.keyframe_files.append(fname)

            keyframes_metadata.append({
                "keyframe_id": i + 1,
                "timestamp_ns": 1700000000000000000 + i * 200000000,
                "file_name": fname,
                "imu": {
                    "accel": [0.05 * i, 9.81 + 0.02 * i, 0.01 * i],
                    "gyro": [0.01, 0.02, 0.005]
                }
            })

        # Save calibration.json
        calib_data = {
            "camera_model": "PINHOLE_RADIAL",
            "image_width": 640,
            "image_height": 480,
            "intrinsics": {
                "fx": 520.0,
                "fy": 520.0,
                "cx": 320.0,
                "cy": 240.0,
                "k1": 0.0,
                "k2": 0.0,
                "p1": 0.0,
                "p2": 0.0
            }
        }
        with open(os.path.join(self.preprocessing_dir, "calibration.json"), "w") as f:
            json.dump(calib_data, f, indent=2)

        # Save preprocessing_manifest.json
        manifest_data = {
            "capture_id": "test-cap-18",
            "total_extracted_keyframes": len(keyframes_metadata),
            "keyframes": keyframes_metadata
        }
        with open(os.path.join(self.preprocessing_dir, "preprocessing_manifest.json"), "w") as f:
            json.dump(manifest_data, f, indent=2)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_quaternion_conversion(self):
        # Identity matrix -> [1, 0, 0, 0]
        R_ident = np.eye(3)
        q = rotation_matrix_to_quaternion(R_ident)
        self.assertEqual(q, [1.0, 0.0, 0.0, 0.0])

        # 90 deg rotation around Z
        R_z90 = np.array([
            [0, -1, 0],
            [1,  0, 0],
            [0,  0, 1]
        ], dtype=np.float64)
        q_z90 = rotation_matrix_to_quaternion(R_z90)
        # Expected qw = cos(pi/4) ~ 0.7071, qz = sin(pi/4) ~ 0.7071
        self.assertAlmostEqual(q_z90[0], 0.707107, places=4)
        self.assertAlmostEqual(q_z90[3], 0.707107, places=4)

    def test_tracking_pipeline(self):
        tracker = CameraTracker()
        result = tracker.track_capture_sequence(self.preprocessing_dir, self.output_dir)

        # Verify output structure
        self.assertEqual(result["total_keyframes"], 4)
        self.assertGreater(result["trajectory_length_meters"], 0.0)
        self.assertEqual(len(result["poses"]), 4)

        # Verify initial origin pose
        p0 = result["poses"][0]
        self.assertEqual(p0["position"], [0.0, 0.0, 0.0])
        self.assertEqual(p0["quaternion"], [1.0, 0.0, 0.0, 0.0])

        # Verify generated files
        poses_file = os.path.join(self.output_dir, "camera_poses.json")
        transforms_file = os.path.join(self.output_dir, "transforms.json")
        traj_csv_file = os.path.join(self.output_dir, "trajectory.csv")

        self.assertTrue(os.path.exists(poses_file))
        self.assertTrue(os.path.exists(transforms_file))
        self.assertTrue(os.path.exists(traj_csv_file))

        # Verify NeRF transforms.json format
        with open(transforms_file, "r") as f:
            transforms = json.load(f)
            self.assertIn("camera_angle_x", transforms)
            self.assertIn("frames", transforms)
            self.assertEqual(len(transforms["frames"]), 4)
            self.assertEqual(len(transforms["frames"][0]["transform_matrix"]), 4)
            self.assertEqual(len(transforms["frames"][0]["transform_matrix"][0]), 4)

if __name__ == "__main__":
    unittest.main()
