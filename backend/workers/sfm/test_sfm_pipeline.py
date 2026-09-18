#!/usr/bin/env python3
"""
Unit tests for Structure-from-Motion (Point 19)
"""

import os
import json
import shutil
import unittest
import numpy as np
import cv2

from sfm_pipeline import SfMPipeline, Landmark3D

class TestSfMPipeline(unittest.TestCase):
    def setUp(self):
        self.test_dir = "/tmp/vastu_test_sfm"
        self.preprocessing_dir = os.path.join(self.test_dir, "preprocessing")
        self.keyframes_dir = os.path.join(self.preprocessing_dir, "keyframes")
        self.tracking_dir = os.path.join(self.test_dir, "tracking")
        self.output_dir = os.path.join(self.test_dir, "sfm_output")

        os.makedirs(self.keyframes_dir, exist_ok=True)
        os.makedirs(self.tracking_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)

        # Setup Camera Intrinsics
        self.fx, self.fy = 500.0, 500.0
        self.cx, self.cy = 320.0, 240.0
        self.K = np.array([
            [self.fx, 0.0, self.cx],
            [0.0, self.fy, self.cy],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        # Create lightweight textured 3D scene
        np.random.seed(42)
        base_canvas = np.random.randint(50, 200, (600, 800, 3), dtype=np.uint8)
        # Add rich corner features
        for y in range(60, 540, 60):
            for x in range(60, 740, 60):
                color = (int((x * 3) % 255), int((y * 5) % 255), int((x + y) % 255))
                cv2.circle(base_canvas, (x, y), 5, color, -1)
                cv2.rectangle(base_canvas, (x - 8, y - 8), (x + 8, y + 8), (255, 255, 255), 1)

        # Simulate 3 camera views with horizontal translation
        # Baseline = 0.15m per keyframe
        self.cam_positions = [
            np.array([0.0, 0.0, 0.0]),
            np.array([0.15, 0.0, 0.0]),
            np.array([0.30, 0.0, 0.0])
        ]
        self.cam_rotations = [np.eye(3), np.eye(3), np.eye(3)]

        keyframes_meta = []
        poses_meta = []

        for idx, pos in enumerate(self.cam_positions):
            fname = f"keyframe_{idx:04d}.jpg"
            shift_px = int(idx * 20)
            frame = base_canvas[50:530, 50 + shift_px : 690 + shift_px]
            fpath = os.path.join(self.keyframes_dir, fname)
            cv2.imwrite(fpath, frame)

            keyframes_meta.append({
                "keyframe_id": idx + 1,
                "timestamp_ns": 1700000000000000000 + idx * 100000000,
                "file_name": fname
            })

            poses_meta.append({
                "keyframe_id": idx + 1,
                "timestamp_ns": 1700000000000000000 + idx * 100000000,
                "file_name": fname,
                "position": [float(pos[0]), float(pos[1]), float(pos[2])],
                "rotation_matrix": [[float(v) for v in row] for row in self.cam_rotations[idx]]
            })

        # Save calibration.json
        calib_data = {
            "camera_model": "PINHOLE_RADIAL",
            "image_width": 640,
            "image_height": 480,
            "intrinsics": {
                "fx": self.fx,
                "fy": self.fy,
                "cx": self.cx,
                "cy": self.cy
            }
        }
        with open(os.path.join(self.preprocessing_dir, "calibration.json"), "w") as f:
            json.dump(calib_data, f, indent=2)

        # Save preprocessing_manifest.json
        manifest_data = {
            "capture_id": "test-sfm-19",
            "keyframes": keyframes_meta
        }
        with open(os.path.join(self.preprocessing_dir, "preprocessing_manifest.json"), "w") as f:
            json.dump(manifest_data, f, indent=2)

        # Save camera_poses.json
        poses_data = {
            "poses": poses_meta
        }
        with open(os.path.join(self.tracking_dir, "camera_poses.json"), "w") as f:
            json.dump(poses_data, f, indent=2)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def test_triangulation_and_projection(self):
        sfm = SfMPipeline(min_triangulation_angle_deg=0.5)
        R1 = np.eye(3)
        t1 = np.zeros((3, 1))
        R2 = np.eye(3)
        t2 = np.array([[-0.2], [0.0], [0.0]]) # Camera 2 translated right: C = [0.2, 0, 0] -> t = -R*C = [-0.2, 0, 0]

        pt_3d_gt = np.array([0.1, -0.05, 3.0])
        proj1 = sfm.project_point(self.K, R1, t1, pt_3d_gt)
        proj2 = sfm.project_point(self.K, R2, t2, pt_3d_gt)

        self.assertIsNotNone(proj1)
        self.assertIsNotNone(proj2)

        pts1 = np.array([proj1])
        pts2 = np.array([proj2])

        tri_pts, valid = sfm.triangulate_two_views(self.K, R1, t1, R2, t2, pts1, pts2)
        self.assertTrue(valid[0])
        self.assertAlmostEqual(tri_pts[0, 0], pt_3d_gt[0], places=2)
        self.assertAlmostEqual(tri_pts[0, 1], pt_3d_gt[1], places=2)
        self.assertAlmostEqual(tri_pts[0, 2], pt_3d_gt[2], places=2)

    def test_bundle_adjustment_refinement(self):
        sfm = SfMPipeline(max_reprojection_error=3.0)
        cam_poses = [
            {'R': np.eye(3), 't': np.zeros((3, 1))},
            {'R': np.eye(3), 't': np.array([[-0.2], [0.0], [0.0]])},
            {'R': np.eye(3), 't': np.array([[0.0], [-0.2], [0.0]])}
        ]

        # Generate 8 ground-truth 3D landmarks
        landmarks = []
        initial_errors = []
        true_points = []

        np.random.seed(42)
        for p_i in range(8):
            pt_true = np.array([
                -0.3 + 0.1 * (p_i % 4),
                -0.2 + 0.15 * (p_i // 4),
                2.5 + 0.1 * p_i
            ])
            true_points.append(pt_true)
            p1 = sfm.project_point(self.K, cam_poses[0]['R'], cam_poses[0]['t'], pt_true)
            p2 = sfm.project_point(self.K, cam_poses[1]['R'], cam_poses[1]['t'], pt_true)
            p3 = sfm.project_point(self.K, cam_poses[2]['R'], cam_poses[2]['t'], pt_true)

            obs = [(0, p_i, p1[0], p1[1]), (1, p_i, p2[0], p2[1]), (2, p_i, p3[0], p3[1])]
            perturbation = np.array([0.03, -0.02, 0.04])
            perturbed_xyz = pt_true + perturbation
            initial_errors.append(np.linalg.norm(perturbation))

            lm = Landmark3D(point_id=p_i + 1, xyz=perturbed_xyz, color_rgb=(255, 0, 0), observations=obs)
            landmarks.append(lm)

        ref_poses, ref_landmarks = sfm.run_bundle_adjustment(self.K, cam_poses, landmarks)
        # Calculate reprojection error before and after BA
        def calc_mean_reproj_err(cams, lms):
            errs = []
            for lm in lms:
                for c_idx, _, u, v in lm.observations:
                    proj = sfm.project_point(self.K, cams[c_idx]['R'], cams[c_idx]['t'], lm.xyz)
                    if proj is not None:
                        errs.append(np.hypot(proj[0] - u, proj[1] - v))
            return float(np.mean(errs)) if errs else 0.0

        init_repr_err = calc_mean_reproj_err(cam_poses, landmarks)
        final_repr_err = calc_mean_reproj_err(ref_poses, ref_landmarks)

        # Reprojection error must drop significantly (e.g. from >5px to <1px)
        self.assertLess(final_repr_err, init_repr_err)
        self.assertLess(final_repr_err, 1.0)

    def test_full_sfm_pipeline_execution(self):
        sfm = SfMPipeline(min_triangulation_angle_deg=0.2, max_reprojection_error=4.0)
        stats = sfm.run_reconstruction(self.preprocessing_dir, self.tracking_dir, self.output_dir)

        # Check output statistics
        self.assertEqual(stats["registered_keyframes"], 3)
        self.assertGreater(stats["total_sparse_points"], 0)

        # Check output files exist and are valid
        ply_file = os.path.join(self.output_dir, "sparse_points3D.ply")
        json_file = os.path.join(self.output_dir, "sparse_points3D.json")
        stats_file = os.path.join(self.output_dir, "reconstruction_stats.json")

        self.assertTrue(os.path.exists(ply_file))
        self.assertTrue(os.path.exists(json_file))
        self.assertTrue(os.path.exists(stats_file))

        # Check PLY Header
        with open(ply_file, "r") as f:
            header_lines = [f.readline() for _ in range(8)]
            self.assertTrue(any("element vertex" in l for l in header_lines))

        # Check JSON point structure
        with open(json_file, "r") as f:
            points_data = json.load(f)
            self.assertGreater(len(points_data), 0)
            self.assertIn("position", points_data[0])
            self.assertIn("color", points_data[0])
            self.assertEqual(len(points_data[0]["position"]), 3)
            self.assertEqual(len(points_data[0]["color"]), 3)

if __name__ == "__main__":
    unittest.main()
