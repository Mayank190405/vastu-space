#!/usr/bin/env python3
"""
Comprehensive Unit & Integration Test Suite for Point 25: Spatial Cell System.
Validates all 7 roadmap scenarios:
1. Small room (compact 3x3x2.5m space partitioning)
2. Large room (open 12x8x3.5m spatial division)
3. Large building (multi-room multi-floor structure)
4. Complex furniture (sub-cellular high density object assignment)
5. Different cell sizes (0.5m, 1.0m, 2.0m adaptive grid scaling)
6. Boundary conditions (points landing exactly on cell edges and origin (0,0,0))
7. Neighbor queries (26-connectivity topological adjacency)
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import numpy as np

# Add parent directory
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from spatial_cell_engine import SpatialCellEngine


class TestSpatialCellSystemScenarios(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="vastu_test_cells_")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    # -------------------------------------------------------------------------
    # Scenario 1: Small Room
    # -------------------------------------------------------------------------
    def test_01_small_room(self):
        """Test 1: Small room (3m x 3m x 2.5m) partitioned with 1.0m cells."""
        engine = SpatialCellEngine(cell_size_m=1.0)

        # Points across room bounds: X in [0, 3], Y in [0, 2.5], Z in [0, 3]
        xs = np.linspace(0.1, 2.9, 10)
        ys = np.linspace(0.1, 2.4, 8)
        zs = np.linspace(0.1, 2.9, 10)
        xx, yy, zz = np.meshgrid(xs, ys, zs)
        room_pts = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])

        engine.assign_geometry(room_pts)
        engine.assign_quality()
        engine.compute_neighbors(connectivity=26)

        # 3 x 3 x 3 = 27 cells expected
        self.assertEqual(len(engine.cells), 27)
        # Verify all cells have valid points and quality
        for cell in engine.cells.values():
            self.assertGreater(len(cell.point_indices), 0)
            self.assertFalse(cell.is_low_confidence)

    # -------------------------------------------------------------------------
    # Scenario 2: Large Room
    # -------------------------------------------------------------------------
    def test_02_large_room(self):
        """Test 2: Large open hall (12m x 8m x 3.5m) partitioned with 2.0m cells."""
        engine = SpatialCellEngine(cell_size_m=2.0)

        xs = np.linspace(0.2, 11.8, 20)
        ys = np.linspace(0.2, 3.4, 8)
        zs = np.linspace(0.2, 7.8, 15)
        xx, yy, zz = np.meshgrid(xs, ys, zs)
        hall_pts = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()])

        engine.assign_geometry(hall_pts)
        # Expected cells: ceil(12/2)=6 in X, ceil(3.5/2)=2 in Y, ceil(8/2)=4 in Z => 6*2*4 = 48 cells
        self.assertEqual(len(engine.cells), 48)

    # -------------------------------------------------------------------------
    # Scenario 3: Large Building (Multi-Floor)
    # -------------------------------------------------------------------------
    def test_03_large_building(self):
        """Test 3: Large building across 3 vertical floors (Y=0m, Y=3.5m, Y=7m)."""
        engine = SpatialCellEngine(cell_size_m=1.0)

        floor_pts = []
        for floor_y in [0.5, 4.0, 7.5]: # 3 distinct levels
            xs = np.linspace(0, 5, 10)
            zs = np.linspace(0, 5, 10)
            xx, zz = np.meshgrid(xs, zs)
            yy = np.full_like(xx, floor_y)
            floor_pts.append(np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()]))

        building_pts = np.vstack(floor_pts)
        engine.assign_geometry(building_pts)

        # Floor Y coords should populate cy = 0, cy = 4, cy = 7
        y_coords = {c[1] for c in engine.cells.keys()}
        self.assertIn(0, y_coords)
        self.assertIn(4, y_coords)
        self.assertIn(7, y_coords)

    # -------------------------------------------------------------------------
    # Scenario 4: Complex Furniture
    # -------------------------------------------------------------------------
    def test_04_complex_furniture(self):
        """Test 4: Complex furniture - object spans across 2 neighboring cells."""
        engine = SpatialCellEngine(cell_size_m=1.0)

        # A 1.8m wide conference table centered at X=1.0 (straddles cell 0 and cell 1)
        table_obj = {
            "object_id": "table_001",
            "centroid": [1.0, 0.4, 1.5],
            "bounds": {"min_xyz": [0.1, 0.0, 0.5], "max_xyz": [1.9, 0.8, 2.5]}
        }

        engine.assign_semantics([table_obj])
        # Table centroid at X=1.0 -> maps to cell coord cx=1
        cell = engine.cells.get((1, 0, 1))
        self.assertIsNotNone(cell)
        self.assertIn("table_001", cell.semantic_object_ids)

    # -------------------------------------------------------------------------
    # Scenario 5: Different Cell Sizes
    # -------------------------------------------------------------------------
    def test_05_different_cell_sizes(self):
        """Test 5: Validates adaptive grid scaling (0.5m, 1.0m, 2.0m)."""
        pts = np.array([
            [0.1, 0.1, 0.1],
            [0.8, 0.8, 0.8]
        ])

        # Cell size 1.0m -> both points land in (0, 0, 0)
        e1 = SpatialCellEngine(cell_size_m=1.0)
        e1.assign_geometry(pts)
        self.assertEqual(len(e1.cells), 1)

        # Cell size 0.5m -> points land in (0,0,0) and (1,1,1) => 2 distinct cells
        e05 = SpatialCellEngine(cell_size_m=0.5)
        e05.assign_geometry(pts)
        self.assertEqual(len(e05.cells), 2)

    # -------------------------------------------------------------------------
    # Scenario 6: Boundary Conditions
    # -------------------------------------------------------------------------
    def test_06_boundary_conditions(self):
        """Test 6: Boundary conditions - points landing exactly on integer cell edges and origin (0,0,0)."""
        engine = SpatialCellEngine(cell_size_m=1.0)

        boundary_pts = np.array([
            [0.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [-0.001, 0.0, 0.0], # Negative boundary
            [2.0, 2.0, 2.0]
        ])

        engine.assign_geometry(boundary_pts)

        # (0,0,0) -> cell (0,0,0)
        self.assertIn((0, 0, 0), engine.cells)
        # (1,0,0) -> cell (1,0,0)
        self.assertIn((1, 0, 0), engine.cells)
        # (-0.001, 0, 0) -> cell (-1,0,0)
        self.assertIn((-1, 0, 0), engine.cells)

    # -------------------------------------------------------------------------
    # Scenario 7: Neighbor Queries
    # -------------------------------------------------------------------------
    def test_07_neighbor_queries(self):
        """Test 7: Neighbor queries - 26-connectivity topological adjacency."""
        engine = SpatialCellEngine(cell_size_m=1.0)

        # Create a 3x3x3 block of cells
        for cx in range(3):
            for cy in range(3):
                for cz in range(3):
                    engine.get_or_create_cell(cx, cy, cz)

        engine.compute_neighbors(connectivity=26)

        # Center cell (1, 1, 1) has exactly 26 neighbors in a 3x3x3 grid
        center_neighbors = engine.query_neighbors(1, 1, 1)
        self.assertEqual(len(center_neighbors), 26)

        # Corner cell (0, 0, 0) has 7 neighbors in a 3x3x3 grid
        corner_neighbors = engine.query_neighbors(0, 0, 0)
        self.assertEqual(len(corner_neighbors), 7)

    # -------------------------------------------------------------------------
    # End-to-End Serialization & Versioning
    # -------------------------------------------------------------------------
    def test_08_versioning_and_storage(self):
        """Test 8: Cell version increment on dirty update and JSON manifest export."""
        engine = SpatialCellEngine(cell_size_m=1.0)
        cell = engine.get_or_create_cell(0, 0, 0)
        self.assertEqual(cell.version, 1)
        self.assertFalse(cell.is_dirty)

        # Mark dirty
        engine.mark_cell_dirty(0, 0, 0)
        self.assertEqual(cell.version, 2)
        self.assertTrue(cell.is_dirty)

        manifest = engine.store_cell_metadata(self.output_dir)
        self.assertEqual(manifest["status"], "success")
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "spatial_cells.json")))


if __name__ == "__main__":
    unittest.main()
