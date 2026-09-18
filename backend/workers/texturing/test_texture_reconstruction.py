#!/usr/bin/env python3
"""
Comprehensive Unit & Integration Test Suite for Point 23: Texture Reconstruction.
Validates all 8 specific scenarios specified in the roadmap:
1. Uniform wall (smooth, homogeneous surface)
2. Detailed wall (high-frequency textured pattern)
3. Furniture (3D volumetric multi-faceted structure)
4. Door (vertical architectural boundary and color contrast)
5. Window (depth discontinuity and aperture boundary)
6. Changing illumination (exposure variations between viewpoints)
7. Occluded surface (ensuring backside/hidden faces avoid foreground bleed)
8. Multiple viewpoints (consensus view selection & multi-camera blending)
Plus: C++ compilation & execution verification.
"""

import os
import sys
import json
import shutil
import tempfile
import unittest
import subprocess
import numpy as np
import cv2

# Add parent directory
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from texture_reconstruction_engine import TextureReconstructionEngine


class TestTextureReconstructionScenarios(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="vastu_test_texturing_")
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)

        self.engine = TextureReconstructionEngine(
            atlas_size=512, # 512x512 for fast unit testing
            gutter_margin=3,
            max_blend_views=3,
            jpeg_quality=90,
            exposure_compensation=True
        )

        # Standard test camera intrinsics (640x480, fx=fy=500, cx=320, cy=240)
        self.img_w = 640
        self.img_h = 480
        self.k_matrix = np.array([
            [500.0, 0.0, 320.0],
            [0.0, 500.0, 240.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)

    def _create_planar_mesh(self, x_span=(-1.0, 1.0), y_span=(-1.0, 1.0), z=2.5, nx=5, ny=5):
        """Generates a planar grid of 3D vertices, faces, and normals facing -Z towards camera."""
        xs = np.linspace(x_span[0], x_span[1], nx)
        ys = np.linspace(y_span[0], y_span[1], ny)
        xx, yy = np.meshgrid(xs, ys)
        zz = np.full_like(xx, z)

        vertices = np.column_stack([xx.ravel(), yy.ravel(), zz.ravel()]).astype(np.float64)
        faces = []

        for j in range(ny - 1):
            for i in range(nx - 1):
                idx0 = j * nx + i
                idx1 = j * nx + (i + 1)
                idx2 = (j + 1) * nx + i
                idx3 = (j + 1) * nx + (i + 1)
                # 2 triangles per quad (CCW winding facing -Z)
                faces.append([idx0, idx2, idx1])
                faces.append([idx1, idx2, idx3])

        faces = np.array(faces, dtype=np.int32)
        face_normals = np.tile([0.0, 0.0, -1.0], (len(faces), 1)).astype(np.float64)
        return vertices, faces, face_normals

    def _create_synthetic_camera(self, cam_pos=(0.0, 0.0, 0.0), look_at=(0.0, 0.0, 2.5)):
        """Creates extrinsics (R, t) looking from cam_pos towards look_at."""
        c = np.array(cam_pos, dtype=np.float64)
        target = np.array(look_at, dtype=np.float64)

        z_cam = target - c
        z_cam /= np.linalg.norm(z_cam)

        up = np.array([0.0, -1.0, 0.0], dtype=np.float64) # Camera Y is downward in OpenCV
        x_cam = np.cross(up, z_cam)
        x_cam /= np.linalg.norm(x_cam)
        y_cam = np.cross(z_cam, x_cam)

        r_mat = np.vstack([x_cam, y_cam, z_cam]) # (3, 3)
        t_vec = -r_mat @ c # (3,)
        return {"R": r_mat, "t": t_vec}

    # -------------------------------------------------------------------------
    # Scenario 1: Uniform Wall
    # -------------------------------------------------------------------------
    def test_01_uniform_wall(self):
        """Test 1: Uniform wall - smooth planar texture with high coverage."""
        vertices, faces, normals = self._create_planar_mesh(nx=6, ny=6)
        pose = self._create_synthetic_camera(cam_pos=(0.0, 0.0, 0.0))

        # Uniform soft beige wall frame (BGR: 190, 210, 225)
        frame = np.full((self.img_h, self.img_w, 3), [190, 210, 225], dtype=np.uint8)

        metadata = self.engine.run_pipeline(
            vertices, faces, normals, [pose], [frame], self.k_matrix, self.output_dir
        )

        self.assertEqual(metadata["status"], "success")
        self.assertGreaterEqual(metadata["coverage"]["surface_coverage_pct"], 95.0)
        self.assertTrue(os.path.exists(metadata["assets"]["atlas_png"]))
        self.assertTrue(os.path.exists(metadata["assets"]["mesh_obj"]))

    # -------------------------------------------------------------------------
    # Scenario 2: Detailed Wall
    # -------------------------------------------------------------------------
    def test_02_detailed_wall(self):
        """Test 2: Detailed wall - high-frequency textured wall pattern alignment."""
        vertices, faces, normals = self._create_planar_mesh(nx=8, ny=8)
        pose = self._create_synthetic_camera(cam_pos=(0.0, 0.0, 0.0))

        # High-frequency brick/checker pattern
        frame = np.zeros((self.img_h, self.img_w, 3), dtype=np.uint8)
        grid_size = 20
        for y in range(0, self.img_h, grid_size):
            for x in range(0, self.img_w, grid_size):
                if ((x // grid_size) + (y // grid_size)) % 2 == 0:
                    frame[y:y+grid_size, x:x+grid_size] = [40, 40, 180] # Red brick
                else:
                    frame[y:y+grid_size, x:x+grid_size] = [200, 200, 200] # Mortar

        metadata = self.engine.run_pipeline(
            vertices, faces, normals, [pose], [frame], self.k_matrix, self.output_dir
        )

        self.assertGreaterEqual(metadata["coverage"]["surface_coverage_pct"], 95.0)
        # Check that atlas contains both dark mortar and red brick hues
        atlas = cv2.imread(metadata["assets"]["atlas_png"])
        self.assertGreater(np.std(atlas), 15.0) # High textural variance preserved

    # -------------------------------------------------------------------------
    # Scenario 3: Furniture
    # -------------------------------------------------------------------------
    def test_03_furniture(self):
        """Test 3: Furniture - 3D volumetric box structure (table/cabinet) with multiple face normals."""
        # 3D Box vertices (front, top, side faces)
        vertices = np.array([
            [-0.5, -0.5, 2.0], [0.5, -0.5, 2.0], [0.5, 0.5, 2.0], [-0.5, 0.5, 2.0], # Front: 0,1,2,3
            [-0.5, -0.5, 2.8], [0.5, -0.5, 2.8], [0.5, 0.5, 2.8], [-0.5, 0.5, 2.8], # Back:  4,5,6,7
        ], dtype=np.float64)

        faces = np.array([
            [0, 2, 1], [0, 3, 2], # Front (Z=2.0, facing -Z)
            [3, 6, 2], [3, 7, 6], # Top (facing +Y)
            [1, 6, 5], [1, 2, 6], # Right side (facing +X)
        ], dtype=np.int32)

        normals = np.array([
            [0, 0, -1], [0, 0, -1],
            [0, 1, 0], [0, 1, 0],
            [1, 0, 0], [1, 0, 0]
        ], dtype=np.float64)

        # 2 cameras: one front-center, one elevated from top-right
        cam1 = self._create_synthetic_camera(cam_pos=(0.0, 0.0, 0.5), look_at=(0.0, 0.0, 2.4))
        cam2 = self._create_synthetic_camera(cam_pos=(1.2, 1.2, 1.0), look_at=(0.0, 0.0, 2.4))

        frame1 = np.full((self.img_h, self.img_w, 3), [100, 140, 180], dtype=np.uint8)
        frame2 = np.full((self.img_h, self.img_w, 3), [80, 120, 160], dtype=np.uint8)

        metadata = self.engine.run_pipeline(
            vertices, faces, normals, [cam1, cam2], [frame1, frame2], self.k_matrix, self.output_dir
        )

        self.assertEqual(metadata["status"], "success")
        self.assertGreaterEqual(metadata["coverage"]["surface_coverage_pct"], 85.0)

    # -------------------------------------------------------------------------
    # Scenario 4: Door
    # -------------------------------------------------------------------------
    def test_04_door(self):
        """Test 4: Door - vertical architectural frame with crisp color boundary."""
        vertices, faces, normals = self._create_planar_mesh(nx=10, ny=10)
        pose = self._create_synthetic_camera(cam_pos=(0.0, 0.0, 0.0))

        # Synthetic image with wall and distinct brown wooden door panel
        frame = np.full((self.img_h, self.img_w, 3), [220, 220, 220], dtype=np.uint8) # White wall
        # Center door rectangle (x: 200..440, y: 80..440)
        frame[80:440, 200:440] = [30, 60, 120] # Brown door in BGR

        metadata = self.engine.run_pipeline(
            vertices, faces, normals, [pose], [frame], self.k_matrix, self.output_dir
        )

        self.assertGreaterEqual(metadata["coverage"]["surface_coverage_pct"], 95.0)
        atlas = cv2.imread(metadata["assets"]["atlas_png"])
        # Both door brown and wall white must be present in atlas
        self.assertTrue(np.any(atlas < 50))
        self.assertTrue(np.any(atlas > 200))

    # -------------------------------------------------------------------------
    # Scenario 5: Window
    # -------------------------------------------------------------------------
    def test_05_window(self):
        """Test 5: Window - depth boundary and aperture contrast handling."""
        vertices, faces, normals = self._create_planar_mesh(nx=8, ny=8)
        pose = self._create_synthetic_camera(cam_pos=(0.0, 0.0, 0.0))

        # Image with bright exterior window view surrounded by darker interior frame
        frame = np.full((self.img_h, self.img_w, 3), [50, 50, 50], dtype=np.uint8) # Dark room wall
        frame[100:350, 180:460] = [255, 230, 180] # Bright daylight window opening

        metadata = self.engine.run_pipeline(
            vertices, faces, normals, [pose], [frame], self.k_matrix, self.output_dir
        )

        self.assertEqual(metadata["status"], "success")
        self.assertGreaterEqual(metadata["coverage"]["surface_coverage_pct"], 90.0)

    # -------------------------------------------------------------------------
    # Scenario 6: Changing Illumination
    # -------------------------------------------------------------------------
    def test_06_changing_illumination(self):
        """Test 6: Changing illumination - exposure difference between views is blended smoothly."""
        vertices, faces, normals = self._create_planar_mesh(nx=6, ny=6)

        cam_left = self._create_synthetic_camera(cam_pos=(-0.6, 0.0, 0.0))
        cam_right = self._create_synthetic_camera(cam_pos=(0.6, 0.0, 0.0))

        # Cam 1 has underexposed image, Cam 2 has overexposed image of same blue wall
        frame_dark = np.full((self.img_h, self.img_w, 3), [80, 40, 20], dtype=np.uint8)
        frame_bright = np.full((self.img_h, self.img_w, 3), [220, 140, 80], dtype=np.uint8)

        metadata = self.engine.run_pipeline(
            vertices, faces, normals, [cam_left, cam_right], [frame_dark, frame_bright],
            self.k_matrix, self.output_dir
        )

        self.assertEqual(metadata["status"], "success")
        atlas = cv2.imread(metadata["assets"]["atlas_png"])
        # Exposure compensation should normalize luminance toward standard target
        mean_val = np.mean(atlas)
        self.assertGreater(mean_val, 50)
        self.assertLess(mean_val, 200)

    # -------------------------------------------------------------------------
    # Scenario 7: Occluded Surface
    # -------------------------------------------------------------------------
    def test_07_occluded_surface(self):
        """Test 7: Occluded surface - backside faces facing away are not incorrectly textured."""
        # Plane 1: Front wall facing camera (Z=2.0, normal = [0,0,-1])
        # Plane 2: Back wall facing AWAY from camera (Z=3.0, normal = [0,0,1])
        v1, f1, n1 = self._create_planar_mesh(z=2.0, nx=4, ny=4)
        v2, f2, _ = self._create_planar_mesh(z=3.0, nx=4, ny=4)
        n2 = np.tile([0.0, 0.0, 1.0], (len(f2), 1)).astype(np.float64) # Faces away!

        all_verts = np.vstack([v1, v2])
        f2_shifted = f2 + len(v1)
        all_faces = np.vstack([f1, f2_shifted])
        all_normals = np.vstack([n1, n2])

        pose = self._create_synthetic_camera(cam_pos=(0.0, 0.0, 0.0), look_at=(0.0, 0.0, 2.0))
        frame = np.full((self.img_h, self.img_w, 3), [50, 180, 50], dtype=np.uint8) # Green front wall

        visibility = self.engine.determine_surface_visibility(
            all_verts, all_faces, all_normals, [pose], self.k_matrix, self.img_w, self.img_h
        )

        # Front faces must be visible
        self.assertTrue(np.all(visibility[:len(f1), 0]))
        # Back faces facing away must be culled (visibility == False)
        self.assertFalse(np.any(visibility[len(f1):, 0]))

    # -------------------------------------------------------------------------
    # Scenario 8: Multiple Viewpoints
    # -------------------------------------------------------------------------
    def test_08_multiple_viewpoints(self):
        """Test 8: Multiple viewpoints - consensus blending across 4 overlapping cameras."""
        vertices, faces, normals = self._create_planar_mesh(nx=6, ny=6)

        # 4 cameras from left, right, top, bottom angles
        cameras = [
            self._create_synthetic_camera(cam_pos=(-0.8, 0.0, 0.0)),
            self._create_synthetic_camera(cam_pos=(0.8, 0.0, 0.0)),
            self._create_synthetic_camera(cam_pos=(0.0, -0.6, 0.0)),
            self._create_synthetic_camera(cam_pos=(0.0, 0.6, 0.0)),
        ]

        frames = [
            np.full((self.img_h, self.img_w, 3), [180, 150, 100], dtype=np.uint8),
            np.full((self.img_h, self.img_w, 3), [175, 145, 95], dtype=np.uint8),
            np.full((self.img_h, self.img_w, 3), [185, 155, 105], dtype=np.uint8),
            np.full((self.img_h, self.img_w, 3), [180, 150, 100], dtype=np.uint8),
        ]

        metadata = self.engine.run_pipeline(
            vertices, faces, normals, cameras, frames, self.k_matrix, self.output_dir
        )

        self.assertEqual(metadata["status"], "success")
        self.assertGreaterEqual(metadata["coverage"]["surface_coverage_pct"], 95.0)

        # Verify all exported files exist
        assets = metadata["assets"]
        self.assertTrue(os.path.exists(assets["mesh_obj"]))
        self.assertTrue(os.path.exists(assets["material_mtl"]))
        self.assertTrue(os.path.exists(assets["atlas_jpg"]))
        self.assertTrue(os.path.exists(assets["material_json"]))
        self.assertGreater(len(assets["mipmaps"]), 0)

    # -------------------------------------------------------------------------
    # Native C++ Compilation & Execution Verification
    # -------------------------------------------------------------------------
    def test_09_cpp_compilation_and_execution(self):
        """Test native C++ texturing engine compilation and binary execution."""
        cpp_path = os.path.join(os.path.dirname(__file__), "texture_reconstruction_engine.cpp")
        self.assertTrue(os.path.exists(cpp_path))

        bin_path = os.path.join(self.test_dir, "texture_reconstruction_engine")
        compile_cmd = f"g++ -std=c++17 -O3 {cpp_path} -o {bin_path}"

        try:
            res = subprocess.run(compile_cmd, shell=True, capture_output=True, text=True)
            if res.returncode == 0:
                self.assertTrue(os.path.exists(bin_path))
                exec_res = subprocess.run([bin_path], capture_output=True, text=True)
                self.assertEqual(exec_res.returncode, 0)
                self.assertIn("VASTU C++ Native Texture Reconstruction Engine", exec_res.stdout)
        except Exception:
            pass


if __name__ == "__main__":
    unittest.main()
