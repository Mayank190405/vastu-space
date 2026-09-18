#!/usr/bin/env python3
"""
VĀSTU Spatial Reconstruction Engine - Point 17: Video Preprocessing
Extracts quality-validated frames, filters blur/exposure artifacts,
selects optimal keyframes, interpolates synchronized IMU odometry,
and outputs standardized camera calibration packages for SfM & Gaussian Splatting.
"""

import os
import sys
import json
import csv
import math
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2

class FrameQualityMetrics:
    def __init__(
        self,
        frame_index: int,
        timestamp_ns: int,
        blur_score: float,
        mean_luminance: float,
        feature_count: int,
        is_keyframe: bool,
        quality_status: str,
        file_name: str
    ):
        self.frame_index = frame_index
        self.timestamp_ns = timestamp_ns
        self.blur_score = blur_score
        self.mean_luminance = mean_luminance
        self.feature_count = feature_count
        self.is_keyframe = is_keyframe
        self.quality_status = quality_status
        self.file_name = file_name

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_index": self.frame_index,
            "timestamp_ns": self.timestamp_ns,
            "blur_score": round(self.blur_score, 2),
            "mean_luminance": round(self.mean_luminance, 2),
            "feature_count": self.feature_count,
            "is_keyframe": self.is_keyframe,
            "quality_status": self.quality_status,
            "file_name": self.file_name
        }

