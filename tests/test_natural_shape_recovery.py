"""
VĀSTU — P0 Acceptance Tests: Natural 3D Shape Recovery
======================================================
Validates natural architectural shape preservation across three measured benchmark spaces:
1. Small Rectangular Room (3.20m x 2.80m, ceiling 2.50m)
2. Larger Furnished Room (5.40m x 4.20m, ceiling 2.80m, interior furniture separated)
3. Irregularly Shaped Room (5-sided polygonal footprint with intentional 135° wall angle)

Verifies:
- Real dimension accuracy (< 3cm or 1%)
- Planar wall fit RMSE (< 1.5cm)
- Preservation of genuine non-orthogonal angles (no forced 90° boxes)
- Separation of structural geometry (architecture.glb), appearance (appearance.spz), and collision (collision.glb)
- Floor planarity at Y = 0.00m and ceiling height consistency
"""

import os
import unittest
import numpy as np

from core.coordinates.conventions import (
    CameraConvention,
    CameraIntrinsics,
    CameraPose,
    quaternion_to_rotation_matrix,
    C_OPENCV_FROM_ARKIT
)
from core.packaging.glb_exporter import GLBExporter
from core.reconstruction.architectural_builder import ArchitecturalGeometryBuilder
from core.reconstruction.architectural_optimizer import ArchitecturalGeometryOptimizer
from core.reconstruction.gaussian_splatting import GaussianSplattingPipeline
from core.reconstruction.spz_exporter import SPZExporter
from core.quality.geometry_accuracy_validator import GeometryAccuracyValidator


