#!/usr/bin/env python3
"""
Unit tests and quantitative benchmark validation for Depth Estimation (Point 20)
Measures AbsRel, RMSE, delta < 1.25 threshold accuracy, MAD outlier rejection,
multi-view depth consistency, and Point 20 -> Point 21 data contract.
"""

import os
import json
import shutil
import unittest
import numpy as np
import cv2

from depth_estimator import DepthEstimator


class TestDepthEstimatorEscalation(unittest.TestCase):
    def setUp(self):
        self.test_dir = "/tmp/vastu_test_depth_escalation"
        self.prep_dir = os.path.join(self.test_dir, "preprocessing")
        self.keyframes_dir = os.path.join(self.prep_dir, "keyframes")
        self.track_dir = os.path.join(self.test_dir, "tracking")
        self.sfm_dir = os.path.join(self.test_dir, "sfm")
        self.output_dir = os.path.join(self.test_dir, "depth_output")

        os.makedirs(self.keyframes_dir, exist_ok=True)
        os.makedirs(self.track_dir, exist_ok=True)
        os.makedirs(self.sfm_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        self.w, self.h = 320, 240
        self.fx, self.fy = 300.0, 300.0
        self.cx, self.cy = 160.0, 120.0
        self.K = np.array([
            [self.fx, 0.0, self.cx],
            [0.0, self.fy, self.cy],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        # Ground Truth Synthetic Scene Creation:
        # Background Wall at Z = 3.5m
        # Floor plane sloping from Z = 1.8m to 3.5m
        # Furniture Box at Z = 2.0m
        # Thin Object at Z = 1.2m
        self.gt_depth = np.full((self.h, self.w), 3.5, dtype=np.float32)

        # Floor slope
        for y in range(120, self.h):
            self.gt_depth[y, :] = 1.8 + (1.0 - (y - 120) / 120.0) * 1.7

        # Furniture Box (y: 60..180, x: 50..150)
        self.gt_depth[60:180, 50:150] = 2.0

        # Thin Vertical Stand (y: 30..200, x: 230..236)
        self.gt_depth[30:200, 230:236] = 1.2

        # Generate 2 consecutive keyframe images simulating camera panning
        self.cam_positions = [
            np.array([0.0, 0.0, 0.0]),
            np.array([0.15, 0.0, 0.0])
        ]

        self.keyframe_names = []
        poses_meta = []
        keyframes_meta = []

        for idx, pos in enumerate(self.cam_positions):
            fname = f"keyframe_{idx:04d}.jpg"
            img = np.full((self.h, self.w, 3), 190, dtype=np.uint8)

            # Floor color gradient
            for y in range(120, self.h):
                img[y, :] = [int(130 + y*0.2), int(100 + y*0.15), 80]

            # Shift furniture based on camera position
            shift_x = int(idx * 20)
            cv2.rectangle(img, (50 - shift_x, 60), (150 - shift_x, 180), (60, 80, 120), -1) # Furniture
            cv2.rectangle(img, (230 - shift_x, 30), (236 - shift_x, 200), (30, 30, 30), -1) # Thin stand

            fpath = os.path.join(self.keyframes_dir, fname)
            cv2.imwrite(fpath, img)
            self.keyframe_names.append(fname)

            keyframes_meta.append({"keyframe_id": idx + 1, "file_name": fname})
            poses_meta.append({
                "keyframe_id": idx + 1,
                "file_name": fname,
                "position": [float(pos[0]), float(pos[1]), float(pos[2])],
                "rotation_matrix": [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
            })

        # Save calibration.json
        calib_data = {
            "camera_model": "PINHOLE_RADIAL",
            "image_width": self.w,
            "image_height": self.h,
            "intrinsics": {"fx": self.fx, "fy": self.fy, "cx": self.cx, "cy": self.cy}
        }
        with open(os.path.join(self.prep_dir, "calibration.json"), "w") as f:
            json.dump(calib_data, f, indent=2)

        with open(os.path.join(self.prep_dir, "preprocessing_manifest.json"), "w") as f:
            json.dump({"keyframes": keyframes_meta}, f, indent=2)

        with open(os.path.join(self.track_dir, "camera_poses.json"), "w") as f:
            json.dump({"poses": poses_meta}, f, indent=2)

        # Save Point 19 sparse SfM geometric anchors (ground-truth reference anchors)
        sfm_anchors = [
            {"point_id": 1, "position": [-0.6, 0.4, 3.5], "color": [190, 190, 190]},
            {"point_id": 2, "position": [0.7, 0.5, 3.5], "color": [190, 190, 190]},
            {"point_id": 3, "position": [-0.3, 0.0, 2.0], "color": [60, 80, 120]},
            {"point_id": 4, "position": [-0.1, -0.2, 2.0], "color": [60, 80, 120]},
            {"point_id": 5, "position": [0.4, 0.1, 1.2], "color": [30, 30, 30]},
            # Add 1 artificial noisy outlier anchor to test MAD filtering
            {"point_id": 6, "position": [0.0, 0.0, 19.5], "color": [0, 0, 0]}
        ]
        with open(os.path.join(self.sfm_dir, "sparse_points3D.json"), "w") as f:
            json.dump(sfm_anchors, f, indent=2)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_level_1_mad_scale_alignment_and_outlier_rejection(self):
        """
        Level 1: Tests MAD scale alignment, outlier rejection, and scale confidence.
        """
        estimator = DepthEstimator(device="cpu")
        with open(os.path.join(self.sfm_dir, "sparse_points3D.json")) as f:
            sfm_anchors = json.load(f)

        img_path = os.path.join(self.keyframes_dir, self.keyframe_names[0])
        img = cv2.imread(img_path)
        rel_depth, raw_conf = estimator.estimate_relative_depth_and_confidence(img)

        scale_res = estimator.align_metric_scale_with_sfm_mad(
            rel_depth, sfm_anchors, self.K, np.eye(3), np.zeros((3, 1))
        )

        # Verify MAD successfully rejected outlier anchor (point_id 6)
        self.assertGreater(scale_res["rejected_anchors"], 0)
        self.assertGreaterEqual(scale_res["valid_anchors"], 4)
        self.assertGreater(scale_res["scale_confidence"], 0.70)
        self.assertLess(scale_res["scale_uncertainty"], 0.50)
        self.assertGreater(scale_res["scale_factor"], 0.5)

    def test_level_2_quantitative_accuracy_metrics(self):
        """
        Level 2: Quantitative Depth Accuracy Validation (AbsRel, RMSE, delta < 1.25).
        """
        estimator = DepthEstimator(device="cpu")
        with open(os.path.join(self.sfm_dir, "sparse_points3D.json")) as f:
            sfm_anchors = json.load(f)

        img_path = os.path.join(self.keyframes_dir, self.keyframe_names[0])
        res = estimator.process_keyframe(
            img_path, self.K, np.eye(3), np.zeros((3, 1)), sfm_anchors, self.output_dir, 1
        )

        pred_depth = np.load(os.path.join(self.output_dir, res["depth_npy"]))

        # Calculate standard Computer Vision Depth Metrics
        valid_mask = (self.gt_depth > 0.1) & (pred_depth > 0.1)
        gt_v = self.gt_depth[valid_mask]
        pred_v = pred_depth[valid_mask]

        # 1. Absolute Relative Error: mean(|d_pred - d_gt| / d_gt)
        abs_rel = float(np.mean(np.abs(pred_v - gt_v) / gt_v))

        # 2. Root Mean Squared Error (RMSE)
        rmse = float(np.sqrt(np.mean((pred_v - gt_v)**2)))

        # 3. Threshold Accuracy: delta = max(d_pred/d_gt, d_gt/d_pred) < 1.25
        ratios = np.maximum(pred_v / gt_v, gt_v / pred_v)
        delta_125 = float(np.mean(ratios < 1.25))

        print(f"\n[Depth Benchmark Metrics] AbsRel: {abs_rel:.4f}, RMSE: {rmse:.3f}m, delta<1.25: {delta_125*100:.1f}%")

        self.assertLess(abs_rel, 0.40, "AbsRel must be strictly bounded")
        self.assertLess(rmse, 1.40, "RMSE must be within indoor tolerances")
        self.assertGreater(delta_125, 0.30, "Delta < 1.25 accuracy must meet benchmark threshold")

    def test_level_4_multi_view_depth_consistency(self):
        """
        Level 4: Tests cross-keyframe geometric depth re-projection consistency.
        """
        estimator = DepthEstimator(device="cpu")
        manifest = estimator.estimate_depth_for_sequence(
            self.prep_dir, self.track_dir, self.sfm_dir, self.output_dir, capture_duration_s=10.0
        )

        self.assertEqual(manifest["total_depth_maps"], 2)
        self.assertGreaterEqual(manifest["multi_view_consistency_pct"], 75.0)
        self.assertTrue(manifest["benchmark"]["meets_speed_target"])
        self.assertEqual(manifest["version"], "2.0.0_COMPETITION_READY")

    def test_level_7_point_20_to_point_21_data_contract(self):
        """
        Level 7 & 8: Verifies clean output contracts for Point 21 Dense Point Cloud fusion.
        """
        estimator = DepthEstimator(device="cpu")
        manifest = estimator.estimate_depth_for_sequence(
            self.prep_dir, self.track_dir, self.sfm_dir, self.output_dir
        )
        manifest_file = os.path.join(self.output_dir, "depth_manifest.json")
        self.assertTrue(os.path.exists(manifest_file))

        self.assertIn("point_21_data_contract", manifest)
        self.assertTrue(manifest["point_21_data_contract"]["spatial_ready"])
        self.assertEqual(len(manifest["frames"]), 2)

        # Check frame 1 files
        f0 = manifest["frames"][0]
        depth_png = os.path.join(self.output_dir, f0["depth_png"])
        conf_png = os.path.join(self.output_dir, f0["confidence_png"])
        depth_npy = os.path.join(self.output_dir, f0["depth_npy"])

        self.assertTrue(os.path.exists(depth_png))
        self.assertTrue(os.path.exists(conf_png))
        self.assertTrue(os.path.exists(depth_npy))


if __name__ == "__main__":
    unittest.main()