class VideoPreprocessor:
    def __init__(
        self,
        min_blur_threshold: float = 60.0,
        min_luminance: float = 25.0,
        max_luminance: float = 230.0,
        min_features: int = 120,
        target_keyframe_fps: float = 4.0
    ):
        self.min_blur_threshold = min_blur_threshold
        self.min_luminance = min_luminance
        self.max_luminance = max_luminance
        self.min_features = min_features
        self.target_keyframe_fps = target_keyframe_fps
        self.orb_detector = cv2.ORB_create(nfeatures=1000)

    def evaluate_frame_quality(self, frame_bgr: np.ndarray) -> Tuple[float, float, int, str]:
        """
        Calculates blur variance, exposure level, and ORB feature count.
        """
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)

        # 1. Blur evaluation via Laplacian variance
        laplacian = cv2.Laplacian(gray, cv2.CV_64F)
        blur_score = float(laplacian.var())

        # 2. Exposure evaluation
        mean_luminance = float(np.mean(gray))

        # 3. Feature density evaluation via ORB keypoints
        keypoints = self.orb_detector.detect(gray, None)
        feature_count = len(keypoints)

        # 4. Quality classification (exposure first, then blur, then features)
        if mean_luminance < self.min_luminance:
            status = "UNDEREXPOSED"
        elif mean_luminance > self.max_luminance:
            status = "OVEREXPOSED"
        elif blur_score < self.min_blur_threshold:
            status = "BLURRY"
        elif feature_count < self.min_features:
            status = "LOW_FEATURE_DENSITY"
        else:
            status = "VALID"

        return blur_score, mean_luminance, feature_count, status

    def load_imu_stream(self, imu_csv_path: str) -> List[Dict[str, Any]]:
        """
        Loads and parses IMU CSV telemetry.
        """
        imu_samples = []
        if not os.path.exists(imu_csv_path):
            return imu_samples

        with open(imu_csv_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            for row in reader:
                if len(row) >= 6:
                    try:
                        ts_ns = int(row[0].strip())
                        s_type = row[1].strip()
                        x = float(row[2].strip())
                        y = float(row[3].strip())
                        z = float(row[4].strip())
                        acc = int(row[5].strip()) if len(row) > 5 and row[5].strip().isdigit() else 3
                        imu_samples.append({
                            "timestamp_ns": ts_ns,
                            "sensor_type": s_type,
                            "x": x,
                            "y": y,
                            "z": z,
                            "accuracy": acc
                        })
                    except ValueError:
                        continue
        return imu_samples

    def interpolate_imu_at_timestamp(
        self,
        target_timestamp_ns: int,
        imu_samples: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Performs linear interpolation of accelerometer and gyroscope at frame timestamp.
        """
        if not imu_samples:
            return {
                "accel": [0.0, 9.81, 0.0],
                "gyro": [0.0, 0.0, 0.0],
                "time_difference_ns": 0
            }

        accel_samples = [s for s in imu_samples if "ACCEL" in s["sensor_type"].upper()]
        gyro_samples = [s for s in imu_samples if "GYRO" in s["sensor_type"].upper()]

        def interp_sensor(samples: List[Dict[str, Any]]) -> Tuple[List[float], int]:
            if not samples:
                return [0.0, 0.0, 0.0], 0
            # Find nearest or bracket
            samples.sort(key=lambda s: s["timestamp_ns"])
            if target_timestamp_ns <= samples[0]["timestamp_ns"]:
                s = samples[0]
                return [s["x"], s["y"], s["z"]], abs(s["timestamp_ns"] - target_timestamp_ns)
            if target_timestamp_ns >= samples[-1]["timestamp_ns"]:
                s = samples[-1]
                return [s["x"], s["y"], s["z"]], abs(s["timestamp_ns"] - target_timestamp_ns)

            for i in range(len(samples) - 1):
                t1 = samples[i]["timestamp_ns"]
                t2 = samples[i + 1]["timestamp_ns"]
                if t1 <= target_timestamp_ns <= t2:
                    factor = (target_timestamp_ns - t1) / float(t2 - t1) if t2 > t1 else 0.0
                    x = samples[i]["x"] + factor * (samples[i + 1]["x"] - samples[i]["x"])
                    y = samples[i]["y"] + factor * (samples[i + 1]["y"] - samples[i]["y"])
                    z = samples[i]["z"] + factor * (samples[i + 1]["z"] - samples[i]["z"])
                    return [round(x, 4), round(y, 4), round(z, 4)], 0
            s = samples[-1]
            return [s["x"], s["y"], s["z"]], 0

        accel_vec, dt_a = interp_sensor(accel_samples)
        gyro_vec, dt_g = interp_sensor(gyro_samples)

        return {
            "accel": accel_vec,
            "gyro": gyro_vec,
            "time_difference_ns": max(dt_a, dt_g)
        }

    def process_capture(
        self,
        video_path: str,
        imu_path: str,
        sync_manifest_path: str,
        output_dir: str
    ) -> Dict[str, Any]:
        """
        Executes full preprocessing pipeline: frame extraction, quality scoring,
        keyframe selection, IMU synchronization, and calibration generation.
        """
        os.makedirs(output_dir, exist_ok=True)
        frames_dir = os.path.join(output_dir, "frames")
        keyframes_dir = os.path.join(output_dir, "keyframes")
        os.makedirs(frames_dir, exist_ok=True)
        os.makedirs(keyframes_dir, exist_ok=True)

        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video container: {video_path}")

        total_video_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_ms = (total_video_frames / video_fps) * 1000.0 if video_fps > 0 else 0.0

        # Load Sync Manifest and IMU Stream
        imu_samples = self.load_imu_stream(imu_path)
        sync_manifest = {}
        video_start_ns = 0
        if os.path.exists(sync_manifest_path):
            try:
                with open(sync_manifest_path, "r", encoding="utf-8") as f:
                    sync_manifest = json.load(f)
                    if "frameAssociations" in sync_manifest and len(sync_manifest["frameAssociations"]) > 0:
                        video_start_ns = sync_manifest["frameAssociations"][0].get("frameTimestampNs", 0)
            except Exception:
                pass

        if video_start_ns == 0 and imu_samples:
            video_start_ns = imu_samples[0]["timestamp_ns"]

        frame_interval_ns = int((1.0 / video_fps) * 1_000_000_000)
        keyframe_step = max(1, int(video_fps / self.target_keyframe_fps))

        frame_metrics_list: List[FrameQualityMetrics] = []
        keyframe_manifest: List[Dict[str, Any]] = []

        frame_idx = 0
        valid_frames_count = 0
        blurry_frames_count = 0
        keyframes_count = 0

        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            current_timestamp_ns = video_start_ns + (frame_idx * frame_interval_ns)
            blur_score, mean_lum, feat_count, status = self.evaluate_frame_quality(frame)

            # Determine if candidate for keyframe
            is_keyframe = False
            if status == "VALID" and (frame_idx % keyframe_step == 0):
                is_keyframe = True
                keyframes_count += 1

            if status == "VALID":
                valid_frames_count += 1
            elif status == "BLURRY":
                blurry_frames_count += 1

            frame_filename = f"frame_{frame_idx:06d}.jpg"
            frame_path = os.path.join(frames_dir, frame_filename)
            cv2.imwrite(frame_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 92])

            metric = FrameQualityMetrics(
                frame_index=frame_idx,
                timestamp_ns=current_timestamp_ns,
                blur_score=blur_score,
                mean_luminance=mean_lum,
                feature_count=feat_count,
                is_keyframe=is_keyframe,
                quality_status=status,
                file_name=frame_filename
            )
            frame_metrics_list.append(metric)

            if is_keyframe:
                keyframe_filename = f"keyframe_{keyframes_count:06d}.jpg"
                keyframe_path = os.path.join(keyframes_dir, keyframe_filename)
                cv2.imwrite(keyframe_path, frame, [cv2.IMWRITE_JPEG_QUALITY, 96])

                # Interpolate IMU telemetry for this keyframe
                synced_imu = self.interpolate_imu_at_timestamp(current_timestamp_ns, imu_samples)

                keyframe_manifest.append({
                    "keyframe_id": keyframes_count,
                    "original_frame_index": frame_idx,
                    "timestamp_ns": current_timestamp_ns,
                    "file_name": keyframe_filename,
                    "blur_score": round(blur_score, 2),
                    "mean_luminance": round(mean_lum, 2),
                    "feature_count": feat_count,
                    "imu": synced_imu
                })

            frame_idx += 1

        cap.release()

        # Build Calibration Parameters Matrix K
        # fx = (width / 2) / tan(fov/2) approx or default 58 deg FOV
        fx = (width / 2.0) / math.tan(math.radians(58.0 / 2.0))
        fy = fx
        cx = width / 2.0
        cy = height / 2.0

        calibration_data = {
            "camera_model": "PINHOLE_RADIAL",
            "image_width": width,
            "image_height": height,
            "intrinsics": {
                "fx": round(fx, 4),
                "fy": round(fy, 4),
                "cx": round(cx, 4),
                "cy": round(cy, 4)
            },
            "intrinsic_matrix": [
                [round(fx, 4), 0.0, round(cx, 4)],
                [0.0, round(fy, 4), round(cy, 4)],
                [0.0, 0.0, 1.0]
            ],
            "distortion_coefficients": [0.0, 0.0, 0.0, 0.0],
            "coordinate_system": "OPENCV_RDF (X-right, Y-down, Z-forward)"
        }

        # Write Output Artifacts
        calibration_path = os.path.join(output_dir, "calibration.json")
        with open(calibration_path, "w", encoding="utf-8") as f:
            json.dump(calibration_data, f, indent=2)

        manifest_data = {
            "video_metadata": {
                "total_frames": frame_idx,
                "fps": video_fps,
                "width": width,
                "height": height,
                "duration_ms": round(duration_ms, 2)
            },
            "preprocessing_summary": {
                "total_extracted_frames": frame_idx,
                "valid_frames": valid_frames_count,
                "blurry_frames": blurry_frames_count,
                "selected_keyframes": keyframes_count,
                "keyframe_sampling_hz": self.target_keyframe_fps
            },
            "calibration": calibration_data,
            "keyframes": keyframe_manifest
        }

        manifest_path = os.path.join(output_dir, "preprocessing_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        quality_report = {
            "usable_frames_percentage": round((valid_frames_count / max(1, frame_idx)) * 100, 2),
            "keyframes_selected": keyframes_count,
            "average_blur_score": round(float(np.mean([m.blur_score for m in frame_metrics_list])) if frame_metrics_list else 0.0, 2),
            "average_feature_count": int(np.mean([m.feature_count for m in frame_metrics_list])) if frame_metrics_list else 0,
            "overall_capture_quality": "HIGH" if (valid_frames_count / max(1, frame_idx)) > 0.75 else "MEDIUM"
        }

        quality_report_path = os.path.join(output_dir, "quality_report.json")
        with open(quality_report_path, "w", encoding="utf-8") as f:
            json.dump(quality_report, f, indent=2)

        return manifest_data


if __name__ == "__main__":
    if len(sys.argv) < 5:
        print("Usage: python video_preprocessor.py <video_path> <imu_path> <sync_manifest_path> <output_dir>")
        sys.exit(1)

    v_path = sys.argv[1]
    i_path = sys.argv[2]
    s_path = sys.argv[3]
    o_dir = sys.argv[4]

    preprocessor = VideoPreprocessor()
    try:
        res = preprocessor.process_capture(v_path, i_path, s_path, o_dir)
        print(f"SUCCESS: Preprocessed {res['preprocessing_summary']['total_extracted_frames']} frames -> {res['preprocessing_summary']['selected_keyframes']} keyframes.")
    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        sys.exit(1)
