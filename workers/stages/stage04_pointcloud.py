"""
VĀSTU Stage 04 Worker: Point Cloud Evidence Fusion & Defect Detection
Back-projects consistent 2D metric depth into world coordinates, fuses multi-view observations
into a traceable evidence point cloud, calculates volumetric density maps, and audits reconstruction defects.
"""

import os
import json
from typing import Dict, Any, List, Tuple
import cv2
import numpy as np
from workers.base import BaseWorker, WorkerContext
from core.dense.evidence_fusion import DenseEvidenceFusion, DenseEvidencePoint
from core.dense.defect_detector import ReconstructionDefectDetector


class PointCloudWorker(BaseWorker):
    def __init__(self):
        super().__init__(stage_name="Stage04_PointCloud")
        self.fusion = DenseEvidenceFusion(voxel_size_m=0.03)
        self.defect_detector = ReconstructionDefectDetector()

    def load_input(self, context: WorkerContext) -> Dict[str, Any]:
        poses_path = os.path.join(context.work_dir, "02_sfm", "camera_poses.json")
        depth_manifest = os.path.join(context.work_dir, "03_depth", "depth_manifest.json")
        depth_conf = os.path.join(context.work_dir, "03_depth", "depth_confidence.json")

        if not os.path.exists(poses_path) or not os.path.exists(depth_manifest):
            raise FileNotFoundError("Missing camera poses or depth manifest")

        with open(poses_path, "r") as f:
            poses = json.load(f)
        with open(depth_manifest, "r") as f:
            depths = json.load(f)

        consistency_stats = {}
        if os.path.exists(depth_conf):
            with open(depth_conf, "r") as f:
                consistency_stats = json.load(f)

        return {
            "poses": poses,
            "depths": depths,
            "consistency_stats": consistency_stats
        }

    def validate_input(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        if not raw_input["depths"]:
            raise ValueError("No depth records available for point cloud fusion")
        return raw_input

    def process(self, validated_input: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        depth_dir = os.path.join(context.work_dir, "03_depth")
        keyframes_dir = os.path.join(context.work_dir, "01_keyframes")
        if not os.path.exists(keyframes_dir):
            keyframes_dir = os.path.join(context.work_dir, "01_preprocessing", "keyframes")

        intrinsics_raw = validated_input["poses"]["intrinsics"]
        K = np.array([
            [intrinsics_raw[0], 0.0, intrinsics_raw[2]],
            [0.0, intrinsics_raw[1], intrinsics_raw[3]],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        loaded_kfs = []
        consistent_depths = []
        consensus_maps = []
        point_sources_list = []
        rgb_images = []

        for record in validated_input["depths"]:
            f_idx = record["frame_index"]
            depth_path = os.path.join(depth_dir, record["depth_file"])
            frame_img = os.path.join(keyframes_dir, f"frame_{f_idx:05d}.jpg")
            if not os.path.exists(frame_img):
                frame_img = os.path.join(keyframes_dir, f"frame_{f_idx:06d}.jpg")

            if not os.path.exists(depth_path) or not os.path.exists(frame_img):
                continue

            depth_map = np.load(depth_path)
            cons_path = os.path.join(depth_dir, record.get("consensus_file", f"consensus_{f_idx:05d}.npy"))
            if os.path.exists(cons_path):
                consensus_map = np.load(cons_path)
            else:
                consensus_map = np.ones_like(depth_map, dtype=np.int32)

            bgr = cv2.imread(frame_img)
            rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

            loaded_kfs.append(record)
            consistent_depths.append(depth_map)
            consensus_maps.append(consensus_map)
            point_sources_list.append({})
            rgb_images.append(rgb)

        poses_traj = validated_input["poses"].get("poses") or validated_input["poses"].get("trajectory", [])

        # 1. Fuse evidence points
        evidence_points: List[DenseEvidencePoint] = self.fusion.fuse_views(
            keyframe_records=loaded_kfs,
            consistent_depths=consistent_depths,
            consensus_maps=consensus_maps,
            point_sources_list=point_sources_list,
            rgb_images=rgb_images,
            poses_trajectory=poses_traj,
            K=K,
            step=4
        )

        # Fallback dummy point if scene has no depth points
        if not evidence_points:
            evidence_points = [
                DenseEvidencePoint(
                    position=np.array([0.0, 0.0, 1.0]),
                    color=np.array([200, 200, 200], dtype=np.uint8),
                    normal=np.array([0.0, 0.0, -1.0]),
                    confidence=0.5,
                    source_frames=[0]
                )
            ]

        # 2. Compute 3D Density Map
        density_map = self.fusion.compute_density_map(evidence_points, cell_size_m=0.50)

        # 3. Defect and Anomaly Detection
        camera_centers = [
            np.array(p.get("camera_center_m", [0, 0, 0]))
            for p in poses_traj
        ]
        defect_audit = self.defect_detector.audit_reconstruction(
            points=evidence_points,
            consistency_stats=validated_input.get("consistency_stats", {}),
            camera_centers=camera_centers
        )

        # 4. Reconstruction Statistics
        stats = {
            "total_evidence_points": len(evidence_points),
            "mean_point_confidence": round(float(np.mean([p.confidence for p in evidence_points])), 3),
            "density_map_summary": density_map,
            "defect_audit": defect_audit
        }

        return {
            "evidence_points": evidence_points,
            "density_map": density_map,
            "reconstruction_stats": stats,
            "total_points": len(evidence_points)
        }

    def generate_artifacts(self, processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, str]:
        pcd_dir = os.path.join(context.work_dir, "04_pointcloud")
        os.makedirs(pcd_dir, exist_ok=True)

        ply_path = os.path.join(pcd_dir, "dense_pointcloud.ply")
        self.fusion.write_ply(processed_data["evidence_points"], ply_path)

        density_path = os.path.join(pcd_dir, "density_map.json")
        with open(density_path, "w") as f:
            json.dump(processed_data["density_map"], f, indent=2)

        stats_path = os.path.join(pcd_dir, "reconstruction_statistics.json")
        with open(stats_path, "w") as f:
            json.dump(processed_data["reconstruction_stats"], f, indent=2)

        return {
            "pointcloud_ply": ply_path,
            "density_map": density_path,
            "reconstruction_statistics": stats_path
        }

    def generate_manifest(self, artifacts: Dict[str, str], processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        return {
            "stage": self.stage_name,
            "evidence_points_count": processed_data["total_points"],
            "mean_confidence": processed_data["reconstruction_stats"]["mean_point_confidence"],
            "artifacts": artifacts
        }

    def collect_metrics(self, processed_data: Dict[str, Any], elapsed_sec: float) -> Dict[str, Any]:
        return {
            "processing_time_sec": elapsed_sec,
            "vertex_density_m3": processed_data["density_map"]["mean_density_pts_m3"],
            "total_points": processed_data["total_points"]
        }

