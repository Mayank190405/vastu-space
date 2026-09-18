"""
VĀSTU Stage 02 Worker: Structure-from-Motion (SfM)
Hierarchical fusion of device AR/VIO, visual odometry, feature matching, and epipolar geometry.
Explicitly detects and flags tracking loss, low parallax, disconnected trajectories, and loop closure drift.
"""

import os
import json
from typing import Dict, Any, List
import cv2
import numpy as np
from workers.base import BaseWorker, WorkerContext
from core.tracking.fusion import HierarchicalPoseEstimator
from core.schemas.camera_poses import CameraPoses


class SfMWorker(BaseWorker):
    def __init__(self):
        super().__init__(stage_name="Stage02_SfM")
        self.estimator = HierarchicalPoseEstimator()

    def load_input(self, context: WorkerContext) -> Dict[str, Any]:
        keyframes_meta = os.path.join(context.work_dir, "01_keyframes", "frame_metadata.json")
        if not os.path.exists(keyframes_meta):
            keyframes_meta = os.path.join(context.work_dir, "01_preprocessing", "frame_manifest.json")

        if not os.path.exists(keyframes_meta):
            raise FileNotFoundError(f"Keyframe metadata not found: {keyframes_meta}")

        with open(keyframes_meta, "r") as f:
            metadata = json.load(f)

        if isinstance(metadata, dict) and "frames" in metadata:
            # Handle PreprocessingManifest format
            raw_frames = metadata["frames"]
            base_dir = os.path.join(context.work_dir, "01_preprocessing")
            keyframes = []
            for f_rec in raw_frames:
                if f_rec.get("is_keyframe", False):
                    k_file = f_rec.get("keyframe_filename", "")
                    keyframes.append({
                        "frame_index": f_rec["frame_index"],
                        "timestamp_ns": f_rec["timestamp_ns"],
                        "file_path": os.path.join(base_dir, k_file) if k_file else ""
                    })
        else:
            keyframes = [m for m in metadata if m.get("is_keyframe", True)]

        device_poses = context.params.get("device_poses")
        return {
            "keyframes": keyframes,
            "device_poses": device_poses
        }

    def validate_input(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        keyframes = raw_input.get("keyframes", [])
        if len(keyframes) < 2:
            raise ValueError(f"Insufficient keyframes ({len(keyframes)}) for SfM, minimum 2 required")
        for k in keyframes:
            if not os.path.exists(k["file_path"]):
                raise FileNotFoundError(f"Frame image missing: {k['file_path']}")
        return raw_input

    def process(self, validated_input: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        keyframes = validated_input["keyframes"]
        images = [cv2.imread(k["file_path"]) for k in keyframes]

        h, w = images[0].shape[:2]
        K = np.array([
            [1.2 * w, 0.0, w / 2.0],
            [0.0, 1.2 * w, h / 2.0],
            [0.0, 0.0, 1.0]
        ], dtype=np.float64)

        poses_contract: CameraPoses = self.estimator.estimate_trajectory(
            keyframe_images=images,
            keyframe_metadata=keyframes,
            intrinsics_k=K,
            device_vio_poses=validated_input.get("device_poses")
        )

        # Structure payload containing both full contract and backward-compatible poses alias
        output_dict = poses_contract.model_dump()
        output_dict["poses"] = [
            {
                "frame_index": f["frame_index"],
                "R": f["rotation_matrix"],
                "t": f["translation_vector_m"],
                "reprojection_error": f["reprojection_error_px"]
            }
            for f in output_dict["trajectory"]
        ]

        return {
            "camera_poses": output_dict,
            "poses_contract": poses_contract,
            "registered_count": len(poses_contract.trajectory),
            "unreliable_segments_count": len(poses_contract.unreliable_segments)
        }

    def generate_artifacts(self, processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, str]:
        sfm_dir = os.path.join(context.work_dir, "02_sfm")
        os.makedirs(sfm_dir, exist_ok=True)
        poses_path = os.path.join(sfm_dir, "camera_poses.json")
        with open(poses_path, "w") as f:
            json.dump(processed_data["camera_poses"], f, indent=2)
        return {"camera_poses": poses_path}

    def generate_manifest(self, artifacts: Dict[str, str], processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        return {
            "stage": self.stage_name,
            "registered_cameras": processed_data["registered_count"],
            "unreliable_segments_count": processed_data["unreliable_segments_count"],
            "artifacts": artifacts
        }

    def collect_metrics(self, processed_data: Dict[str, Any], elapsed_sec: float) -> Dict[str, Any]:
        return {
            "processing_time_sec": elapsed_sec,
            "registered_poses": processed_data["registered_count"],
            "unreliable_segments": processed_data["unreliable_segments_count"]
        }

