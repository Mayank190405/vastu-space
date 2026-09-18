"""
Unit & Integration Tests: Dense Reconstruction & Evidence Fusion (Stages 03 & 04)
Validates:
1. Multi-view depth consistency verification and disagreement detection
2. Dense evidence point cloud representation (point confidence, normals, observation traceability)
3. Volumetric density map computation
4. Defect detection: holes, isolated regions, floating geometry, excessive noise, inconsistent depth
5. DepthWorker and PointCloudWorker full lifecycle execution
"""

import os
import cv2
import json
import uuid
import pytest
import numpy as np

from core.dense.consistency import MultiViewDepthConsistency
from core.dense.evidence_fusion import DenseEvidenceFusion, DenseEvidencePoint
from core.dense.defect_detector import ReconstructionDefectDetector
from workers.stages.stage03_depth import DepthWorker
from workers.stages.stage04_pointcloud import PointCloudWorker
from workers.base import WorkerContext


def test_multi_view_depth_consistency():
    checker = MultiViewDepthConsistency(max_depth_discrepancy_ratio=0.10)
    K = np.array([[400.0, 0.0, 240.0], [0.0, 400.0, 180.0], [0.0, 0.0, 1.0]])

    # View 1 at origin (0, 0, 0) looking at a flat plane at z = 2.0m
    ref_depth = np.ones((120, 160), dtype=np.float32) * 2.0
    ref_R = np.eye(3)
    ref_t = np.zeros((3, 1))

    # View 2 slightly translated along x by 0.10m: plane depth should still be ~2.0m
    n_depth_agree = np.ones((120, 160), dtype=np.float32) * 2.002
    n_R = np.eye(3)
    n_t = np.array([[0.10], [0.0], [0.0]])

    mask, consensus, sources, stats = checker.verify_consistency(
        ref_depth=ref_depth,
        ref_R=ref_R,
        ref_t=ref_t,
        neighbor_depths=[n_depth_agree],
        neighbor_Rs=[n_R],
        neighbor_ts=[n_t],
        neighbor_frame_indices=[1],
        K=K,
        subsample_step=8
    )

    assert stats["consistent_pixels"] > 0
    assert stats["consistency_ratio"] > 0.80

    # Inconsistent depth: neighbor observes depth at 5.0m instead of 2.0m!
    n_depth_conflict = np.ones((120, 160), dtype=np.float32) * 5.0
    mask_bad, consensus_bad, _, stats_bad = checker.verify_consistency(
        ref_depth=ref_depth,
        ref_R=ref_R,
        ref_t=ref_t,
        neighbor_depths=[n_depth_conflict],
        neighbor_Rs=[n_R],
        neighbor_ts=[n_t],
        neighbor_frame_indices=[2],
        K=K,
        subsample_step=8
    )

    assert stats_bad["inconsistent_pixels"] > 0
    assert stats_bad["consistency_ratio"] == 0.0


def test_evidence_fusion_and_traceability():
    fusion = DenseEvidenceFusion(voxel_size_m=0.03)
    K = np.array([[400.0, 0.0, 120.0], [0.0, 400.0, 90.0], [0.0, 0.0, 1.0]])

    depth_map = np.ones((90, 120), dtype=np.float32) * 1.5
    consensus_map = np.ones((90, 120), dtype=np.int32) * 2
    rgb = np.ones((90, 120, 3), dtype=np.uint8) * 180

    kfs = [{"frame_index": 0}]
    poses = [{
        "frame_index": 0,
        "R": np.eye(3).tolist(),
        "t": [0.0, 0.0, 0.0]
    }]

    points = fusion.fuse_views(
        keyframe_records=kfs,
        consistent_depths=[depth_map],
        consensus_maps=[consensus_map],
        point_sources_list=[{(10, 10): [1, 2]}],
        rgb_images=[rgb],
        poses_trajectory=poses,
        K=K,
        step=4
    )

    assert len(points) > 0
    p0 = points[0]

    # Measurable confidence
    assert 0.0 < p0.confidence <= 1.0
    # Traceability: every point traces back to source observations
    assert len(p0.source_frames) >= 1
    assert 0 in p0.source_frames
    assert p0.position.shape == (3,)
    assert p0.normal.shape == (3,)


