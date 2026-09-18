#!/usr/bin/env python3
"""
Unit tests for VĀSTU Point 27: Quality Engine
Tests the 6 key quality scenarios:
1. Good recon -> PASS
2. Poor tracking -> FAIL
3. Missing wall (geometry hole) -> FAIL
4. Poor coverage -> FAIL
5. Bad texture -> WARNING / FAIL
6. Navigation disconnected -> FAIL
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from quality.quality_engine import QualityEngine


class TestQualityEngine(unittest.TestCase):
    def setUp(self):
        self.engine = QualityEngine()
        # Baseline good reconstruction model data
        self.good_model = {
            "geometry": {
                "vertices": [[0, 0, 0]] * 100,
                "faces": [[0, 1, 2]] * 100,
                "hole_ratio": 0.02,
                "has_inverted_normals": False
            },
            "tracking": {
                "lost_track_frames": 0,
                "total_frames": 200,
                "drift_rate_m_per_m": 0.005
            },
            "cells": [
                {"cell_id": "cell_0_0_0", "quality_score": 0.95, "point_count": 150},
                {"cell_id": "cell_0_1_0", "quality_score": 0.92, "point_count": 140},
                {"cell_id": "cell_1_0_0", "quality_score": 0.88, "point_count": 120}
            ],
            "expected_cells_count": 3,
            "texture": {
                "laplacian_variance": 145.0,
                "has_seam_artifacts": False
            },
            "semantics": [
                {"class_name": "floor", "bbox": {"min_z": 0.0, "max_z": 0.1}},
                {"class_name": "ceiling", "bbox": {"min_z": 2.8, "max_z": 3.0}},
                {"class_name": "chair", "object_id": "chair_1", "bbox": {"min_z": 0.1, "max_z": 0.9}}
            ],
            "cell_boundaries": [
                {"step_error_m": 0.01}
            ],
            "nav_nodes": [{"id": "n1"}, {"id": "n2"}, {"id": "n3"}],
            "nav_edges": [("n1", "n2"), ("n2", "n3")]
        }

    def test_scenario_1_good_recon_passes(self):
        """1. Good recon should pass all gates with PASS status."""
        report = self.engine.evaluate(self.good_model)
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["passed_gate"])
        self.assertGreaterEqual(report["overall_score"], 0.85)
        self.assertEqual(len(report["failed_cell_ids"]), 0)

    def test_scenario_2_poor_tracking_fails(self):
        """2. Poor tracking (excessive lost frames and drift) must FAIL."""
        bad_model = dict(self.good_model)
        bad_model["tracking"] = {
            "lost_track_frames": 45,
            "total_frames": 100,
            "drift_rate_m_per_m": 0.08
        }
        report = self.engine.evaluate(bad_model)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["passed_gate"])
        self.assertLess(report["scores"]["tracking"], 0.60)
        self.assertTrue(any("drift" in issue.lower() or "lost track" in issue.lower() for issue in report["issues"]))

    def test_scenario_3_missing_wall_fails(self):
        """3. Missing wall / large geometric holes must FAIL geometry gate."""
        bad_model = dict(self.good_model)
        bad_model["geometry"] = {
            "vertices": [[0, 0, 0]] * 100,
            "faces": [[0, 1, 2]] * 100,
            "hole_ratio": 0.35, # 35% missing surface / holes
            "has_inverted_normals": True
        }
        report = self.engine.evaluate(bad_model)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["passed_gate"])
        self.assertLess(report["scores"]["geometry"], 0.60)
        self.assertTrue(any("hole" in issue.lower() for issue in report["issues"]))

    def test_scenario_4_poor_coverage_fails(self):
        """4. Poor coverage (scanned only 2 cells out of 10 expected) must FAIL."""
        bad_model = dict(self.good_model)
        bad_model["cells"] = [
            {"cell_id": "cell_0_0_0", "quality_score": 0.90, "point_count": 100},
            {"cell_id": "cell_0_1_0", "quality_score": 0.30, "point_count": 10} # degraded cell
        ]
        bad_model["expected_cells_count"] = 10 # 20% coverage
        report = self.engine.evaluate(bad_model)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["passed_gate"])
        self.assertLess(report["scores"]["coverage"], 0.65)
        self.assertIn("cell_0_1_0", report["failed_cell_ids"])

    def test_scenario_5_bad_texture_warning_or_fail(self):
        """5. Bad blurry texture triggers WARNING or FAIL with recommendation."""
        bad_model = dict(self.good_model)
        bad_model["texture"] = {
            "laplacian_variance": 32.0, # severely blurry
            "has_seam_artifacts": True
        }
        report = self.engine.evaluate(bad_model)
        self.assertIn(report["status"], ["WARNING", "FAIL"])
        self.assertLess(report["scores"]["texture"], 0.55)
        self.assertTrue(any("blurry" in issue.lower() or "seam" in issue.lower() for issue in report["issues"]))

    def test_scenario_6_nav_disconnected_fails(self):
        """6. Disconnected navigation nodes must FAIL navigation gate."""
        bad_model = dict(self.good_model)
        bad_model["nav_nodes"] = [{"id": "n1"}, {"id": "n2"}, {"id": "island_n3"}]
        bad_model["nav_edges"] = [("n1", "n2")] # island_n3 is completely disconnected
        report = self.engine.evaluate(bad_model)
        self.assertEqual(report["status"], "FAIL")
        self.assertFalse(report["passed_gate"])
        self.assertEqual(report["scores"]["navigation"], 0.0)
        self.assertTrue(any("disconnected" in issue.lower() for issue in report["issues"]))


if __name__ == "__main__":
    unittest.main()
