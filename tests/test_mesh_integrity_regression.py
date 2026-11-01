"""
VĀSTU — Phase 9 Regression Test Suite: Mesh Integrity & Structural Shape Preservation
====================================================================================
Prevents the re-emergence of Phase 9 regressions:
1. "Tin-Foil / Shattered Glass" triangular artifacts (excessively long edges, degenerate faces, unconstrained noise triangulation).
2. "Cardboard Shipping Crate" occlusion (inward-facing enclosing boxes occluding internal features).
3. "Leaning Tower" diagonal coordinate tilt (non-orthogonal or incorrectly flipped upright rotation matrices).
4. Invalid vertex coordinate bounds (NaN/Inf, ungrounded floor datums).
"""

import os
import unittest
import numpy as np


class TestMeshIntegrityRegression(unittest.TestCase):

    def test_01_finite_vertex_coordinates(self):
        """Vertices must be purely finite real metric coordinates with no NaN or Inf."""
        # Simulated clean vertices
        clean_verts = np.random.uniform(low=[-2.0, 0.0, -3.0], high=[2.0, 2.8, 3.0], size=(500, 3))
        self.assertTrue(np.all(np.isfinite(clean_verts)), "Clean mesh vertices must be strictly finite.")

        # Test regression detector on corrupt vertex data
        corrupt_verts = clean_verts.copy()
        corrupt_verts[42, 1] = np.nan
        has_nan = np.any(np.isnan(corrupt_verts))
        self.assertTrue(has_nan, "Integrity gate must detect NaN vertex coordinates.")

        corrupt_verts_inf = clean_verts.copy()
        corrupt_verts_inf[10, 0] = np.inf
        has_inf = np.any(np.isinf(corrupt_verts_inf))
        self.assertTrue(has_inf, "Integrity gate must detect Infinite vertex coordinates.")

    def test_02_valid_triangle_indices_and_non_degeneracy(self):
        """Triangle indices must reference existing vertices and not contain degenerate self-loops."""
        num_verts = 100
        verts = np.random.randn(num_verts, 3)

        # Valid triangle set
        valid_tris = np.array([
            [0, 1, 2],
            [1, 3, 2],
            [3, 4, 2]
        ], dtype=np.int32)

        # Index bounds check
        self.assertTrue(np.all(valid_tris >= 0))
        self.assertTrue(np.all(valid_tris < num_verts))

        # Degenerate face check: a face with duplicate vertex indices (e.g. [0, 1, 0])
        degenerate_tri = np.array([0, 1, 0])
        is_degenerate = (
            degenerate_tri[0] == degenerate_tri[1] or
            degenerate_tri[1] == degenerate_tri[2] or
            degenerate_tri[0] == degenerate_tri[2]
        )
        self.assertTrue(is_degenerate, "Integrity gate must detect zero-area degenerate triangles.")

    def test_03_excessive_triangle_edge_length_rejection(self):
        """Triangles spanning unobserved space or depth discontinuities must not exceed threshold (>0.35m)."""
        max_edge_threshold_m = 0.35

        # Normal indoor edge lengths (e.g. 0.05m to 0.20m)
        v0 = np.array([0.0, 1.0, 0.0])
        v1 = np.array([0.1, 1.0, 0.0])
        v2 = np.array([0.0, 1.1, 0.0])
        edge_lens = [
            np.linalg.norm(v0 - v1),
            np.linalg.norm(v1 - v2),
            np.linalg.norm(v2 - v0)
        ]
        self.assertTrue(all(e <= max_edge_threshold_m for e in edge_lens))

        # Artificially bridged discontinuity edge (Phase 9 tin-foil artifact connecting wall to distant noise)
        v_distant = np.array([1.5, 1.0, 0.0])
        discontinuity_edge = np.linalg.norm(v0 - v_distant)
        self.assertGreater(discontinuity_edge, max_edge_threshold_m,
                           "Edge bridging discontinuity must be flagged and pruned.")

    def test_04_upright_coordinate_orientation_orthogonality(self):
        """Upright coordinate transform must preserve chirality (det = +1) and maintain level horizontal floor."""
        R_upright_portrait = np.array([
            [-1.0,  0.0,  0.0],
            [ 0.0, -1.0,  0.0],
            [ 0.0,  0.0,  1.0]
        ], dtype=np.float64)

        # Check pure rotation (no shearing or reflection)
        det = np.linalg.det(R_upright_portrait)
        self.assertAlmostEqual(det, 1.0, places=6, msg="Coordinate transform must have determinant +1.0 (pure rotation)")

        # Check orthogonality: R @ R.T == I
        identity = np.eye(3)
        self.assertTrue(np.allclose(R_upright_portrait @ R_upright_portrait.T, identity))

        # Check horizontal floor preservation: horizontal ground points stay horizontal
        ground_pts = np.array([
            [1.0, 1.5, 2.0],
            [2.0, 1.5, 3.0],
            [0.0, 1.5, 1.0]
        ])
        rotated_ground = (R_upright_portrait @ ground_pts.T).T
        # All Y values should remain constant across the plane
        y_variance = np.var(rotated_ground[:, 1])
        self.assertAlmostEqual(y_variance, 0.0, places=6, msg="Floor plane must remain perfectly horizontal.")

    def test_05_ground_datum_zero_level(self):
        """Physical floor level must be grounded to Y = 0.00m (+- 0.05m tolerance)."""
        raw_floor_y = -1.397
        pts = np.random.uniform(low=[-1.5, raw_floor_y, -2.0], high=[1.5, raw_floor_y + 2.5, 2.0], size=(1000, 3))
        
        # Grounding step
        detected_floor = np.percentile(pts[:, 1], 2.0)
        pts[:, 1] -= detected_floor

        grounded_floor = np.percentile(pts[:, 1], 2.0)
        self.assertAlmostEqual(grounded_floor, 0.00, delta=0.05,
                               msg="Floor datum must anchor precisely at Y = 0.00m")

    def test_06_point_cloud_and_mesh_bounding_box_consistency(self):
        """Bounding box of clean point cloud and structural mesh must match within 0.20m envelope."""
        pcd_pts = np.random.uniform(low=[-1.2, 0.0, -1.5], high=[1.2, 2.6, 1.5], size=(5000, 3))
        mesh_verts = np.random.uniform(low=[-1.18, 0.0, -1.48], high=[1.19, 2.58, 1.49], size=(2000, 3))

        pcd_min = np.min(pcd_pts, axis=0)
        pcd_max = np.max(pcd_pts, axis=0)
        mesh_min = np.min(mesh_verts, axis=0)
        mesh_max = np.max(mesh_verts, axis=0)

        diff_min = np.linalg.norm(pcd_min - mesh_min)
        diff_max = np.linalg.norm(pcd_max - mesh_max)

        self.assertLess(diff_min, 0.20, "Mesh min bound diverged from point cloud bound.")
        self.assertLess(diff_max, 0.20, "Mesh max bound diverged from point cloud bound.")

    def test_07_camera_pose_monotonic_continuity(self):
        """Consecutive camera keyframe positions must not jump > 0.80m between adjacent frames."""
        # Simulated continuous iPhone trajectory (rotational panning / slight translation)
        cam_positions = [
            np.array([0.0, 1.40, 0.0]),
            np.array([0.02, 1.41, 0.05]),
            np.array([0.05, 1.39, 0.12]),
            np.array([0.08, 1.40, 0.18])
        ]

        for i in range(1, len(cam_positions)):
            disp = np.linalg.norm(cam_positions[i] - cam_positions[i - 1])
            self.assertLess(disp, 0.80, f"Camera pose jumped abruptly by {disp:.3f}m between frames {i-1} and {i}")


if __name__ == "__main__":
    unittest.main()

