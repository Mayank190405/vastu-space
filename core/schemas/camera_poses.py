"""
Contract 4: Camera Poses Schema
Version: 1.0.0
Producer: Stage 02 SfM Pipeline / Stage 03 Camera Tracker
Consumer: Stage 04 Depth Estimator, Stage 07 Texture Engine, Web Viewer
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class TrackingSource(str, Enum):
    DEVICE_VIO = "DEVICE_VIO"
    VISUAL_TRACKING = "VISUAL_TRACKING"
    SFM_BA = "SFM_BA"
    FUSED_HYBRID = "FUSED_HYBRID"
    ESTIMATED_INTERPOLATION = "ESTIMATED_INTERPOLATION"


class PoseAnomalyType(str, Enum):
    TRACKING_LOSS = "TRACKING_LOSS"
    INSUFFICIENT_PARALLAX = "INSUFFICIENT_PARALLAX"
    DISCONNECTED_TRAJECTORY = "DISCONNECTED_TRAJECTORY"
    HIGH_REPROJECTION_ERROR = "HIGH_REPROJECTION_ERROR"
    LOOP_CLOSURE_MISMATCH = "LOOP_CLOSURE_MISMATCH"


class CameraTrajectoryFrame(BaseModel):
    frame_index: int = Field(ge=0)
    timestamp_ns: int = Field(ge=0)
    rotation_matrix: List[List[float]] = Field(description="3x3 rotation matrix SO(3)")
    translation_vector_m: List[float] = Field(min_length=3, max_length=3)
    quaternion_xyzw: List[float] = Field(min_length=4, max_length=4)
    camera_center_m: List[float] = Field(min_length=3, max_length=3)
    reprojection_error_px: float = Field(ge=0.0)
    inlier_points_count: int = Field(ge=0)
    tracking_source: TrackingSource = TrackingSource.FUSED_HYBRID
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    is_reliable: bool = True
    anomaly_flags: List[str] = Field(default_factory=list)


class UnreliablePoseSegment(BaseModel):
    start_frame: int
    end_frame: int
    reason: str
    anomaly_type: PoseAnomalyType


class CameraPoses(BaseModel):
    camera_model: str = "PINHOLE"
    intrinsics: List[float] = Field(min_length=4, max_length=4, description="[fx, fy, cx, cy]")
    trajectory: List[CameraTrajectoryFrame]
    unreliable_segments: List[UnreliablePoseSegment] = Field(default_factory=list)
    loop_closure_detected: bool = False
    loop_closure_residual_m: Optional[float] = None
    overall_confidence: float = Field(ge=0.0, le=1.0, default=1.0)

