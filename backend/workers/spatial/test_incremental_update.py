#!/usr/bin/env python3
"""
Unit tests for VĀSTU Point 29: Incremental Model Update Engine
Covers all 7 required scenarios:
1. Single cell update
2. Multi-cell update
3. Boundary cell update
4. Add new cell (volume expansion)
5. Delete cell
6. Quality passes -> V2 promoted
7. Quality fails -> V2 rejected, V1 remains valid and active
"""

import os
import sys
import unittest
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from spatial.incremental_update_engine import IncrementalUpdateEngine


class TestIncrementalUpdateEngine(unittest.TestCase):
    def setUp(self):
        self.engine = IncrementalUpdateEngine(cell_size_m=1.0)
        self.base_v1 = {
            "model_id": "building_alpha_v1",
            "version": 1,
            "is_active": True,
            "cells": {
                "cell_0_0_0": {"cell_id": "cell_0_0_0", "points": np.random.uniform(0, 1, (100, 3)), "quality_score": 0.85, "version": 1},
                "cell_1_0_0": {"cell_id": "cell_1_0_0", "points": np.random.uniform([1, 0, 0], [2, 1, 1], (100, 3)), "quality_score": 0.88, "version": 1},
                "cell_0_1_0": {"cell_id": "cell_0_1_0", "points": np.random.uniform([0, 1, 0], [1, 2, 1], (100, 3)), "quality_score": 0.90, "version": 1}
            }
        }

    def test_scenario_1_single_cell_update(self):
        """1. Single cell update only modifies target cell and increments its version."""
        update = {
            "cell_0_0_0": {"points": np.random.uniform(0, 1, (150, 3)), "quality_score": 0.95}
        }
        res = self.engine.apply_incremental_update(self.base_v1, update)
        self.assertEqual(res["status"], "PROMOTED_V2")
        self.assertEqual(res["active_version"], 2)
        v2_cells = res["active_model"]["cells"]
        self.assertEqual(v2_cells["cell_0_0_0"]["version"], 2)
        self.assertEqual(v2_cells["cell_1_0_0"]["version"], 1) # untouched cell remains v1

    def test_scenario_2_multi_cell_update(self):
        """2. Multi-cell update updates multiple specified cells."""
        update = {
            "cell_0_0_0": {"points": np.random.uniform(0, 1, (120, 3)), "quality_score": 0.92},
            "cell_1_0_0": {"points": np.random.uniform([1, 0, 0], [2, 1, 1], (130, 3)), "quality_score": 0.91}
        }
        res = self.engine.apply_incremental_update(self.base_v1, update)
        self.assertEqual(res["status"], "PROMOTED_V2")
        self.assertEqual(res["active_model"]["updated_cells_count"], 2)

    def test_scenario_3_boundary_cell_update(self):
        """3. Boundary cell update correctly identifies affected 26-connectivity subgraph."""
        all_cells = list(self.base_v1["cells"].keys())
        affected = self.engine.identify_affected_subgraph(["cell_0_0_0"], all_cells)
        # 0_0_0 is adjacent to 1_0_0 and 0_1_0
        self.assertIn("cell_0_0_0", affected)
        self.assertIn("cell_1_0_0", affected)
        self.assertIn("cell_0_1_0", affected)

    def test_scenario_4_add_new_cell(self):
        """4. Add new cell expands spatial model volume."""
        update = {
            "cell_2_0_0": {"points": np.random.uniform([2, 0, 0], [3, 1, 1], (80, 3)), "quality_score": 0.89}
        }
        res = self.engine.apply_incremental_update(self.base_v1, update)
        self.assertEqual(res["status"], "PROMOTED_V2")
        v2_cells = res["active_model"]["cells"]
        self.assertEqual(len(v2_cells), 4)
        self.assertIn("cell_2_0_0", v2_cells)

    def test_scenario_5_delete_cell(self):
        """5. Delete cell removes obsolete or pruned spatial region."""
        res = self.engine.apply_incremental_update(self.base_v1, {}, deleted_cell_ids=["cell_0_1_0"])
        self.assertEqual(res["status"], "PROMOTED_V2")
        v2_cells = res["active_model"]["cells"]
        self.assertEqual(len(v2_cells), 2)
        self.assertNotIn("cell_0_1_0", v2_cells)

    def test_scenario_6_quality_passes_v2_promoted(self):
        """6. Quality passes: V2 promoted to active, V1 deactivated."""
        update = {
            "cell_0_0_0": {"points": np.random.uniform(0, 1, (100, 3)), "quality_score": 0.95}
        }
        res = self.engine.apply_incremental_update(self.base_v1, update)
        self.assertEqual(res["status"], "PROMOTED_V2")
        self.assertTrue(res["active_model"]["is_active"])
        self.assertFalse(self.base_v1["is_active"])

    def test_scenario_7_quality_fails_v1_remains_active(self):
        """7. CRITICAL: If candidate update fails quality checks, V1 remains active and untouched."""
        update = {
            "cell_0_0_0": {"points": np.random.uniform(0, 1, (10, 3)), "quality_score": 0.30}
        }
        res = self.engine.apply_incremental_update(self.base_v1, update, force_fail_quality=True)
        self.assertEqual(res["status"], "REJECTED_V1_RETAINED")
        self.assertEqual(res["active_version"], 1)
        self.assertTrue(res["active_model"]["is_active"])
        self.assertTrue(self.base_v1["is_active"], "Base V1 must remain the active production model")
        self.assertEqual(self.base_v1["cells"]["cell_0_0_0"]["version"], 1)


if __name__ == "__main__":
    unittest.main()
