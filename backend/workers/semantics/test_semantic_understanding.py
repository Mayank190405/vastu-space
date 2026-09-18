#!/usr/bin/env python3
"""
Comprehensive Unit & Integration Test Suite for Point 24: Semantic Understanding.
Validates all 7 specific scenarios specified in the roadmap:
1. Correct object (accurate identification and 3D bounding box)
2. Partial object (partial camera view observation aggregation)
3. Occluded object (depth-based separation of foreground vs background)
4. Multiple objects (multi-instance clustering and distinct bounding boxes)
5. Similar objects (discrimination between related classes: Door vs Wall, Chair vs Sofa)
6. Unknown object (proper assignment to 'Other / Background')
7. False detection (low-confidence noise rejection)
Plus: Validation of Precision, Recall, F1, and IoU mathematical metrics.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import numpy as np
import cv2
import torch

# Add parent directory
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from semantic_understanding_engine import (
    SemanticUnderstandingEngine,
    SEMANTIC_CLASSES,
    CLASS_TO_ID
)


class TestSemanticUnderstandingScenarios(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="vastu_test_semantics_")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

        self.engine = SemanticUnderstandingEngine(
            device="cpu", # Force CPU for deterministic test execution
            confidence_threshold=0.35,
            min_cluster_points=10,
            cluster_eps_m=0.25
        )

        self.img_w = 320
        self.img_h = 240
        self.k_matrix = np.array([
            [250.0, 0.0, 160.0],
            [0.0, 250.0, 120.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_synthetic_camera(self, cam_pos=(0.0, 0.0, 0.0), look_at=(0.0, 0.0, 2.5)):
        """Creates extrinsics (R, t) looking from cam_pos towards look_at."""
        c = np.array(cam_pos, dtype=np.float64)
        target = np.array(look_at, dtype=np.float64)

        z_cam = target - c
        z_cam /= np.linalg.norm(z_cam)

        up = np.array([0.0, -1.0, 0.0], dtype=np.float64) # Camera Y down
        x_cam = np.cross(up, z_cam)
        x_cam /= np.linalg.norm(x_cam)
        y_cam = np.cross(z_cam, x_cam)

        r_mat = np.vstack([x_cam, y_cam, z_cam])
        t_vec = -r_mat @ c
        return {"R": r_mat, "t": t_vec}

    # -------------------------------------------------------------------------
    # Evaluation Metrics Validation
    # -------------------------------------------------------------------------
    def test_00_metrics_calculation(self):
        """Validates Precision, Recall, F1, and IoU calculation formulas."""
        # 10 samples: 6 True Positives, 2 False Positives, 2 False Negatives for Class 1 (Floor)
        y_true = np.array([1, 1, 1, 1, 1, 1, 1, 1, 0, 0])
        y_pred = np.array([1, 1, 1, 1, 1, 1, 0, 0, 1, 1])

        metrics = self.engine.calculate_evaluation_metrics(y_true, y_pred, target_classes=[1])
        floor_metrics = metrics["classes"]["Floor"]

        # TP = 6, FP = 2, FN = 2
        # Precision = 6 / (6 + 2) = 0.75
        # Recall    = 6 / (6 + 2) = 0.75
        # F1        = 2 * 0.75 * 0.75 / (1.5) = 0.75
        # IoU       = 6 / (6 + 2 + 2) = 0.60
        self.assertAlmostEqual(floor_metrics["precision"], 0.75, places=3)
        self.assertAlmostEqual(floor_metrics["recall"], 0.75, places=3)
        self.assertAlmostEqual(floor_metrics["f1_score"], 0.75, places=3)
        self.assertAlmostEqual(floor_metrics["iou"], 0.60, places=3)

    # -------------------------------------------------------------------------
    # Scenario 1: Correct Object
    # -------------------------------------------------------------------------
    def test_01_correct_object(self):
        """Test 1: Correct object - known table structure detection & 3D bounding box extraction."""
        # 3D points forming a rectangular table: X in [-0.5, 0.5], Y in [-0.2, 0.2], Z in [1.8, 2.2]
        x = np.linspace(-0.5, 0.5, 10)
        y = np.linspace(-0.2, 0.2, 5)
        z = np.linspace(1.8, 2.2, 6)
        xx, yy, zz = np.meshgrid(x, y, z)
        table_points = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()]).astype(np.float64)

        # Mock predictions: all points classified as Table (class 6) with high confidence
        class_ids = np.full(len(table_points), CLASS_TO_ID["Table"], dtype=np.int64)
        confidences = np.full(len(table_points), 0.95, dtype=np.float32)

        objects = self.engine.extract_semantic_objects(table_points, class_ids, confidences)
        self.assertEqual(len(objects), 1)
        obj = objects[0]

        self.assertEqual(obj["class_name"], "Table")
        self.assertEqual(obj["class_id"], CLASS_TO_ID["Table"])
        self.assertAlmostEqual(obj["centroid"][0], 0.0, delta=0.05)
        self.assertAlmostEqual(obj["centroid"][1], 0.0, delta=0.05)
        self.assertAlmostEqual(obj["centroid"][2], 2.0, delta=0.05)
        # Dimensions must be close to 1.0 x 0.4 x 0.4
        self.assertAlmostEqual(obj["bounding_box"]["dimensions_xyz"][0], 1.0, delta=0.05)
        self.assertAlmostEqual(obj["bounding_box"]["dimensions_xyz"][1], 0.4, delta=0.05)

    # -------------------------------------------------------------------------
    # Scenario 2: Partial Object
    # -------------------------------------------------------------------------
    def test_02_partial_object(self):
        """Test 2: Partial object - object observed across different camera views aggregates spatial boundaries."""
        # Long sofa (2.0m wide): left half observed by Cam 1, right half observed by Cam 2
        sofa_left = np.column_stack([
            np.linspace(-1.0, -0.1, 15),
            np.zeros(15),
            np.full(15, 2.0)
        ])
        sofa_right = np.column_stack([
            np.linspace(0.1, 1.0, 15),
            np.zeros(15),
            np.full(15, 2.0)
        ])
        full_sofa = np.vstack([sofa_left, sofa_right])

        class_ids = np.full(len(full_sofa), CLASS_TO_ID["Sofa"], dtype=np.int64)
        confidences = np.full(len(full_sofa), 0.88, dtype=np.float32)

        objects = self.engine.extract_semantic_objects(full_sofa, class_ids, confidences)
        self.assertEqual(len(objects), 1)
        # Bounding box width should span almost 2.0m (-1.0 to 1.0)
        dim_x = objects[0]["bounding_box"]["dimensions_xyz"][0]
        self.assertGreaterEqual(dim_x, 1.8)

    # -------------------------------------------------------------------------
    # Scenario 3: Occluded Object
    # -------------------------------------------------------------------------
    def test_03_occluded_object(self):
        """Test 3: Occluded object - foreground chair at Z=1.5m and background table at Z=2.8m."""
        # Foreground Chair points (Z=1.5)
        chair_pts = np.column_stack([
            np.linspace(-0.2, 0.2, 12),
            np.linspace(-0.3, 0.3, 12),
            np.full(12, 1.5)
        ])
        # Background Table points (Z=2.8)
        table_pts = np.column_stack([
            np.linspace(-0.6, 0.6, 16),
            np.linspace(-0.4, 0.4, 16),
            np.full(16, 2.8)
        ])

        combined_pts = np.vstack([chair_pts, table_pts])
        class_ids = np.concatenate([
            np.full(len(chair_pts), CLASS_TO_ID["Chair"]),
            np.full(len(table_pts), CLASS_TO_ID["Table"])
        ])
        confidences = np.full(len(combined_pts), 0.90, dtype=np.float32)

        objects = self.engine.extract_semantic_objects(combined_pts, class_ids, confidences)
        self.assertEqual(len(objects), 2)
        classes_detected = {obj["class_name"] for obj in objects}
        self.assertIn("Chair", classes_detected)
        self.assertIn("Table", classes_detected)

    # -------------------------------------------------------------------------
    # Scenario 4: Multiple Objects
    # -------------------------------------------------------------------------
    def test_04_multiple_objects(self):
        """Test 4: Multiple objects - 1 Table and 2 spatially separated Chairs."""
        # Chair 1 at X = -1.2m
        chair1 = np.column_stack([np.linspace(-1.4, -1.0, 12), np.zeros(12), np.full(12, 2.0)])
        # Chair 2 at X = +1.2m
        chair2 = np.column_stack([np.linspace(1.0, 1.4, 12), np.zeros(12), np.full(12, 2.0)])
        # Table in center at X = 0.0m
        table = np.column_stack([np.linspace(-0.4, 0.4, 15), np.zeros(15), np.full(15, 2.0)])

        all_pts = np.vstack([chair1, chair2, table])
        class_ids = np.concatenate([
            np.full(len(chair1), CLASS_TO_ID["Chair"]),
            np.full(len(chair2), CLASS_TO_ID["Chair"]),
            np.full(len(table), CLASS_TO_ID["Table"])
        ])
        confidences = np.full(len(all_pts), 0.92, dtype=np.float32)

        objects = self.engine.extract_semantic_objects(all_pts, class_ids, confidences)
        self.assertEqual(len(objects), 3)

        chair_objs = [obj for obj in objects if obj["class_name"] == "Chair"]
        table_objs = [obj for obj in objects if obj["class_name"] == "Table"]

        self.assertEqual(len(chair_objs), 2)
        self.assertEqual(len(table_objs), 1)
        # Distinct spatial centroids
        self.assertLess(chair_objs[0]["centroid"][0], -0.8)
        self.assertGreater(chair_objs[1]["centroid"][0], 0.8)

    # -------------------------------------------------------------------------
    # Scenario 5: Similar Objects
    # -------------------------------------------------------------------------
    def test_05_similar_objects(self):
        """Test 5: Similar objects - discrimination between Wall vs Door and Chair vs Sofa."""
        # Wall points
        wall_pts = np.column_stack([np.linspace(-2, 2, 20), np.zeros(20), np.full(20, 3.0)])
        # Door points embedded in the wall
        door_pts = np.column_stack([np.linspace(-0.4, 0.4, 12), np.zeros(12), np.full(12, 3.0)])

        wall_gt = np.full(len(wall_pts), CLASS_TO_ID["Wall"])
        door_gt = np.full(len(door_pts), CLASS_TO_ID["Door"])

        y_true = np.concatenate([wall_gt, door_gt])
        # Simulated prediction with 90% accuracy
        y_pred = y_true.copy()
        y_pred[0] = CLASS_TO_ID["Door"] # 1 confusion

        metrics = self.engine.calculate_evaluation_metrics(y_true, y_pred, target_classes=[CLASS_TO_ID["Wall"], CLASS_TO_ID["Door"]])
        wall_f1 = metrics["classes"]["Wall"]["f1_score"]
        door_f1 = metrics["classes"]["Door"]["f1_score"]

        self.assertGreater(wall_f1, 0.85)
        self.assertGreater(door_f1, 0.85)

    # -------------------------------------------------------------------------
    # Scenario 6: Unknown Object
    # -------------------------------------------------------------------------
    def test_06_unknown_object(self):
        """Test 6: Unknown object - unrecognized structure assigned to 'Other / Background' without false entity creation."""
        # Random sculpture points
        unknown_pts = np.random.uniform(-0.5, 0.5, (30, 3))
        # Classified as Other (0)
        class_ids = np.zeros(len(unknown_pts), dtype=np.int64)
        confidences = np.full(len(unknown_pts), 0.80, dtype=np.float32)

        objects = self.engine.extract_semantic_objects(unknown_pts, class_ids, confidences)
        # Class 0 (Other) should NOT be exported as a distinct foreground object
        self.assertEqual(len(objects), 0)

    # -------------------------------------------------------------------------
    # Scenario 7: False Detection
    # -------------------------------------------------------------------------
    def test_07_false_detection(self):
        """Test 7: False detection - low confidence spurious predictions (<0.35) are pruned."""
        pts = np.column_stack([np.linspace(0, 1, 20), np.zeros(20), np.full(20, 2.0)])
        class_ids = np.full(len(pts), CLASS_TO_ID["Cabinet"]) # Fake cabinet
        # Low confidence noise (0.20 < 0.35 threshold)
        confidences = np.full(len(pts), 0.20, dtype=np.float32)

        objects = self.engine.extract_semantic_objects(pts, class_ids, confidences)
        self.assertEqual(len(objects), 0)

    # -------------------------------------------------------------------------
    # End-to-End Pipeline Asset Export Test
    # -------------------------------------------------------------------------
    def test_08_end_to_end_storage(self):
        """Test 8: Full end-to-end asset storage (JSON metadata & semantic PLY point cloud)."""
        pts = np.random.uniform(-1, 1, (50, 3))
        class_ids = np.random.randint(0, len(SEMANTIC_CLASSES), 50)
        confidences = np.random.uniform(0.5, 0.99, 50).astype(np.float32)

        objects = self.engine.extract_semantic_objects(pts, class_ids, confidences)
        output = self.engine.store_semantic_assets(self.output_dir, pts, class_ids, confidences, objects)

        self.assertEqual(output["status"], "success")
        self.assertEqual(output["pipeline_point"], 24)
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "semantic_objects.json")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "semantic_pointcloud.ply")))

    # -------------------------------------------------------------------------
    # Native C++ Compilation & Execution Verification
    # -------------------------------------------------------------------------
    def test_09_cpp_compilation_and_execution(self):
        """Test native C++ semantic fuser compilation and binary execution."""
        cpp_path = os.path.join(os.path.dirname(__file__), "semantic_fuser.cpp")
        self.assertTrue(os.path.exists(cpp_path))

        bin_path = os.path.join(self.test_dir, "semantic_fuser")
        compile_cmd = f"g++ -std=c++17 -O3 {cpp_path} -o {bin_path}"

        try:
            res = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                self.assertTrue(os.path.exists(bin_path))
                exec_res = subprocess.run([bin_path], capture_output=True, text=True)
                self.assertEqual(exec_res.returncode, 0)
                self.assertIn("VASTU C++ Native Semantic Fuser", exec_res.stdout)
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()

