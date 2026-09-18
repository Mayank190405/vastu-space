#!/usr/bin/env python3
"""
Unit tests for VĀSTU Point 28: Targeted Rescan Manager
Covers all 8 required scenarios:
1. Single failed cell
2. Multiple failed cells
3. Room boundary rescan
4. Rescan with different lighting
5. Rescan with slight camera offset
6. Rescan succeeds
7. Rescan fails (base scan preserved)
8. Partial rescan
"""

import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from rescan.targeted_rescan_manager import TargetedRescanManager


class TestTargetedRescanManager(unittest.TestCase):
    def setUp(self):
        self.manager = TargetedRescanManager(cell_size_m=1.0)
        # Setup base model cells
        self.base_cells = {
            "cell_0_0_0": {"cell_id": "cell_0_0_0", "points": np.random.uniform(0, 1, (100, 3)), "quality_score": 0.85, "version": 1},
            "cell_0_1_0": {"cell_id": "cell_0_1_0", "points": np.random.uniform([0, 1, 0], [1, 2, 1], (15, 3)), "quality_score": 0.30, "version": 1}, # failed cell
            "cell_1_1_0": {"cell_id": "cell_1_1_0", "points": np.random.uniform([1, 1, 0], [2, 2, 1], (10, 3)), "quality_score": 0.25, "version": 1}  # failed cell
        }

    def test_scenario_1_single_failed_cell(self):
        """1. Single failed cell generates accurate bounding box & waypoints."""
        instr = self.manager.generate_rescan_instructions(["cell_0_1_0"])
        self.assertEqual(instr["status"], "rescan_required")
        self.assertEqual(len(instr["recommended_waypoints"]), 4)
        bbox = instr["target_bounding_box"]
        self.assertEqual(bbox["min"], [0.0, 1.0, 0.0])
        self.assertEqual(bbox["max"], [1.0, 2.0, 1.0])
        self.assertEqual(bbox["center"], [0.5, 1.5, 0.5])

    def test_scenario_2_multiple_failed_cells(self):
        """2. Multiple failed cells correctly merge spatial bounding box."""
        instr = self.manager.generate_rescan_instructions(["cell_0_1_0", "cell_1_1_0"])
        bbox = instr["target_bounding_box"]
        self.assertEqual(bbox["min"], [0.0, 1.0, 0.0])
        self.assertEqual(bbox["max"], [2.0, 2.0, 1.0])
        self.assertEqual(bbox["center"], [1.0, 1.5, 0.5])

    def test_scenario_3_room_boundary_rescan(self):
        """3. Room boundary rescan on outer wall cell."""
        instr = self.manager.generate_rescan_instructions(["cell_5_0_2"], reason="Outer wall boundary missing")
        self.assertIn("Outer wall boundary missing", instr["guidance_message"])
        self.assertEqual(instr["target_bounding_box"]["min"], [5.0, 0.0, 2.0])

    def test_scenario_4_rescan_with_different_lighting(self):
        """4. Rescan with lighting defect includes specialized lighting instruction."""
        instr = self.manager.generate_rescan_instructions(["cell_0_0_0"], reason="Underexposed dark texture", lighting_defect=True)
        self.assertIn("bright, even illumination", instr["lighting_instructions"])

    def test_scenario_5_rescan_with_slight_camera_offset(self):
        """5. Rescan with slight camera offset registers patch accurately."""
        # Simulated patch points covering cell_0_1_0 with offset
        patch_pts = np.random.uniform([0.05, 1.05, 0.05], [0.95, 1.95, 0.95], (120, 3))
        patch_data = {
            "points": patch_pts,
            "patch_quality_score": 0.88
        }
        res = self.manager.apply_rescan_patch(self.base_cells, patch_data, ["cell_0_1_0"])
        self.assertTrue(res["success"])
        self.assertIn("cell_0_1_0", res["applied_cell_ids"])
        self.assertEqual(res["updated_cells"]["cell_0_1_0"]["version"], 2)

    def test_scenario_6_rescan_succeeds(self):
        """6. Rescan succeeds: cell quality score improves and passes quality gate."""
        patch_pts = np.random.uniform([0.0, 1.0, 0.0], [1.0, 2.0, 1.0], (200, 3))
        patch_data = {
            "points": patch_pts,
            "patch_quality_score": 0.94
        }
        res = self.manager.apply_rescan_patch(self.base_cells, patch_data, ["cell_0_1_0"])
        self.assertTrue(res["success"])
        self.assertGreater(res["updated_cells"]["cell_0_1_0"]["quality_score"], 0.70)
        self.assertTrue(res["re_evaluated_quality"]["passed_gate"])

    def test_scenario_7_rescan_fails_preserves_base_scan(self):
        """7. Rescan fails: bad patch data rejected, base scan preserved untouched."""
        bad_patch = {
            "points": np.random.uniform([0, 0, 0], [1, 1, 1], (5, 3)), # insufficient points
            "patch_quality_score": 0.20
        }
        res = self.manager.apply_rescan_patch(self.base_cells, bad_patch, ["cell_0_1_0"])
        self.assertFalse(res["success"])
        # Base cells should remain untouched
        self.assertEqual(self.base_cells["cell_0_1_0"]["version"], 1)
        self.assertEqual(len(self.base_cells["cell_0_1_0"]["points"]), 15)

    def test_scenario_8_partial_rescan(self):
        """8. Partial rescan: user scanned 1 of 2 failed cells -> updates provided cell only."""
        patch_pts = np.random.uniform([0.0, 1.0, 0.0], [1.0, 2.0, 1.0], (100, 3)) # only covers cell_0_1_0
        patch_data = {
            "points": patch_pts,
            "patch_quality_score": 0.90
        }
        # Targeted both cells, but patch only has points for cell_0_1_0
        res = self.manager.apply_rescan_patch(self.base_cells, patch_data, ["cell_0_1_0", "cell_1_1_0"])
        self.assertTrue(res["success"])
        self.assertEqual(res["applied_cell_ids"], ["cell_0_1_0"])
        self.assertEqual(res["updated_cells"]["cell_0_1_0"]["version"], 2)
        # cell_1_1_0 was not present in patch, so remains version 1
        self.assertEqual(res["updated_cells"]["cell_1_1_0"]["version"], 1)


if __name__ == "__main__":
    unittest.main()
