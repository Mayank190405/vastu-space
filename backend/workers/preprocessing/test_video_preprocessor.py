#!/usr/bin/env python3
"""
Unit tests for VideoPreprocessor (Point 17: Video Preprocessing)
"""

import os
import sys
import unittest
import tempfile
import numpy as np
import cv2

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from video_preprocessor import VideoPreprocessor

class TestVideoPreprocessor(unittest.TestCase):

    def setUp(self):
        self.preprocessor = VideoPreprocessor(
            min_blur_threshold=50.0,
            min_luminance=30.0,
            max_luminance=225.0,
            min_features=10,
            target_keyframe_fps=2.0
        )
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_evaluate_frame_quality_sharp(self):
        # Create synthetic sharp high-contrast texture image
        img = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(img, "VASTU SPATIAL", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
        for i in range(0, 640, 20):
            cv2.line(img, (i, 0), (i, 480), (200, 200, 200), 2)

        blur_score, mean_lum, feat_count, status = self.preprocessor.evaluate_frame_quality(img)
        self.assertGreater(blur_score, 50.0)
        self.assertEqual(status, "VALID")
        self.assertGreater(feat_count, 10)

    def test_evaluate_frame_quality_blurry(self):
        # Create blurry image using heavy Gaussian blur on normal illuminated background
        img = np.ones((480, 640, 3), dtype=np.uint8) * 128
        cv2.putText(img, "BLUR TEST", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 2)
        blurry = cv2.GaussianBlur(img, (45, 45), 0)

        blur_score, _, _, status = self.preprocessor.evaluate_frame_quality(blurry)
        self.assertEqual(status, "BLURRY")

    def test_evaluate_frame_quality_underexposed(self):
        # Extremely dark image
        dark_img = np.ones((480, 640, 3), dtype=np.uint8) * 10
        _, mean_lum, _, status = self.preprocessor.evaluate_frame_quality(dark_img)
        self.assertLess(mean_lum, 25.0)
        self.assertEqual(status, "UNDEREXPOSED")

    def test_imu_interpolation(self):
        imu_samples = [
            {"timestamp_ns": 1000000000, "sensor_type": "ACCELEROMETER", "x": 0.0, "y": 9.8, "z": 0.0, "accuracy": 3},
            {"timestamp_ns": 1000000000, "sensor_type": "GYROSCOPE", "x": 0.1, "y": 0.2, "z": 0.0, "accuracy": 3},
            {"timestamp_ns": 1000020000, "sensor_type": "ACCELEROMETER", "x": 0.2, "y": 9.6, "z": 0.0, "accuracy": 3},
            {"timestamp_ns": 1000020000, "sensor_type": "GYROSCOPE", "x": 0.3, "y": 0.4, "z": 0.0, "accuracy": 3}
        ]

        target_ts = 1000010000 # Exactly halfway
        result = self.preprocessor.interpolate_imu_at_timestamp(target_ts, imu_samples)

        self.assertAlmostEqual(result["accel"][0], 0.1, places=2)
        self.assertAlmostEqual(result["accel"][1], 9.7, places=2)
        self.assertAlmostEqual(result["gyro"][0], 0.2, places=2)

    def test_full_video_pipeline(self):
        # Create a mock 1-second 30fps video
        video_path = os.path.join(self.temp_dir, "test_video.mp4")
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, 30.0, (640, 480))

        for f in range(30):
            frame = np.ones((480, 640, 3), dtype=np.uint8) * 128
            cv2.putText(frame, f"FRAME {f}", (50, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3)
            for i in range(0, 640, 30):
                cv2.circle(frame, (i, (f * 10) % 480), 8, (180, 180, 180), -1)
            out.write(frame)
        out.release()

        # Create mock IMU CSV
        imu_path = os.path.join(self.temp_dir, "imu.csv")
        with open(imu_path, "w", encoding="utf-8") as f:
            f.write("timestamp_ns,sensor_type,x,y,z,accuracy\n")
            for i in range(100):
                ts = 1725475200000000 + (i * 10000000)
                f.write(f"{ts},ACCELEROMETER,0.1,9.81,0.0,3\n")
                f.write(f"{ts},GYROSCOPE,0.01,0.02,0.0,3\n")

        manifest = self.preprocessor.process_capture(
            video_path=video_path,
            imu_path=imu_path,
            sync_manifest_path="",
            output_dir=self.temp_dir
        )

        self.assertIn("video_metadata", manifest)
        self.assertEqual(manifest["video_metadata"]["total_frames"], 30)
        self.assertGreater(manifest["preprocessing_summary"]["selected_keyframes"], 0)
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "calibration.json")))
        self.assertTrue(os.path.exists(os.path.join(self.temp_dir, "quality_report.json")))


if __name__ == "__main__":
    unittest.main()
