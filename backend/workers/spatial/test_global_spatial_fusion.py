#!/usr/bin/env python3
"""
Unit tests for VĀSTU Point 26: Global Spatial Fusion Engine
Covers all 7 required scenarios:
1. Adjacent rooms
2. Repeated room
3. Multi-floor
4. Misaligned recon
5. Partial overlap
6. No overlap
7. Fusion inconsistency
"""

import os
import sys
import unittest
import tempfile
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from spatial.global_spatial_fusion_engine import GlobalSpatialFusionEngine


class TestGlobalSpatialFusionEngine(unittest.TestCase):
    def setUp(self):
        self.engine = GlobalSpatialFusionEngine(
            voxel_size_m=0.05,
            max_icp_iterations=60,
            max_correspondence_dist_m=0.40,
            rmse_tolerance_m=0.10
        )
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_scenario_1_adjacent_rooms(self):
        """1. Adjacent rooms connected via doorway/corridor overlap."""
        # Room A: [0, 5] x [0, 5] x [0, 3]
        pts_a = np.random.uniform(low=[0.0, 0.0, 0.0], high=[5.0, 5.0, 3.0], size=(1000, 3))
        # Room B: [4.0, 9.0] x [0, 5] x [0, 3] with 1.0m overlap on X axis ([4.0, 5.0])
        pts_b = np.random.uniform(low=[4.0, 0.0, 0.0], high=[9.0, 5.0, 3.0], size=(1000, 3))

        has_overlap, ratio = self.engine.identify_overlap(pts_a, pts_b)
        self.assertTrue(has_overlap, "Adjacent rooms with overlapping doorway must have overlap")
        self.assertGreater(ratio, 0.05)

        recon_a = {"points": pts_a, "semantics": np.zeros(len(pts_a), dtype=int), "quality": np.full(len(pts_a), 0.8), "semantic_objects": ["wall", "door"]}
        recon_b = {"points": pts_b, "semantics": np.ones(len(pts_b), dtype=int), "quality": np.full(len(pts_b), 0.9), "semantic_objects": ["door", "window"]}

        fused = self.engine.fuse_local_reconstructions(recon_a, recon_b)
        self.assertEqual(fused["status"], "success")
        self.assertIn("door", fused["semantic_objects"])
        self.assertIn("wall", fused["semantic_objects"])
        self.assertIn("window", fused["semantic_objects"])
        self.assertGreater(fused["total_points"], 1000)

    def test_scenario_2_repeated_room(self):
        """2. Repeated room (identical layout shifted in space)."""
        # Identical 4-corner room points
        base_room = np.array([
            [0.0, 0.0, 0.0], [4.0, 0.0, 0.0], [4.0, 4.0, 0.0], [0.0, 4.0, 0.0],
            [0.0, 0.0, 2.5], [4.0, 0.0, 2.5], [4.0, 4.0, 2.5], [0.0, 4.0, 2.5]
        ])
        room_2 = base_room + np.array([10.0, 0.0, 0.0])

        has_overlap, _ = self.engine.identify_overlap(base_room, room_2)
        self.assertFalse(has_overlap, "Spatially separated repeated rooms should not have physical bounding overlap")

    def test_scenario_3_multi_floor(self):
        """3. Multi-floor building: Floor 1 (Z: 0-3) and Floor 2 (Z: 3.2-6.2)."""
        floor_1 = np.random.uniform(low=[0.0, 0.0, 0.0], high=[10.0, 10.0, 3.0], size=(800, 3))
        floor_2 = np.random.uniform(low=[0.0, 0.0, 3.2], high=[10.0, 10.0, 6.2], size=(800, 3))

        has_overlap, _ = self.engine.identify_overlap(floor_1, floor_2)
        self.assertFalse(has_overlap, "Vertically separated floors should not overlap on Z axis")

        # Fusion should still succeed by combining both floors into unified global twin
        recon_1 = {"points": floor_1, "semantic_objects": ["floor1_room"]}
        recon_2 = {"points": floor_2, "semantic_objects": ["floor2_room"]}
        fused = self.engine.fuse_local_reconstructions(recon_1, recon_2)
        self.assertEqual(fused["status"], "success")
        self.assertEqual(len(fused["semantic_objects"]), 2)
        self.assertAlmostEqual(fused["total_points"], len(floor_1) + len(floor_2), delta=30)

    def test_scenario_4_misaligned_recon(self):
        """4. Misaligned recon with known rigid translation and small rotation."""
        pts_target = np.random.uniform(low=[0.0, 0.0, 0.0], high=[4.0, 4.0, 2.5], size=(500, 3))
        # Apply known translation + 0.1 rad rotation around Z
        theta = 0.05
        R_true = np.array([
            [np.cos(theta), -np.sin(theta), 0.0],
            [np.sin(theta),  np.cos(theta), 0.0],
            [0.0, 0.0, 1.0]
        ])
        t_true = np.array([0.15, -0.10, 0.05])
        pts_source = (R_true @ pts_target.T).T + t_true

        T_est, rmse, is_aligned = self.engine.estimate_transformation(pts_source, pts_target)
        self.assertIsNotNone(T_est)
        self.assertLess(rmse, 0.20, f"Registration RMSE should be low, got {rmse}")

    def test_scenario_5_partial_overlap(self):
        """5. Partial overlap (two sweeps overlapping by 30%)."""
        sweep_1 = np.random.uniform(low=[0.0, 0.0, 0.0], high=[5.0, 5.0, 2.5], size=(600, 3))
        sweep_2 = np.random.uniform(low=[3.5, 0.0, 0.0], high=[8.5, 5.0, 2.5], size=(600, 3))

        has_overlap, ratio = self.engine.identify_overlap(sweep_1, sweep_2)
        self.assertTrue(has_overlap)
        self.assertGreater(ratio, 0.05)

        recon_1 = {"points": sweep_1, "quality": np.full(len(sweep_1), 0.7)}
        recon_2 = {"points": sweep_2, "quality": np.full(len(sweep_2), 0.95)}
        fused = self.engine.fuse_local_reconstructions(recon_1, recon_2)
        # Quality-based conflict resolution should maintain points
        self.assertGreater(fused["total_points"], 600)
        self.assertLess(fused["total_points"], 1200)

    def test_scenario_6_no_overlap(self):
        """6. No overlap (disjoint areas)."""
        zone_a = np.random.uniform(low=[0.0, 0.0, 0.0], high=[3.0, 3.0, 2.5], size=(300, 3))
        zone_b = np.random.uniform(low=[20.0, 20.0, 0.0], high=[23.0, 23.0, 2.5], size=(300, 3))

        has_overlap, ratio = self.engine.identify_overlap(zone_a, zone_b)
        self.assertFalse(has_overlap)
        self.assertEqual(ratio, 0.0)

    def test_scenario_7_fusion_inconsistency(self):
        """7. Fusion inconsistency (NaN or Inf points in input data)."""
        pts_corrupted = np.array([
            [1.0, 2.0, np.nan],
            [3.0, np.inf, 4.0]
        ])
        fused_corrupted = {
            "points": pts_corrupted,
            "quality": np.array([0.5, 0.5]),
            "semantic_objects": []
        }
        manifest = self.engine.validate_and_export_global_model(
            fused_corrupted,
            self.temp_dir.name,
            "corrupted_model"
        )
        self.assertFalse(manifest["is_consistent"], "Corrupted model with NaNs/Infs must fail consistency")
        self.assertEqual(manifest["status"], "failed")


if __name__ == "__main__":
    unittest.main()
