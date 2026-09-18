"""
VĀSTU Stage 01 Worker: Preprocessing
Extracts video frames, performs blur, exposure, duplicate, and feature-density analysis,
and executes content-adaptive keyframe selection with 100% auditable discard reasons.
"""

import os
import json
from typing import Dict, Any, List
import cv2
from workers.base import BaseWorker, WorkerContext
from core.preprocessing.engine import PreprocessingEngine


class PreprocessingWorker(BaseWorker):
    def __init__(self):
        super().__init__(stage_name="Stage01_Preprocessing")
        self.engine = PreprocessingEngine()

    def load_input(self, context: WorkerContext) -> Dict[str, Any]:
        video_path = context.params.get("video_path")
        imu_path = context.params.get("imu_path")
        context_hints = context.params.get("context_hints")
        telemetry_motion = context.params.get("telemetry_motion")
        if not video_path or not os.path.exists(video_path):
            raise FileNotFoundError(f"Input video file not found: {video_path}")
        return {
            "video_path": video_path,
            "imu_path": imu_path,
            "context_hints": context_hints,
            "telemetry_motion": telemetry_motion
        }

    def validate_input(self, raw_input: Dict[str, Any]) -> Dict[str, Any]:
        cap = cv2.VideoCapture(raw_input["video_path"])
        if not cap.isOpened():
            raise ValueError(f"Cannot open video stream: {raw_input['video_path']}")
        fps = cap.get(cv2.CAP_PROP_FPS)
        count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()
        if count < 5:
            raise ValueError(f"Video too short ({count} frames), minimum 5 frames required")
        raw_input["fps"] = fps
        raw_input["frame_count"] = count
        return raw_input

    def process(self, validated_input: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        stage_dir = os.path.join(context.work_dir, "01_preprocessing")
        os.makedirs(stage_dir, exist_ok=True)

        res = self.engine.process_video(
            video_path=validated_input["video_path"],
            output_dir=stage_dir,
            context_hints=validated_input.get("context_hints"),
            telemetry_motion_map=validated_input.get("telemetry_motion")
        )
        return {
            "stage_dir": stage_dir,
            "keyframes_dir": res["keyframes_dir"],
            "quality_json": res["quality_json"],
            "frame_manifest_json": res["frame_manifest_json"],
            "keyframes_count": res["keyframes_count"],
            "total_extracted": res["total_extracted"]
        }

    def generate_artifacts(self, processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, str]:
        # Also copy / link frame_metadata.json into 01_keyframes for legacy stage compatibility if needed
        legacy_dir = os.path.join(context.work_dir, "01_keyframes")
        os.makedirs(legacy_dir, exist_ok=True)
        legacy_meta_path = os.path.join(legacy_dir, "frame_metadata.json")

        with open(processed_data["frame_manifest_json"], "r") as f:
            manifest_data = json.load(f)

        legacy_list = []
        for frame in manifest_data.get("frames", []):
            legacy_list.append({
                "frame_index": frame["frame_index"],
                "timestamp_ns": frame["timestamp_ns"],
                "exposure_time_sec": 0.016,
                "iso": 100,
                "focal_length_px": 1400.0,
                "laplacian_blur_score": frame["quality_metrics"]["sharpness_score"],
                "is_keyframe": frame["is_keyframe"],
                "is_blurry": frame["quality_metrics"]["sharpness_score"] < 40.0,
                "file_path": os.path.join(processed_data["stage_dir"], frame["keyframe_filename"]) if frame["keyframe_filename"] else ""
            })

        with open(legacy_meta_path, "w") as f:
            json.dump(legacy_list, f, indent=2)

        return {
            "keyframes_dir": processed_data["keyframes_dir"],
            "quality_json": processed_data["quality_json"],
            "frame_manifest": processed_data["frame_manifest_json"],
            "frame_metadata": legacy_meta_path
        }

    def generate_manifest(self, artifacts: Dict[str, str], processed_data: Dict[str, Any], context: WorkerContext) -> Dict[str, Any]:
        return {
            "stage": self.stage_name,
            "total_extracted_frames": processed_data["total_extracted"],
            "keyframe_count": processed_data["keyframes_count"],
            "artifacts": artifacts
        }

    def collect_metrics(self, processed_data: Dict[str, Any], elapsed_sec: float) -> Dict[str, Any]:
        return {
            "processing_time_sec": elapsed_sec,
            "total_frames": processed_data["total_extracted"],
            "keyframes": processed_data["keyframes_count"]
        }