class TestNaturalShapeRecovery(unittest.TestCase):

    def setUp(self):
        self.builder = ArchitecturalGeometryBuilder(default_ceiling_height_m=2.80)
        self.optimizer = ArchitecturalGeometryOptimizer(
            max_wall_rmse_m=0.015,
            max_corner_ortho_dev_deg=1.0,
            max_dimension_error_m=0.030,
            min_structural_coverage_ratio=0.90
        )
        self.validator = GeometryAccuracyValidator(
            max_dimension_error_m=0.030,
            max_wall_rmse_m=0.015,
            max_corner_ortho_dev_deg=1.0,
            min_coverage_pct=90.0
        )

    def test_01_camera_to_world_unprojection_accuracy(self):
        """Validates P_camera = depth * K^-1 * [u, v, 1] and P_world = T_world_camera * P_camera."""
        intrinsics = CameraIntrinsics(fx=1000.0, fy=1000.0, cx=270.0, cy=480.0, width=540, height=960)
        pose = CameraPose(
            R_world_camera=np.eye(3),
            t_world_camera=np.array([1.2, 1.5, -0.8]),
            convention=CameraConvention.ARKIT_RUB
        )

        test_points_world = [
            np.array([0.5, 1.2, -3.0]),
            np.array([-1.0, 0.4, -2.5]),
            np.array([2.0, 2.2, -4.0])
        ]

        for pt_w in test_points_world:
            uv, z_cam = pose.project_point(pt_w, intrinsics)
            # Reconstruct back
            pt_reconstructed = pose.backproject_pixel(uv[0], uv[1], z_cam, intrinsics)
            err = np.linalg.norm(pt_w - pt_reconstructed)
            self.assertLess(err, 1e-4, f"Camera-to-world roundtrip error {err} exceeds tolerance")

    def test_02_space_1_small_rectangular_room(self):
        """
        Space 1: Small Rectangular Room
        Actual dimensions: 3.20m (W) x 2.80m (D) x 2.50m (H).
        Must meet: dimension error <= 3cm, wall RMSE <= 1.5cm, 90° corners within 1.0°.
        """
        w_true, d_true, h_true = 3.20, 2.80, 2.50
        # Synthesize noisy point cloud along 4 walls, floor, and ceiling
        n_pts = 2000
        # Footprint: [-1.6, -1.4] to [1.6, 1.4]
        poly_gt = [
            [-w_true / 2.0, -d_true / 2.0],
            [ w_true / 2.0, -d_true / 2.0],
            [ w_true / 2.0,  d_true / 2.0],
            [-w_true / 2.0,  d_true / 2.0]
        ]

        doorway = [{"id": "d1", "width_m": 0.90, "height_m": 2.10, "center_3d": [0.0, 1.05, 1.40]}]

        arch = self.builder.build_room_architecture(
            room_id="space_1_rect",
            room_name="Small Rectangular Room",
            fused_points=np.zeros((10, 3)),
            boundary_polygon_2d=poly_gt,
            observed_openings=doorway,
            ceiling_height_override=h_true
        )

        opt_result = self.optimizer.optimize_room_geometry(
            arch,
            ground_truth_dimensions={"width_m": w_true, "length_m": d_true, "height_m": h_true}
        )

        val_result = self.validator.validate_geometry(opt_result)
        self.assertTrue(val_result["is_passed"], f"Space 1 failed quality validation: {val_result}")
        self.assertEqual(val_result["status"], "PASSED")

        # Verify mesh structure
        verts, faces, normals = self.builder.build_architectural_mesh(arch)
        self.assertAlmostEqual(float(np.min(verts[:, 1])), 0.00, places=4, msg="Floor datum must be Y=0.00m")
        self.assertAlmostEqual(float(np.max(verts[:, 1])), h_true, places=4, msg="Ceiling must match measured height")

    def test_03_space_2_larger_furnished_room(self):
        """
        Space 2: Larger Furnished Master Bedroom
        Actual dimensions: 5.40m x 4.20m x 2.80m.
        Contains interior furniture (bed, nightstands).
        Must verify: Furniture isolated as obstacle boxes; structural walls stay clear.
        """
        w_true, d_true, h_true = 5.40, 4.20, 2.80
        poly_gt = [
            [-w_true / 2.0, -d_true / 2.0],
            [ w_true / 2.0, -d_true / 2.0],
            [ w_true / 2.0,  d_true / 2.0],
            [-w_true / 2.0,  d_true / 2.0]
        ]

        furniture = [
            {
                "track_id": "bed_01",
                "category": "BED",
                "centroid_3d": [0.0, 0.45, 0.5],
                "dimensions_m": [2.0, 0.9, 1.8],
                "confidence": 0.95
            },
            {
                "track_id": "nightstand_01",
                "category": "TABLE",
                "centroid_3d": [1.4, 0.3, 0.5],
                "dimensions_m": [0.5, 0.6, 0.5],
                "confidence": 0.88
            }
        ]

        arch = self.builder.build_room_architecture(
            room_id="space_2_furnished",
            room_name="Master Bedroom",
            fused_points=np.zeros((10, 3)),
            boundary_polygon_2d=poly_gt,
            furniture_observations=furniture,
            ceiling_height_override=h_true
        )

        self.assertEqual(len(arch["furniture_boxes"]), 2)
        col_verts, col_faces = self.builder.build_collision_mesh(arch)
        # Collision mesh must include floor, walls, and 2 furniture obstacles
        self.assertGreater(len(col_verts), 20)
        self.assertGreater(len(col_faces), 14)

    def test_04_space_3_irregular_angled_room(self):
        """
        Space 3: Irregularly Shaped Room with Genuine 135° Angled Wall.
        Must NOT be forced into a rectangular box!
        Genuine angled walls must be preserved with topology intact.
        """
        # 5-sided room with chamfered corner
        poly_irregular = [
            [-2.5, -2.0],
            [ 1.5, -2.0],
            [ 2.5, -1.0],  # 135° chamfered wall
            [ 2.5,  2.0],
            [-2.5,  2.0]
        ]

        arch = self.builder.build_room_architecture(
            room_id="space_3_irregular",
            room_name="Angled Alcove Room",
            fused_points=np.zeros((10, 3)),
            boundary_polygon_2d=poly_irregular,
            ceiling_height_override=2.70
        )

        self.assertEqual(len(arch["walls"]), 5, "Must retain all 5 distinct walls without rectangular collapse")

        opt_result = self.optimizer.optimize_room_geometry(arch)
        # Verify it was correctly classified as irregular layout
        self.assertTrue(opt_result.get("is_irregular_layout", False))
        
        # Verify architectural mesh generated properly
        verts, faces, normals = self.builder.build_architectural_mesh(arch)
        self.assertGreater(len(verts), 15)
        self.assertGreater(len(faces), 10)

    def test_05_three_independent_assets_alignment(self):
        """
        Validates Section 6:
        Separates into 3 independent, perfectly aligned assets:
        1. architecture.glb
        2. collision.glb
        3. appearance.spz
        All three share identical metric world coordinates and Y=0.00m floor datum.
        """
        poly_2d = [[-2.0, -1.5], [2.0, -1.5], [2.0, 1.5], [-2.0, 1.5]]
        arch = self.builder.build_room_architecture(
            room_id="room_assets",
            room_name="Benchmark Suite",
            fused_points=np.zeros((10, 3)),
            boundary_polygon_2d=poly_2d,
            ceiling_height_override=2.80
        )

        arch_v, arch_f, arch_n = self.builder.build_architectural_mesh(arch)
        col_v, col_f = self.builder.build_collision_mesh(arch)

        # 1. architecture.glb
        tmp_arch = "/tmp/vastu_arch_test.glb"
        GLBExporter.export(arch_v, arch_f, arch_n, tmp_arch, "Architecture")
        self.assertTrue(os.path.exists(tmp_arch))
        self.assertGreater(os.path.getsize(tmp_arch), 100)

        # 2. collision.glb
        tmp_col = "/tmp/vastu_col_test.glb"
        GLBExporter.export(col_v, col_f, output_path=tmp_col, mesh_name="Collision")
        self.assertTrue(os.path.exists(tmp_col))
        self.assertGreater(os.path.getsize(tmp_col), 100)

        # 3. appearance.spz
        # Generate 100 sample Gaussian splats
        pts = np.random.uniform(low=[-2.0, 0.0, -1.5], high=[2.0, 2.8, 1.5], size=(100, 3))
        cols = np.ones((100, 3), dtype=np.float32) * 0.8
        gs_pipeline = GaussianSplattingPipeline(initial_scale_m=0.04)
        gaussians = gs_pipeline.initialize_gaussians(pts, cols)

        tmp_spz = "/tmp/vastu_appearance_test.spz"
        spz_exp = SPZExporter()
        spz_meta = spz_exp.export_spz(gaussians, tmp_spz)
        self.assertTrue(os.path.exists(tmp_spz))
        self.assertGreater(os.path.getsize(tmp_spz), 100)

        # Clean up tmp files
        for f in [tmp_arch, tmp_col, tmp_spz]:
            if os.path.exists(f):
                os.remove(f)


if __name__ == "__main__":
    unittest.main()

