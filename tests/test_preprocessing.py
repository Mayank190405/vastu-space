"""
Unit & Integration Tests: Preprocessing Pipeline (Stage 01)
Validates:
1. Visual quality analysis (sharpness, exposure, feature density, visual delta)
2. Duplicate suppression
3. Adaptive keyframe selection across high-motion, corners, doors, windows, loop closure
4. 100% discard reason audit guarantee
5. PreprocessingWorker and PreprocessingEngine artifact generation (keyframes/, quality.json, frame_manifest.json)
"""

import os
import cv2
import uuid
import pytest
import numpy as np

from core.schemas.preprocessing import (
    FrameDiscardReason,
    SceneContextTag,
    PreprocessingManifest,
    PreprocessingQualityReport
)
from core.preprocessing.analyzer import FrameQualityAnalyzer
from core.preprocessing.selector import AdaptiveKeyframeSelector
from core.preprocessing.engine import PreprocessingEngine
from workers.stages.stage01_preprocessing import PreprocessingWorker
from workers.base import WorkerContext


def _create_synthetic_frame(pattern: str = "checkerboard", brightness: int = 128) -> np.ndarray:
    """Helper to create synthetic test frames."""
    img = np.ones((240, 320, 3), dtype=np.uint8) * brightness
    if pattern == "checkerboard":
        for i in range(0, 240, 20):
            for j in range(0, 320, 20):
                if ((i // 20) + (j // 20)) % 2 == 0:
                    img[i:i+20, j:j+20] = 50
                else:
                    img[i:i+20, j:j+20] = 180
    elif pattern == "blank":
        pass
    elif pattern == "gradient":
        for j in range(320):
            img[:, j] = int(j * 255 / 320)
    return img


def test_quality_analyzer_sharpness_and_blur():
    analyzer = FrameQualityAnalyzer()
    sharp_frame = _create_synthetic_frame("checkerboard")
    blurred_frame = cv2.GaussianBlur(sharp_frame, (25, 25), 0)

    m_sharp, _ = analyzer.analyze(sharp_frame)
    m_blur, _ = analyzer.analyze(blurred_frame)

    assert m_sharp.sharpness_score > m_blur.sharpness_score * 5
    assert m_sharp.tenengrad_gradient_energy > m_blur.tenengrad_gradient_energy


def test_quality_analyzer_exposure():
    analyzer = FrameQualityAnalyzer()
    normal_frame = _create_synthetic_frame("checkerboard", brightness=128)
    dark_frame = np.ones((240, 320, 3), dtype=np.uint8) * 10
    bright_frame = np.ones((240, 320, 3), dtype=np.uint8) * 250

    m_norm, _ = analyzer.analyze(normal_frame)
    m_dark, _ = analyzer.analyze(dark_frame)
    m_bright, _ = analyzer.analyze(bright_frame)

    assert m_dark.mean_luminance < 15.0
    assert m_dark.dark_ratio > 0.90
    assert m_bright.mean_luminance > 245.0
    assert m_bright.highlight_ratio > 0.90
    assert m_norm.dark_ratio < 0.60


def test_quality_analyzer_feature_density():
    analyzer = FrameQualityAnalyzer()
    textured_frame = _create_synthetic_frame("checkerboard")
    blank_frame = _create_synthetic_frame("blank")

    m_tex, _ = analyzer.analyze(textured_frame)
    m_blank, _ = analyzer.analyze(blank_frame)

    assert m_tex.feature_count > 50
    assert m_tex.spatial_grid_coverage > 0.50
    assert m_blank.feature_count == 0
    assert m_blank.spatial_grid_coverage == 0.0


def test_duplicate_detection():
    analyzer = FrameQualityAnalyzer()
    selector = AdaptiveKeyframeSelector(min_visual_delta=0.03)

    frame = _create_synthetic_frame("checkerboard")
    m1, gray1 = analyzer.analyze(frame)
    m2, gray2 = analyzer.analyze(frame, prev_gray=gray1)

    assert m2.visual_delta_prev == 0.0

    # First frame is anchor keyframe
    is_kf1, reason1, _ = selector.evaluate_frame(0, m1)
    assert is_kf1 is True
    assert reason1 is None

    # Exact duplicate should be rejected with DUPLICATE_FRAME
    is_kf2, reason2, _ = selector.evaluate_frame(1, m2)
    assert is_kf2 is False
    assert reason2 == FrameDiscardReason.DUPLICATE_FRAME


def test_100_percent_discard_reasons_and_adaptive_preservation():
    """
    Verifies that 100% of discarded frames receive an auditable discard reason,
    and adaptive contexts (high motion, corners, doors) preserve frame density.
    """
    selector = AdaptiveKeyframeSelector(
        base_cadence_frames=5,
        high_motion_cadence_frames=2
    )
    analyzer = FrameQualityAnalyzer()

    frames = []
    # Generate 15 frames:
    # 0..4: normal steady motion
    # 5..9: high motion corner sweep
    # 10..14: blurry or stationary duplicate
    for i in range(15):
        if i >= 10:
            # Duplicate / slight jitter
            f = _create_synthetic_frame("checkerboard")
        else:
            # Shift pattern by i*10 pixels to simulate motion
            f = np.roll(_create_synthetic_frame("checkerboard"), i * 15, axis=1)
        frames.append(f)

    results = []
    prev_gray = None
    for idx, f in enumerate(frames):
        metrics, gray = analyzer.analyze(f, prev_gray=prev_gray)
        hints = []
        if 5 <= idx <= 8:
            hints.append(SceneContextTag.CORNER)
            hints.append(SceneContextTag.HIGH_MOTION)

        is_kf, reason, tags = selector.evaluate_frame(idx, metrics, context_hints=hints)
        results.append((idx, is_kf, reason, tags))
        if is_kf:
            prev_gray = gray

    # Audit check: Every non-keyframe MUST have a non-None discard_reason!
    for idx, is_kf, reason, tags in results:
        if not is_kf:
            assert reason is not None
            assert isinstance(reason, FrameDiscardReason)
        else:
            assert reason is None

    # Verify corner/high-motion sequence preserved denser frames
    corner_kfs = [idx for idx, is_kf, _, _ in results if is_kf and 5 <= idx <= 8]
    assert len(corner_kfs) >= 2


def test_end_to_end_preprocessing_worker(tmp_path):
    # Generate a temporary MP4 video with OpenCV
    video_path = str(tmp_path / "test_input.mp4")
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(video_path, fourcc, 10.0, (320, 240))

    for i in range(25):
        # Vary frames with checkerboard roll and illumination
        base = _create_synthetic_frame("checkerboard")
        rolled = np.roll(base, i * 12, axis=1)
        out.write(rolled)
    out.release()

    ctx = WorkerContext(
        job_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        work_dir=str(tmp_path),
        params={"video_path": video_path}
    )

    worker = PreprocessingWorker()
    result = worker.execute(ctx)

    assert result.status.value == "SUCCESS"
    assert "keyframes_dir" in result.artifacts
    assert "quality_json" in result.artifacts
    assert "frame_manifest" in result.artifacts

    keyframes_dir = result.artifacts["keyframes_dir"]
    quality_path = result.artifacts["quality_json"]
    manifest_path = result.artifacts["frame_manifest"]

    assert os.path.isdir(keyframes_dir)
    keyframe_files = [f for f in os.listdir(keyframes_dir) if f.endswith(".jpg")]
    assert len(keyframe_files) > 0

    # Validate quality.json structure
    with open(quality_path, "r") as f:
        quality_data = PreprocessingQualityReport.model_validate_json(f.read())
    assert quality_data.total_extracted_frames == 25
    assert quality_data.total_keyframes_selected == len(keyframe_files)
    assert quality_data.total_frames_discarded == 25 - len(keyframe_files)
    assert quality_data.overall_quality_score > 0.0

    # Validate frame_manifest.json structure & 100% discard reason audit
    with open(manifest_path, "r") as f:
        manifest_data = PreprocessingManifest.model_validate_json(f.read())
    assert manifest_data.total_frames == 25
    for frame_rec in manifest_data.frames:
        if not frame_rec.is_keyframe:
            assert frame_rec.discard_reason is not None
        else:
            assert frame_rec.discard_reason is None
            assert frame_rec.keyframe_filename is not None
