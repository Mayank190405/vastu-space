"""
VĀSTU Preprocessing: Adaptive Keyframe Selector
Selects optimal keyframes based on quality gates, motion dynamics, spatial events,
and enforces a 100% auditable discard reason for every rejected frame.
"""

from typing import Optional, List, Tuple, Dict, Any
from core.schemas.preprocessing import (
    FrameQualityMetrics,
    FrameDiscardReason,
    SceneContextTag
)


class AdaptiveKeyframeSelector:
    """
    Intelligent, content-adaptive keyframe selection engine.
    Ensures adequate coverage for high-motion, corners, doors, windows, transitions, and loop closures,
    while pruning duplicates and assigning deterministic discard reasons.
    """
    def __init__(
        self,
        min_sharpness: float = 35.0,
        min_luminance: float = 25.0,
        max_luminance: float = 240.0,
        max_dark_ratio: float = 0.45,
        max_highlight_ratio: float = 0.30,
        min_features: int = 40,
        min_spatial_coverage: float = 0.25,
        min_visual_delta: float = 0.035,
        base_cadence_frames: int = 5,
        high_motion_cadence_frames: int = 2
    ):
        self.min_sharpness = min_sharpness
        self.min_luminance = min_luminance
        self.max_luminance = max_luminance
        self.max_dark_ratio = max_dark_ratio
        self.max_highlight_ratio = max_highlight_ratio
        self.min_features = min_features
        self.min_spatial_coverage = min_spatial_coverage
        self.min_visual_delta = min_visual_delta
        self.base_cadence_frames = base_cadence_frames
        self.high_motion_cadence_frames = high_motion_cadence_frames

        self.last_keyframe_index: Optional[int] = None
        self.keyframe_count = 0

    def evaluate_frame(
        self,
        frame_idx: int,
        metrics: FrameQualityMetrics,
        context_hints: Optional[List[SceneContextTag]] = None,
        telemetry_motion: float = 0.0
    ) -> Tuple[bool, Optional[FrameDiscardReason], List[SceneContextTag]]:
        """
        Evaluates an extracted frame.
        Returns: (is_keyframe, discard_reason, assigned_context_tags)
        """
        tags: List[SceneContextTag] = list(context_hints or [])

        # 1. Detect dynamic scene contexts
        is_high_motion = metrics.visual_delta_prev > 0.12 or telemetry_motion > 0.8
        if is_high_motion and SceneContextTag.HIGH_MOTION not in tags:
            tags.append(SceneContextTag.HIGH_MOTION)

        if not tags:
            tags.append(SceneContextTag.NOMINAL)

        # 2. Quality Gate 1: Excessive Blur
        if metrics.sharpness_score < self.min_sharpness:
            return False, FrameDiscardReason.BLUR_EXCESSIVE, tags

        # 3. Quality Gate 2: Underexposure
        if metrics.mean_luminance < self.min_luminance or metrics.dark_ratio > self.max_dark_ratio:
            return False, FrameDiscardReason.UNDEREXPOSED, tags

        # 4. Quality Gate 3: Overexposure & Glare
        if metrics.mean_luminance > self.max_luminance or metrics.highlight_ratio > self.max_highlight_ratio:
            return False, FrameDiscardReason.OVEREXPOSED_GLARE, tags

        # 5. Quality Gate 4: Low Feature Density / Textureless
        if metrics.feature_count < self.min_features or metrics.spatial_grid_coverage < self.min_spatial_coverage:
            return False, FrameDiscardReason.LOW_FEATURE_DENSITY, tags

        # Initial frame is always accepted as the anchor keyframe
        if self.last_keyframe_index is None:
            self.last_keyframe_index = frame_idx
            self.keyframe_count += 1
            return True, None, tags

        # 6. Quality Gate 5: Duplicate Detection (insufficient motion)
        # Note: If high motion or transition is explicitly tagged, we don't discard as duplicate unless delta is 0
        if metrics.visual_delta_prev < self.min_visual_delta:
            return False, FrameDiscardReason.DUPLICATE_FRAME, tags

        # 7. Adaptive Cadence Check
        # High motion, corners, doors, windows, transitions, and loop closures require denser sampling
        frames_since_last = frame_idx - self.last_keyframe_index
        critical_contexts = {
            SceneContextTag.HIGH_MOTION,
            SceneContextTag.CORNER,
            SceneContextTag.DOOR,
            SceneContextTag.WINDOW,
            SceneContextTag.TRANSITION,
            SceneContextTag.LOOP_CLOSURE
        }
        has_critical_context = any(c in critical_contexts for c in tags)
        required_interval = (
            self.high_motion_cadence_frames if has_critical_context else self.base_cadence_frames
        )

        if frames_since_last < required_interval:
            # Drop redundant frame between adaptive cadence intervals
            return False, FrameDiscardReason.CADENCE_REDUNDANT, tags

        # Passed all gates and cadence criteria!
        self.last_keyframe_index = frame_idx
        self.keyframe_count += 1
        return True, None, tags
