"""
VĀSTU Stage 03 Worker: Depth Estimation & Multi-View Consistency
Estimates metric depth maps and verifies geometric multi-view consistency across neighboring views.
Outputs depth_manifest.json and depth_confidence.json.
"""

import os
import json
from typing import Dict, Any, List
import cv2
import numpy as np
from workers.base import BaseWorker, WorkerContext
from ml.depth.estimator import DepthEstimator
from core.dense.consistency import MultiViewDepthConsistency


class DepthWorker(BaseWorker):
    def __init__(self):
        super().__init__(stage_name="Stage03_Depth")
        self.estimator = DepthEstimator()
        self.consistency_checker = MultiViewDepthConsistency()

    def load_input(self, context: WorkerContext) -> Dict[str, Any]:
        keyframes_meta = os.path.join(context.work_dir, "01_keyframes", "frame_metadata.json")
        poses_path = os.path.join(context.work_dir, "02_sfm", "camera_poses.json")
        if not os.path.exists(keyframes_meta) or not os.path.exists(poses_path):
            raise FileNotFoundError("Missing preceding stage inputs (keyframes or poses)")

        with open(keyframes_meta, "r") as f:
            metadata = json.load(f)
        with open(poses_path, "r") as f:
            poses_data = json.load(f)

        return {
            "metadata": metadata,
            "poses": poses_data.get("poses", []),
            "intrinsics": poses_data.get("intrinsics", [1400.0, 1400.0, 960.0, 540.0])
        }

    def validate_input(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        if not raw_input["poses"]:
            raise ValueError("No registered camera poses available for depth estimation")
        return raw_input

    def process(self, validated_input: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        depth_dir = os.path.join(context.work_dir, "03_depth")
        os.makedirs(depth_dir, exist_ok=True)

        depth_records = []
        raw_depth_maps = []
        loaded_keyframes = []

        # 1. Estimate initial depth maps
        for idx, k in enumerate(validated_input["metadata"]):
            if not k.get("is_keyframe", True):
                continue
            img_path = k["file_path"]
            if not os.path.exists(img_path):
                continue

            bgr = cv2.imread(img_path)
            depth_map, conf_map = self.estimator.estimate_depth(bgr)

            raw_depth_maps.append((k["frame_index"], depth_map, conf_map))
            loaded_keyframes.append(k)

        # 2. Multi-view depth consistency verification
        K = np.array([
            [validated_input["intrinsics"][0], 0.0, validated_input["intrinsics"][2]],
            [0.0, validated_input["intrinsics"][1], validated_input["intrinsics"][3]],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        pose_map = {p["frame_index"]: p for p in validated_input["poses"]}
        all_stats = []

        for idx, (f_idx, d_map, c_map) in enumerate(raw_depth_maps):
            ref_pose = pose_map.get(f_idx)
            if not ref_pose:
                continue

            ref_R = np.array(ref_pose["R"])
            ref_t = np.array(ref_pose["t"]).reshape(3, 1)

            # Find neighboring views
            n_depths, n_Rs, n_ts, n_fidxs = [], [], [], []
            for n_idx, (other_fidx, other_dmap, _) in enumerate(raw_depth_maps):
                if other_fidx != f_idx and other_fidx in pose_map:
                    other_pose = pose_map[other_fidx]
                    n_depths.append(other_dmap)
                    n_Rs.append(np.array(other_pose["R"]))
                    n_ts.append(np.array(other_pose["t"]).reshape(3, 1))
                    n_fidxs.append(other_fidx)

            consistent_mask, consensus_map, pt_sources, stats = self.consistency_checker.verify_consistency(
                ref_depth=d_map,
                ref_R=ref_R,
                ref_t=ref_t,
                neighbor_depths=n_depths[:4],  # Check up to 4 closest neighbors
                neighbor_Rs=n_Rs[:4],
                neighbor_ts=n_ts[:4],
                neighbor_frame_indices=n_fidxs[:4],
                K=K
            )
            all_stats.append(stats)

            d_filename = f"depth_{f_idx:05d}.npy"
            c_filename = f"conf_{f_idx:05d}.npy"
            cons_filename = f"consensus_{f_idx:05d}.npy"

            np.save(os.path.join(depth_dir, d_filename), d_map)
            np.save(os.path.join(depth_dir, c_filename), c_map)
            np.save(os.path.join(depth_dir, cons_filename), consensus_map)

            depth_records.append({
                "frame_index": f_idx,
                "depth_file": d_filename,
                "conf_file": c_filename,
                "consensus_file": cons_filename,
                "mean_depth_m": float(np.mean(d_map)),
                "mean_confidence": float(np.mean(c_map)),
                "consistency_ratio": stats.get("consistency_ratio", 1.0)
            })

        # Save depth confidence summary
        confidence_summary = {
            "total_frames_evaluated": len(depth_records),
            "mean_depth_consistency_ratio": round(float(np.mean([s["consistency_ratio"] for s in all_stats])) if all_stats else 1.0, 4),
            "frame_stats": depth_records
        }
        conf_summary_path = os.path.join(depth_dir, "depth_confidence.json")
        with open(conf_summary_path, "w") as f:
            json.dump(confidence_summary, f, indent=2)

        return {
            "depth_dir": depth_dir,
            "records": depth_records,
            "depth_confidence_json": conf_summary_path
        }

    def generate_artifacts(self, processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, str]:
        manifest_path = os.path.join(processed_data["depth_dir"], "depth_manifest.json")
        with open(manifest_path, "w") as f:
            json.dump(processed_data["records"], f, indent=2)
        return {
            "depth_dir": processed_data["depth_dir"],
            "depth_manifest": manifest_path,
            "depth_confidence": processed_data["depth_confidence_json"]
        }

    def generate_manifest(self, artifacts: Dict[str, str], processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        return {
            "stage": self.stage_name,
            "estimated_frames_count": len(processed_data["records"]),
            "artifacts": artifacts
        }

    def collect_metrics(self, processed_data: Dict[str, Any], elapsed_sec: float) -> Dict[str, Any]:
        return {
            "processing_time_sec": elapsed_sec,
            "depth_maps_generated": len(processed_data["records"])
        }

