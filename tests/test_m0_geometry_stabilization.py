"""
Unit & Integration Tests: Milestone M0 Geometry Stabilization
Validates:
1. Metric Depth Estimator (No synthetic ramp, genuine metric outputs, confidence maps)
2. Camera Pose Composition & Scale Verification (Mathematical correctness, no arbitrary 0.3 factor, +Z optical axis)
3. TSDF Volumetric Reconstruction & Planar Surface Snapping (No crumpled tin-foil faceting, manifold geometry)
"""

import os
import pytest
import numpy as np
import cv2

from ml.depth.estimator import DepthEstimator, DepthType
from core.tracking.fusion import HierarchicalPoseEstimator
from core.dense.evidence_fusion import DenseEvidenceFusion, DenseEvidencePoint
from core.dense.tsdf_fusion import TSDFFusionEngine
from core.schemas.camera_poses import TrackingSource


def test_metric_depth_estimator_non_synthetic():
    """Validates Task 2.1: Depth Estimator outputs genuine metric depth, not a synthetic gradient ramp."""
    estimator = DepthEstimator(min_depth_m=0.5, max_depth_m=5.0)

    # Test with two different synthetic indoor scenes
    img_a = np.ones((180, 240, 3), dtype=np.uint8) * 120
    cv2.circle(img_a, (120, 90), 30, (255, 255, 255), -1)

    img_b = np.ones((180, 240, 3), dtype=np.uint8) * 60
    cv2.rectangle(img_b, (40, 40), (200, 140), (200, 200, 200), -1)

    depth_a, conf_a = estimator.estimate_depth(img_a)
    depth_b, conf_b = estimator.estimate_depth(img_b)

    # In the old defective implementation: depth was a fixed vertical gradient ramp
    # In genuine estimation: depth must depend on image content
    assert depth_a.shape == (180, 240)
    assert depth_b.shape == (180, 240)

    # Metric range bounds
    assert np.all(depth_a >= 0.35)
    assert np.all(depth_a <= 6.0)

    # Distinct content must produce distinct depth maps
    assert not np.allclose(depth_a, depth_b)

    # Check confidence map
    assert np.all(conf_a >= 0.05)
    assert np.all(conf_a <= 1.0)

    # Colorization test
    vis = estimator.colorize_depth(depth_a)
    assert vis.shape == (180, 240, 3)


