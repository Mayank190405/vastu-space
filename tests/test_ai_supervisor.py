"""
Test Suite: Cloud AI Supervisor (Closed-Loop Self-Correction Engine)
Verifies:
1. Diagnosis of CRUMPLED_WALL_FACETING when wall normals deviate from RANSAC planes.
2. Diagnosis of FLOOR_HOLE_DEFECT when floor coverage falls below threshold.
3. Diagnosis of FLOATING_BUBBLE_DEFECT when triangles float outside point cloud consensus.
4. Clean, planar, sealed mesh approval with quality score >= 0.98 and zero defects.
5. Hyperparameter auto-tuning commands (Taubin iterations, normal radius, floor seal, consensus thresholds).
"""

import pytest
import numpy as np
import open3d as o3d
from dataclasses import asdict

from scripts.generate_video_twin import CloudAISupervisor, MeshHyperparameters


def create_synthetic_room_pcd():
    """Generates synthetic L-shaped room point cloud with floor and two walls."""
    pts = []
    # Floor: Y=0, X in [-1, 1], Z in [-1, 1]
    gx, gz = np.meshgrid(np.linspace(-1.0, 1.0, 25), np.linspace(-1.0, 1.0, 25))
    floor_pts = np.column_stack([gx.flatten(), np.zeros(gx.size), gz.flatten()])
    pts.append(floor_pts)

    # Left wall: X = -1.0, Y in [0, 2], Z in [-1, 1]
    gy, gz_w = np.meshgrid(np.linspace(0.0, 2.0, 25), np.linspace(-1.0, 1.0, 25))
    left_wall_pts = np.column_stack([-np.ones(gy.size), gy.flatten(), gz_w.flatten()])
    pts.append(left_wall_pts)

    # Back wall: Z = -1.0, Y in [0, 2], X in [-1, 1]
    gx_w, gy_b = np.meshgrid(np.linspace(-1.0, 1.0, 25), np.linspace(0.0, 2.0, 25))
    back_wall_pts = np.column_stack([gx_w.flatten(), gy_b.flatten(), -np.ones(gx_w.size)])
    pts.append(back_wall_pts)

    all_pts = np.vstack(pts)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(all_pts)
    pcd.colors = o3d.utility.Vector3dVector(np.ones_like(all_pts) * 0.7)
    return pcd


def create_synthetic_mesh(perturb_walls: bool = False, punch_floor_hole: bool = False, add_bubbles: bool = False):
    """Generates synthetic triangle mesh for testing supervisor quality gates."""
    mesh = o3d.geometry.TriangleMesh()
    verts = []
    tris = []

    def add_quad(v0, v1, v2, v3):
        base_idx = len(verts)
        verts.extend([v0, v1, v2, v3])
        tris.append([base_idx, base_idx + 1, base_idx + 2])
        tris.append([base_idx, base_idx + 2, base_idx + 3])

    # 1. Floor grid (Y=0)
    xs = np.linspace(-1.0, 1.0, 11)
    zs = np.linspace(-1.0, 1.0, 11)
    for i in range(len(xs) - 1):
        for j in range(len(zs) - 1):
            if punch_floor_hole and (abs(xs[i]) < 0.4 and abs(zs[j]) < 0.4):
                continue  # Skip center quad to create hole
            add_quad(
                [xs[i], 0.0, zs[j]],
                [xs[i], 0.0, zs[j + 1]],
                [xs[i + 1], 0.0, zs[j + 1]],
                [xs[i + 1], 0.0, zs[j]]
            )

    # 2. Left wall (X = -1.0, Y in [0, 2], Z in [-1, 1])
    ys = np.linspace(0.0, 2.0, 11)
    for i in range(len(ys) - 1):
        for j in range(len(zs) - 1):
            quad = [
                [-1.0, ys[i], zs[j]],
                [-1.0, ys[i + 1], zs[j]],
                [-1.0, ys[i + 1], zs[j + 1]],
                [-1.0, ys[i], zs[j + 1]]
            ]
            if perturb_walls:
                # Add sinusoidal normal jitter simulating tin-foil faceting
                for qv in quad:
                    qv[0] += 0.08 * np.sin(qv[1] * 8.0) * np.cos(qv[2] * 8.0)
            add_quad(*quad)

    # 3. Back wall (Z = -1.0, Y in [0, 2], X in [-1, 1])
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            quad = [
                [xs[i], ys[j], -1.0],
                [xs[i + 1], ys[j], -1.0],
                [xs[i + 1], ys[j + 1], -1.0],
                [xs[i], ys[j + 1], -1.0]
            ]
            if perturb_walls:
                for qv in quad:
                    qv[2] += 0.08 * np.sin(qv[0] * 8.0) * np.cos(qv[1] * 8.0)
            add_quad(*quad)

    # 4. Optional floating bubbles (add enough to exceed 3% threshold)
    if add_bubbles:
        for b_idx in range(25):
            add_quad(
                [3.0 + b_idx * 0.05, 1.0, 3.0],
                [3.04 + b_idx * 0.05, 1.0, 3.0],
                [3.04 + b_idx * 0.05, 1.05, 3.0],
                [3.0 + b_idx * 0.05, 1.05, 3.0]
            )

    mesh.vertices = o3d.utility.Vector3dVector(np.array(verts, dtype=np.float64))
    mesh.triangles = o3d.utility.Vector3iVector(np.array(tris, dtype=np.int32))
    mesh.compute_vertex_normals()
    mesh.compute_triangle_normals()
    return mesh


