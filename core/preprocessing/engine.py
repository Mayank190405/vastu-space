"""
VĀSTU Preprocessing: Preprocessing Engine
Orchestrates video frame extraction, quality analysis, adaptive selection,
and outputs keyframes/, quality.json, and frame_manifest.json with 100% auditable discard reasons.
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
import cv2
import numpy as np

from core.schemas.preprocessing import (
    FrameQualityMetrics,
    FrameAuditRecord,
    PreprocessingQualityReport,
    PreprocessingManifest,
    SceneContextTag,
    FrameDiscardReason
)
from core.preprocessing.analyzer import FrameQualityAnalyzer
from core.preprocessing.selector import AdaptiveKeyframeSelector

logger = logging.getLogger("vastu.preprocessing.engine")


class PreprocessingEngine:
    """
    Production-grade preprocessing engine for indoor spatial reconstruction.
    """
    def __init__(
        self,
        analyzer: Optional[FrameQualityAnalyzer] = None,
        selector: Optional[AdaptiveKeyframeSelector] = None
    ):
        self.analyzer = analyzer or FrameQualityAnalyzer()
        self.selector = selector or AdaptiveKeyframeSelector()

    def process_video(
        self,
        video_path: str,
        output_dir: str,
        context_hints: Optional[Dict[int, List[SceneContextTag]]] = None,
        telemetry_motion_map: Optional[Dict[int, float]] = None
    ) -> Dict[str, Any]:
        """
        Executes end-to-end preprocessing on an input video file.
        Produces:
          - output_dir/keyframes/
          - output_dir/quality.json
          - output_dir/frame_manifest.json
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Failed to open video file: {video_path}")

        fps = float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
        total_frames_est = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration_sec = total_frames_est / max(1.0, fps)

        keyframes_dir = os.path.join(output_dir, "keyframes")
        os.makedirs(keyframes_dir, exist_ok=True)

        records: List[FrameAuditRecord] = []
        discard_counts: Dict[str, int] = {reason.value: 0 for reason in FrameDiscardReason}
        context_counts: Dict[str, int] = {}

        prev_gray: Optional[np.ndarray] = None
        frame_idx = 0
        all_sharpness = []
        all_feature_counts = []
        all_luminance = []

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret or frame is None:
                break

            timestamp_ns = int(frame_idx * (1e9 / max(1.0, fps)))

            # Step 1: Quality analysis
            metrics, gray = self.analyzer.analyze(frame, prev_gray=prev_gray)
            all_sharpness.append(metrics.sharpness_score)
            all_feature_counts.append(metrics.feature_count)
            all_luminance.append(metrics.mean_luminance)

            # Step 2: Context hints & Telemetry
            frame_hints = (context_hints or {}).get(frame_idx, [])
            motion_val = (telemetry_motion_map or {}).get(frame_idx, 0.0)

            # Step 3: Adaptive Keyframe Selection
            is_keyframe, discard_reason, assigned_tags = self.selector.evaluate_frame(
                frame_idx=frame_idx,
                metrics=metrics,
                context_hints=frame_hints,
                telemetry_motion=motion_val
            )

            for tag in assigned_tags:
                context_counts[tag.value] = context_counts.get(tag.value, 0) + 1

            keyframe_file = None
            if is_keyframe:
                filename = f"frame_{frame_idx:06d}.jpg"
                save_path = os.path.join(keyframes_dir, filename)
                cv2.imwrite(save_path, frame)
                keyframe_file = os.path.join("keyframes", filename)
                prev_gray = gray  # Update reference anchor for visual delta calculation
            else:
                if discard_reason is None:
                    # Enforce audit invariant: Discarded frame MUST have a reason
                    discard_reason = FrameDiscardReason.CADENCE_REDUNDANT
                discard_counts[discard_reason.value] += 1

            record = FrameAuditRecord(
                frame_index=frame_idx,
                timestamp_ns=timestamp_ns,
                is_keyframe=is_keyframe,
                discard_reason=discard_reason,
                quality_metrics=metrics,
                context_tags=assigned_tags,
                keyframe_filename=keyframe_file
            )
            records.append(record)
            frame_idx += 1

        cap.release()

        total_extracted = len(records)
        keyframes_selected = sum(1 for r in records if r.is_keyframe)
        total_discarded = total_extracted - keyframes_selected

        # Step 4: Compute overall quality score
        avg_sharpness = float(np.mean(all_sharpness)) if all_sharpness else 0.0
        avg_feats = float(np.mean(all_feature_counts)) if all_feature_counts else 0.0
        lum_std = float(np.std(all_luminance)) if all_luminance else 0.0
        exposure_stability = max(0.0, min(1.0, 1.0 - (lum_std / 128.0)))
        overall_score = max(0.0, min(1.0, (
            (min(1.0, avg_sharpness / 150.0) * 0.4) +
            (min(1.0, avg_feats / 300.0) * 0.3) +
            (exposure_stability * 0.3)
        )))

        # Step 5: Save quality.json
        quality_report = PreprocessingQualityReport(
            total_extracted_frames=total_extracted,
            total_keyframes_selected=keyframes_selected,
            total_frames_discarded=total_discarded,
            overall_quality_score=round(overall_score, 4),
            avg_sharpness=round(avg_sharpness, 2),
            avg_feature_count=round(avg_feats, 1),
            exposure_stability_score=round(exposure_stability, 4),
            discard_breakdown=discard_counts,
            context_tag_breakdown=context_counts
        )
        quality_path = os.path.join(output_dir, "quality.json")
        with open(quality_path, "w") as f:
            f.write(quality_report.model_dump_json(indent=2))

        # Step 6: Save frame_manifest.json
        manifest = PreprocessingManifest(
            video_path=video_path,
            video_fps=fps,
            video_duration_sec=duration_sec,
            resolution=[w, h],
            total_frames=total_extracted,
            keyframes_count=keyframes_selected,
            discarded_count=total_discarded,
            frames=records
        )
        manifest_path = os.path.join(output_dir, "frame_manifest.json")
        with open(manifest_path, "w") as f:
            f.write(manifest.model_dump_json(indent=2))

        logger.info(f"Preprocessing complete: {keyframes_selected}/{total_extracted} keyframes selected. Artifacts written to {output_dir}")
        return {
            "keyframes_dir": keyframes_dir,
            "quality_json": quality_path,
            "frame_manifest_json": manifest_path,
            "keyframes_count": keyframes_selected,
            "total_extracted": total_extracted
        }