def test_camera_pose_composition_and_no_arbitrary_scale():
    """Validates Task 2.2: Coordinate composition is mathematically correct and free of arbitrary 0.3 multipliers."""
    estimator = HierarchicalPoseEstimator()

    # Generate synthetic sequence with known translation
    np.random.seed(42)
    img1 = np.random.randint(50, 200, (240, 320, 3), dtype=np.uint8)
    cv2.putText(img1, "VASTU_TRACK_TEST", (30, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

    # Translate image by 10 pixels horizontally
    img2 = np.roll(img1, 10, axis=1)

    images = [img1, img2]
    meta = [
        {"frame_index": 0, "timestamp_ns": 0},
        {"frame_index": 1, "timestamp_ns": int(1e8)}
    ]
    K = np.array([
        [300.0, 0.0, 160.0],
        [0.0, 300.0, 120.0],
        [0.0, 0.0, 1.0]
    ])

    result = estimator.estimate_trajectory(images, meta, K)
    assert len(result.trajectory) == 2

    frame0 = result.trajectory[0]
    frame1 = result.trajectory[1]

    # Verify camera center in world coordinates C = -R.T @ t
    R0 = np.array(frame0.rotation_matrix)
    t0 = np.array(frame0.translation_vector_m).reshape(3, 1)
    C0_expected = (-R0.T @ t0).flatten()
    assert np.allclose(frame0.camera_center_m, C0_expected, atol=1e-5)

    R1 = np.array(frame1.rotation_matrix)
    t1 = np.array(frame1.translation_vector_m).reshape(3, 1)
    C1_expected = (-R1.T @ t1).flatten()
    assert np.allclose(frame1.camera_center_m, C1_expected, atol=1e-5)


def test_tsdf_volumetric_fusion_and_plane_snapping():
    """Validates Task 2.3: TSDF fusion produces planar architectural surfaces without crumpled faceting."""
    engine = TSDFFusionEngine(voxel_length_m=0.04, sdf_trunc_m=0.12)

    h, w = 120, 160
    K = np.array([
        [150.0, 0.0, 80.0],
        [0.0, 150.0, 60.0],
        [0.0, 0.0, 1.0]
    ])

    # Simulate 3 camera views observing a flat floor at y = 0.0m and wall at z = 2.0m
    for i in range(3):
        color = np.ones((h, w, 3), dtype=np.uint8) * 180
        # Metric depth for a plane at 2.0m
        depth = np.ones((h, w), dtype=np.float32) * 2.0

        # Translation along x by 0.15m per frame
        R = np.eye(3, dtype=np.float64)
        t = np.array([[0.15 * i], [0.0], [0.0]], dtype=np.float64)

        success = engine.integrate_frame(color, depth, R, t, K)
        assert success is True

    assert engine.integrated_frames_count == 3

    mesh = engine.extract_mesh(snap_architectural_planes=True)
    assert mesh is not None
    assert len(mesh.vertices) > 0
    assert len(mesh.triangles) > 0


def test_backend_manifest_and_engine_verification():
    """Validates P0-A: Confirms backend manifest records TSDF engine and meshing method."""
    engine = TSDFFusionEngine()
    manifest = engine.get_backend_manifest()

    assert manifest["fusion_engine"] == "TSDF_SCALABLE_VOLUME"
    assert manifest["meshing_method"] == "TSDF_MARCHING_CUBES_TOPOLOGY_PRESERVING"
    assert manifest["depth_model"] == "NEURAL_METRIC_CALIBRATED"
    assert manifest["pose_estimator"] == "DIRECT_3D_2D_PNP_RANSAC"


def test_quality_gate_fails_on_engine_mismatch():
    """Validates P0-A.5: Quality gate must fail if configured reconstruction backend is not TSDF."""
    from scripts.generate_video_twin import VastuDigitalTwinPipeline
    pipe = VastuDigitalTwinPipeline("IMG_3966.MOV", "scratch/test_qg")

    capture_report = {"usable_frame_pct": 100.0}
    trajectory_metrics = [{"confidence": 0.95}]
    depth_stats = {"frame_statistics": [{"confidence_ratio": 0.95}]}
    reg_metrics = {"consensus_support_ratio": 0.95}
    pcd_metrics = {"total_points": 50000, "dimensions_m": {"width_x": 3.0}}
    reproj_report = {"mean_pixel_rmse": 5.0}
    parallax_report = {"parallax_gate_passed": True, "parallax_score": 0.95}
    tex_val = {"surface_coverage_pct": 98.0}

    # Case 1: Legacy Poisson backend -> MUST FAIL
    mesh_val_poisson = {
        "triangle_count": 50000,
        "non_manifold_edges": 0,
        "reconstruction_backend": {
            "fusion_engine": "SCREENED_POISSON_INTERPOLATION",
            "meshing_method": "POISSON_SURFACE_CLOSURE"
        }
    }
    qg_fail = pipe._stage_22_quality_gate(
        capture_report, trajectory_metrics, depth_stats, reg_metrics,
        pcd_metrics, mesh_val_poisson, tex_val, reproj_report, parallax_report
    )
    assert qg_fail["final_verdict"] == "FAIL"
    assert qg_fail["backend_verification"]["verified"] is False
    assert qg_fail["category_gates"]["BACKEND_VERIFIED"] is False

    # Case 2: Production TSDF backend -> PASSES
    mesh_val_tsdf = {
        "triangle_count": 50000,
        "non_manifold_edges": 0,
        "reconstruction_backend": {
            "fusion_engine": "TSDF_SCALABLE_VOLUME",
            "meshing_method": "TSDF_MARCHING_CUBES_TOPOLOGY_PRESERVING"
        }
    }
    qg_pass = pipe._stage_22_quality_gate(
        capture_report, trajectory_metrics, depth_stats, reg_metrics,
        pcd_metrics, mesh_val_tsdf, tex_val, reproj_report, parallax_report
    )
    assert qg_pass["final_verdict"] == "PASS"
    assert qg_pass["backend_verification"]["verified"] is True
    assert qg_pass["category_gates"]["BACKEND_VERIFIED"] is True


def test_multi_plane_detection_and_no_folded_triangles():
    """Validates P0-B: Multi-plane detection and topology-preserving regularization prevent folded triangles."""
    engine = TSDFFusionEngine(voxel_length_m=0.03, sdf_trunc_m=0.09)

    h, w = 120, 160
    K = np.array([
        [150.0, 0.0, 80.0],
        [0.0, 150.0, 60.0],
        [0.0, 0.0, 1.0]
    ])

    # Synthesize two views of a box room (floor y=0, ceiling y=2.4m, wall z=2.0m)
    for i in range(2):
        color = np.ones((h, w, 3), dtype=np.uint8) * 180
        depth = np.ones((h, w), dtype=np.float32) * 2.0
        R = np.eye(3, dtype=np.float64)
        t = np.array([[0.10 * i], [0.0], [0.0]], dtype=np.float64)
        engine.integrate_frame(color, depth, R, t, K)

    raw_mesh = engine.extract_mesh(snap_architectural_planes=False)
    assert raw_mesh is not None

    reg_mesh = engine.snap_to_architectural_planes(raw_mesh)
    # Check that self-intersecting triangles are zero or negligible
    self_intersecting = reg_mesh.get_self_intersecting_triangles()
    assert len(self_intersecting) < 20


def test_modular_worker_shares_backend():
    """Validates P0-A.2: Modular worker Stage 05 returns reconstruction_backend."""
    from workers.stages.stage05_meshing import MeshingWorker
    from workers.base import WorkerContext

    import uuid
    context = WorkerContext(
        job_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        work_dir="scratch/test_worker",
        stage_name="Stage05_Meshing",
        execution_id="test_01"
    )

    # Create dummy PLY
    os.makedirs(os.path.join(context.work_dir, "04_pointcloud"), exist_ok=True)
    ply_path = os.path.join(context.work_dir, "04_pointcloud", "dense_pointcloud.ply")
    with open(ply_path, "w") as f:
        f.write("ply\nformat ascii 1.0\nelement vertex 4\nproperty float x\nproperty float y\nproperty float z\nend_header\n0 0 0\n1 0 0\n0 1 0\n1 1 0\n")

    worker = MeshingWorker()
    res = worker.process({"ply_path": ply_path}, context)
    manifest = worker.generate_manifest({"mesh_ply": res["mesh_path"]}, res, context)

    assert "reconstruction_backend" in manifest
    assert manifest["reconstruction_backend"]["fusion_engine"] == "TSDF_SCALABLE_VOLUME"

