import numpy as np
import pytest
from geometry.planes import fit_plane_ransac, compute_dihedral_angle_deg, compute_bounding_box
from geometry.spatial_hash import SpatialHashGrid
from geometry.normals import estimate_point_normals
from geometry.mesh_repair import validate_manifold_mesh, filter_mesh_density_threshold

def test_fit_plane_ransac():
    # Generate synthetic plane z = 0 with a little noise
    np.random.seed(42)
    x = np.random.uniform(-1, 1, 100)
    y = np.random.uniform(-1, 1, 100)
    z = np.random.normal(0.0, 0.005, 100)
    points = np.column_stack([x, y, z])
    
    plane_model, inliers = fit_plane_ransac(points, distance_threshold=0.02, num_iterations=100)
    # normal should be close to [0, 0, 1] or [0, 0, -1]
    assert abs(abs(plane_model[2]) - 1.0) < 0.1
    assert len(inliers) > 90

def test_dihedral_angle():
    n1 = np.array([0.0, 1.0, 0.0])
    n2 = np.array([1.0, 0.0, 0.0])
    angle = compute_dihedral_angle_deg(n1, n2)
    assert pytest.approx(angle, 0.01) == 90.0

def test_bounding_box():
    pts = np.array([
        [-1.0, -2.0, -3.0],
        [1.0, 2.0, 3.0]
    ])
    min_xyz, max_xyz, center_xyz = compute_bounding_box(pts)
    assert np.allclose(min_xyz, [-1.0, -2.0, -3.0])
    assert np.allclose(max_xyz, [1.0, 2.0, 3.0])
    assert np.allclose(center_xyz, [0.0, 0.0, 0.0])

def test_spatial_hash_grid():
    grid = SpatialHashGrid(voxel_size_m=0.1)
    pts = np.array([
        [0.01, 0.01, 0.01],
        [0.02, 0.02, 0.02], # Same voxel
        [0.50, 0.50, 0.50]  # Different voxel
    ], dtype=np.float32)
    
    assert grid.insert(pts[0], 0) is True
    assert grid.insert(pts[1], 1) is False
    assert grid.insert(pts[2], 2) is True
    
    downsampled_pts, _ = grid.downsample(pts)
    assert len(downsampled_pts) == 2

def test_estimate_point_normals():
    # Horizontal plane z = 0, camera at [0, 0, 5]
    x, y = np.meshgrid(np.linspace(-1, 1, 5), np.linspace(-1, 1, 5))
    pts = np.column_stack([x.flatten(), y.flatten(), np.zeros(25)])
    normals = estimate_point_normals(pts, k_neighbors=5, camera_origin=np.array([0.0, 0.0, 5.0]))
    assert normals.shape == (25, 3)
    # Normals should point in +Z direction towards camera
    for n in normals:
        assert n[2] > 0.5

def test_mesh_repair_and_manifold():
    # Simple single triangle (boundary edges = 3, non-manifold = 0, watertight = False)
    vertices = np.array([[0,0,0], [1,0,0], [0,1,0]], dtype=float)
    triangles = np.array([[0, 1, 2]])
    report = validate_manifold_mesh(vertices, triangles)
    assert report["triangle_count"] == 1
    assert report["boundary_edges"] == 3
    assert report["non_manifold_edges"] == 0
    assert report["is_watertight"] is False
    
    # Test density filter
    densities = np.array([0.1, 0.9, 0.9])
    clean_verts, clean_tris = filter_mesh_density_threshold(vertices, triangles, densities, quantile=0.5)
    assert len(clean_verts) < len(vertices)