@pytest.fixture
def room_setup():
    pcd = create_synthetic_room_pcd()
    planes_data = {
        "left_wall_plane": [1.0, 0.0, 0.0, 1.0],   # X + 1.0 = 0
        "back_wall_plane": [0.0, 0.0, 1.0, 1.0],   # Z + 1.0 = 0
        "corner_origin": [-1.0, 0.0, -1.0],
        "corner_direction": [0.0, 1.0, 0.0]
    }
    return pcd, planes_data


def test_supervisor_approved_clean_mesh(room_setup):
    """Verifies that a mathematically clean mesh achieves score >= 0.98 and approved=True."""
    pcd, planes_data = room_setup
    mesh = create_synthetic_mesh(perturb_walls=False, punch_floor_hole=False, add_bubbles=False)

    supervisor = CloudAISupervisor(target_quality_score=0.98)
    diag = supervisor.evaluate_mesh(mesh, pcd, planes_data)

    assert diag["approved"] is True
    assert diag["quality_score"] >= 0.98
    assert len(diag["defects"]) == 0
    assert diag["floor_coverage_ratio"] >= 0.95
    assert diag["wall_normal_jitter"] < 0.05
    assert diag["boundary_bubble_ratio"] == 0.0


def test_supervisor_diagnoses_crumpled_wall(room_setup):
    """Verifies that high normal jitter is detected and triggers Taubin / normal radius correction."""
    pcd, planes_data = room_setup
    mesh = create_synthetic_mesh(perturb_walls=True, punch_floor_hole=False, add_bubbles=False)

    supervisor = CloudAISupervisor(target_quality_score=0.98)
    diag = supervisor.evaluate_mesh(mesh, pcd, planes_data)

    assert diag["approved"] is False
    assert "CRUMPLED_WALL_FACETING" in diag["defects"]
    assert diag["wall_normal_jitter"] > 0.09

    # Command corrections
    initial_params = MeshHyperparameters(taubin_iterations=12, normal_radius=0.12, normal_max_nn=50)
    new_params = supervisor.command_parameter_corrections(diag, initial_params)

    assert new_params.taubin_iterations > initial_params.taubin_iterations
    assert new_params.normal_radius > initial_params.normal_radius
    assert new_params.normal_max_nn > initial_params.normal_max_nn


def test_supervisor_diagnoses_floor_hole(room_setup):
    """Verifies that floor holes are detected and trigger floor seal parameter expansion."""
    pcd, planes_data = room_setup
    mesh = create_synthetic_mesh(perturb_walls=False, punch_floor_hole=True, add_bubbles=False)

    supervisor = CloudAISupervisor(target_quality_score=0.98)
    diag = supervisor.evaluate_mesh(mesh, pcd, planes_data)

    assert diag["approved"] is False
    assert "FLOOR_HOLE_DEFECT" in diag["defects"]
    assert diag["floor_coverage_ratio"] < 0.95

    initial_params = MeshHyperparameters(solid_floor_seal=True, floor_seal_y_max=0.050, consensus_distance_thresh=0.15)
    new_params = supervisor.command_parameter_corrections(diag, initial_params)

    assert new_params.solid_floor_seal is True
    assert new_params.floor_seal_y_max > initial_params.floor_seal_y_max
    assert new_params.consensus_distance_thresh > initial_params.consensus_distance_thresh


def test_supervisor_diagnoses_floating_bubble(room_setup):
    """Verifies that floating bubbles are flagged and trigger tighter consensus filtering."""
    pcd, planes_data = room_setup
    mesh = create_synthetic_mesh(perturb_walls=False, punch_floor_hole=False, add_bubbles=True)

    supervisor = CloudAISupervisor(target_quality_score=0.98)
    diag = supervisor.evaluate_mesh(mesh, pcd, planes_data)

    assert "FLOATING_BUBBLE_DEFECT" in diag["defects"]
    assert diag["boundary_bubble_ratio"] > 0.03

    initial_params = MeshHyperparameters(scale=1.10, consensus_distance_thresh=0.15)
    new_params = supervisor.command_parameter_corrections(diag, initial_params)

    assert new_params.scale < initial_params.scale
    assert new_params.consensus_distance_thresh < initial_params.consensus_distance_thresh


def test_parameter_corrections_multi_step():
    """Verifies parameter bounds and multi-step adjustment stability."""
    supervisor = CloudAISupervisor()
    params = MeshHyperparameters()

    crumpled_diag = {"defects": ["CRUMPLED_WALL_FACETING"], "wall_normal_jitter": 0.15}
    for _ in range(5):
        params = supervisor.command_parameter_corrections(crumpled_diag, params)

    assert params.taubin_iterations <= 24
    assert params.normal_radius <= 0.18
    assert params.normal_max_nn <= 80
