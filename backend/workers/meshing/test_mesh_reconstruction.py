import os
import sys
import unittest
import numpy as np
import open3d as o3d
import tempfile
import shutil

from mesh_reconstruction_engine import MeshReconstructionEngine

class TestMeshReconstruction(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.output_dir = os.path.join(self.test_dir, "output")
        os.makedirs(self.output_dir, exist_ok=True)
        self.engine = MeshReconstructionEngine(poisson_depth=6)

    def tearDown(self):
        shutil.rmtree(self.test_dir)
        
    def _create_synthetic_pointcloud(self, points, filename="dense_points3D.ply"):
        pcd = o3d.geometry.PointCloud()
        points = np.array(points, dtype=np.float64)
        points += np.random.normal(0, 0.001, points.shape)
        pcd.points = o3d.utility.Vector3dVector(points)
        # Add basic normals pointing towards Z for surface reconstruction to work
        pcd.estimate_normals()
        pcd.orient_normals_towards_camera_location(np.array([0., 0., 10.]))
        
        filepath = os.path.join(self.test_dir, filename)
        o3d.io.write_point_cloud(filepath, pcd)
        return filepath

    def _validate_reconstruction(self, mesh, metadata):
        self.assertIsNotNone(mesh)
        self.assertGreater(len(mesh.vertices), 0)
        self.assertGreater(len(mesh.triangles), 0)
        self.assertIn("topology", metadata)
        # Poisson generated meshes are typically watertight or have boundaries
        # We ensure the manifold check was executed and recorded
        self.assertIn("is_edge_manifold", metadata["topology"])
        self.assertIn("spatial_cells_count", metadata)

    def test_01_flat_wall(self):
        # Generate dense grid for a wall
        y, x = np.mgrid[0:2:0.05, 0:2:0.05]
        z = np.zeros_like(x)
        points = np.column_stack([x.flatten(), y.flatten(), z.flatten()])
        path = self._create_synthetic_pointcloud(points)
        
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)

    def test_02_floor(self):
        # Generate dense grid for a floor (XZ plane)
        z, x = np.mgrid[0:2:0.05, 0:2:0.05]
        y = np.zeros_like(x)
        points = np.column_stack([x.flatten(), y.flatten(), z.flatten()])
        path = self._create_synthetic_pointcloud(points)
        
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)

    def test_03_ceiling(self):
        z, x = np.mgrid[0:2:0.05, 0:2:0.05]
        y = np.ones_like(x) * 2.5 # Ceiling height
        points = np.column_stack([x.flatten(), y.flatten(), z.flatten()])
        path = self._create_synthetic_pointcloud(points)
        
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)

    def test_04_furniture(self):
        # Box representing furniture
        points = []
        for x in np.linspace(0, 1, 20):
            for y in np.linspace(0, 1, 20):
                for z in np.linspace(0, 1, 20):
                    if x == 0 or x == 1.0 or y == 0 or y == 1.0 or z == 0 or z == 1.0:
                        points.append([x, y, z])
        path = self._create_synthetic_pointcloud(np.array(points))
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)
        # Furniture box should report topological metrics
        self.assertIn("is_watertight", meta["topology"])

    def test_05_door_aperture(self):
        # Wall with a hole in the middle
        points = []
        for y in np.linspace(0, 2.5, 50):
            for x in np.linspace(0, 3, 60):
                if not (1.0 < x < 2.0 and y < 2.0): # Door gap
                    points.append([x, y, 0])
        path = self._create_synthetic_pointcloud(np.array(points))
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)
        self.assertGreater(len(meta["detected_holes"]), 0, "Door should introduce boundary edges/holes")

    def test_06_window_aperture(self):
        # Wall with a window hole
        points = []
        for y in np.linspace(0, 2.5, 50):
            for x in np.linspace(0, 3, 60):
                if not (1.0 < x < 2.0 and 1.0 < y < 2.0): # Window gap
                    points.append([x, y, 0])
        path = self._create_synthetic_pointcloud(np.array(points))
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)
        
    def test_07_complex_geometry(self):
        # Sphere
        points = []
        for phi in np.linspace(0, np.pi, 30):
            for theta in np.linspace(0, 2*np.pi, 30):
                points.append([np.sin(phi)*np.cos(theta), np.sin(phi)*np.sin(theta), np.cos(phi)])
        path = self._create_synthetic_pointcloud(np.array(points))
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)

    def test_08_narrow_corridor(self):
        # Long narrow tube
        points = []
        for z in np.linspace(0, 10, 200):
            for angle in np.linspace(0, 2*np.pi, 20):
                points.append([np.cos(angle)*0.5, np.sin(angle)*0.5, z])
        path = self._create_synthetic_pointcloud(np.array(points))
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)
        self.assertGreater(meta["spatial_cells_count"], 1, "Long corridor must be partitioned into multiple cells")

    def test_09_multi_room(self):
        # Two boxes connected by a corridor
        points = []
        # Room 1
        for x in np.linspace(0, 2, 20):
            for y in np.linspace(0, 2, 20):
                points.append([x, y, 0])
        # Corridor
        for x in np.linspace(2, 4, 20):
            for y in np.linspace(0.8, 1.2, 5):
                points.append([x, y, 0])
        # Room 2
        for x in np.linspace(4, 6, 20):
            for y in np.linspace(0, 2, 20):
                points.append([x, y, 0])
        path = self._create_synthetic_pointcloud(np.array(points))
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        self._validate_reconstruction(mesh, meta)
        
    def test_10_integration_full_chain(self):
        # Validates P20 -> P21 -> P22 contract conceptually by using arbitrary noise
        points = np.random.rand(1000, 3)
        path = self._create_synthetic_pointcloud(points)
        mesh, meta = self.engine.run_pipeline(path, self.output_dir)
        
        # We expect the outlier removal and Poisson depth to either prune it entirely 
        # or create a minimal mesh, but importantly, it must not crash.
        self.assertIn("initial_points", meta)
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "mesh3D.ply")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "mesh3D_metadata.json")))
        self.assertTrue(os.path.exists(os.path.join(self.output_dir, "mesh3D_spatial_cells.json")))

if __name__ == '__main__':
    unittest.main()
