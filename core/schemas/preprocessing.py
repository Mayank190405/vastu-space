"""
VĀSTU Preprocessing Schemas
Formal contracts for video frame extraction, quality scoring, duplicate suppression,
adaptive keyframe selection, and 100% auditable frame discard reasons.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FrameDiscardReason(str, Enum):
    """Deterministic, auditable reason why an extracted frame was not chosen as a keyframe."""
    DUPLICATE_FRAME = "DUPLICATE_FRAME"              # Insufficient visual delta/motion
    BLUR_EXCESSIVE = "BLUR_EXCESSIVE"                # Laplacian / high-frequency sharpness below threshold
    UNDEREXPOSED = "UNDEREXPOSED"                    # Excessive dark pixels / low mean luminance
    OVEREXPOSED_GLARE = "OVEREXPOSED_GLARE"          # Highlight clipping / glare saturation
    LOW_FEATURE_DENSITY = "LOW_FEATURE_DENSITY"      # Insufficient trackable keypoints across spatial grid
    CADENCE_REDUNDANT = "CADENCE_REDUNDANT"          # Temporal pacing budget during smooth stationary motion
    ROLLING_SHUTTER_DISTORTION = "ROLLING_SHUTTER_DISTORTION"  # Severe angular velocity causing wall curvature
    UNRECOVERABLE_MOTION_BLUR = "UNRECOVERABLE_MOTION_BLUR"    # Motion blur lacking recoverable gradient signal
    FLOW_WARP_VIOLATION = "FLOW_WARP_VIOLATION"                # Asymmetrical optical flow warp failing physical sanity


class SceneContextTag(str, Enum):
    """Spatial and camera trajectory event tags requiring frame preservation."""
    HIGH_MOTION = "HIGH_MOTION"                      # High angular or linear velocity requiring dense overlap
    CORNER = "CORNER"                                # 45-degree corner sweep / directional pivot
    DOOR = "DOOR"                                    # Doorway threshold, jamb or entry boundary
    WINDOW = "WINDOW"                                # Window opening, glazing boundary, or high-contrast aperture
    TRANSITION = "TRANSITION"                        # Transition between rooms or distinct spatial zones
    LOOP_CLOSURE = "LOOP_CLOSURE"                    # Returning to origin/earlier scan position
    NOMINAL = "NOMINAL"                              # Standard steady-state scanning


class FrameQualityMetrics(BaseModel):
    """Quantitative quality measurements for a single frame."""
    sharpness_score: float = Field(ge=0.0, description="Laplacian variance sharpness metric")
    tenengrad_gradient_energy: float = Field(ge=0.0, description="Sobel gradient magnitude energy")
    mean_luminance: float = Field(ge=0.0, le=255.0, description="Average grayscale brightness")
    dark_ratio: float = Field(ge=0.0, le=1.0, description="Fraction of pixels below shadow cutoff (<15)")
    highlight_ratio: float = Field(ge=0.0, le=1.0, description="Fraction of pixels saturated (>245)")
    feature_count: int = Field(ge=0, description="Number of detected trackable 2D keypoints")
    spatial_grid_coverage: float = Field(ge=0.0, le=1.0, description="Fraction of 4x4 spatial cells with features")
    visual_delta_prev: float = Field(ge=0.0, description="L1 normalized visual delta from previous candidate")


class FrameAuditRecord(BaseModel):
    """Full audit record for an extracted frame in the video stream."""
    frame_index: int = Field(ge=0)
    timestamp_ns: int = Field(ge=0)
    is_keyframe: bool
    discard_reason: Optional[FrameDiscardReason] = None
    quality_metrics: FrameQualityMetrics
    context_tags: List[SceneContextTag] = Field(default_factory=list)
    keyframe_filename: Optional[str] = None


class PreprocessingQualityReport(BaseModel):
    """Composite quality audit summary saved as quality.json."""
    total_extracted_frames: int
    total_keyframes_selected: int
    total_frames_discarded: int
    overall_quality_score: float = Field(ge=0.0, le=1.0)
    avg_sharpness: float
    avg_feature_count: float
    exposure_stability_score: float = Field(ge=0.0, le=1.0)
    discard_breakdown: Dict[str, int]
    context_tag_breakdown: Dict[str, int]


class PreprocessingManifest(BaseModel):
    """Authoritative frame manifest saved as frame_manifest.json."""
    video_path: str
    video_fps: float
    video_duration_sec: float
    resolution: List[int] = Field(min_length=2, max_length=2, description="[width, height]")
    total_frames: int
    keyframes_count: int
    discarded_count: int
    frames: List[FrameAuditRecord]