def test_density_map_and_defect_detection():
    fusion = DenseEvidenceFusion(voxel_size_m=0.03)
    detector = ReconstructionDefectDetector(outlier_std_ratio=1.5, min_cluster_size=20)

    # Synthetic dense planar wall + 1 floating outlier + 1 isolated small cluster
    pts = []
    # Main wall
    for x in np.linspace(-1.0, 1.0, 30):
        for y in np.linspace(-1.0, 1.0, 30):
            pts.append(DenseEvidencePoint(
                position=np.array([x, y, 2.0]),
                color=np.array([128, 128, 128], dtype=np.uint8),
                normal=np.array([0, 0, -1]),
                confidence=0.90,
                source_frames=[0, 1]
            ))

    # Floating outlier suspended at [10.0, 10.0, 10.0]
    pts.append(DenseEvidencePoint(
        position=np.array([10.0, 10.0, 10.0]),
        color=np.array([255, 0, 0], dtype=np.uint8),
        normal=np.array([0, 0, 1]),
        confidence=0.20,
        source_frames=[2]
    ))

    # Isolated tiny cluster (5 points) far away
    for i in range(5):
        pts.append(DenseEvidencePoint(
            position=np.array([-5.0 + i*0.01, -5.0, 2.0]),
            color=np.array([0, 255, 0], dtype=np.uint8),
            normal=np.array([0, 0, 1]),
            confidence=0.30,
            source_frames=[3]
        ))

    # Volumetric density map
    density_map = fusion.compute_density_map(pts, cell_size_m=0.50)
    assert density_map["total_occupied_cells"] >= 1
    assert density_map["mean_density_pts_m3"] > 0.0

    # Defect Audit
    audit = detector.audit_reconstruction(
        points=pts,
        consistency_stats={"total_tested_pixels": 1000, "inconsistent_pixels": 50}
    )

    defects = audit["defects_detected"]
    # Floating geometry detected
    assert defects["floating_geometry"]["count"] > 0
    # Isolated region detected
    assert defects["isolated_regions"]["count"] > 0
    # Consistency checked
    assert defects["inconsistent_depth"]["detected"] is False


def test_depth_and_pointcloud_workers_integration(tmp_path):
    # Setup working directory with keyframes and camera poses
    keyframes_dir = tmp_path / "01_keyframes"
    os.makedirs(keyframes_dir, exist_ok=True)

    sfm_dir = tmp_path / "02_sfm"
    os.makedirs(sfm_dir, exist_ok=True)

    keyframes = []
    poses = []
    for i in range(2):
        img_file = f"frame_{i:05d}.jpg"
        img_path = keyframes_dir / img_file
        # Write textured test image
        img = np.zeros((180, 240, 3), dtype=np.uint8)
        img[::10, :] = 200
        img[:, ::10] = 150
        cv2.imwrite(str(img_path), img)

        keyframes.append({
            "frame_index": i,
            "timestamp_ns": i * 100000000,
            "is_keyframe": True,
            "file_path": str(img_path)
        })
        poses.append({
            "frame_index": i,
            "R": np.eye(3).tolist(),
            "t": [i * 0.1, 0.0, 0.0],
            "camera_center_m": [i * 0.1, 0.0, 0.0]
        })

    with open(keyframes_dir / "frame_metadata.json", "w") as f:
        json.dump(keyframes, f, indent=2)

    with open(sfm_dir / "camera_poses.json", "w") as f:
        json.dump({
            "intrinsics": [300.0, 300.0, 120.0, 90.0],
            "poses": poses
        }, f, indent=2)

    ctx = WorkerContext(
        job_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        work_dir=str(tmp_path),
        params={}
    )

    # 1. Run DepthWorker
    depth_worker = DepthWorker()
    depth_res = depth_worker.execute(ctx)
    assert depth_res.status.value == "SUCCESS"
    assert "depth_manifest" in depth_res.artifacts
    assert "depth_confidence" in depth_res.artifacts
    assert os.path.exists(depth_res.artifacts["depth_confidence"])

    # 2. Run PointCloudWorker
    pcd_worker = PointCloudWorker()
    pcd_res = pcd_worker.execute(ctx)
    assert pcd_res.status.value == "SUCCESS"
    assert "pointcloud_ply" in pcd_res.artifacts
    assert "density_map" in pcd_res.artifacts
    assert "reconstruction_statistics" in pcd_res.artifacts

    ply_path = pcd_res.artifacts["pointcloud_ply"]
    stats_path = pcd_res.artifacts["reconstruction_statistics"]

    assert os.path.exists(ply_path)
    assert os.path.exists(stats_path)

    with open(stats_path, "r") as f:
        stats = json.load(f)

    assert "total_evidence_points" in stats
    assert "mean_point_confidence" in stats
    assert "defect_audit" in stats
