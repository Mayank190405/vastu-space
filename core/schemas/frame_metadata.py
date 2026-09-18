"""
Contract 2: Frame Metadata Schema
Version: 1.0.0
Producer: Mobile Capture App / Stage 01 Preprocessor
Consumer: Stage 02 SfM Pipeline & Stage 03 Camera Tracker
"""

from pydantic import BaseModel, Field

class FrameMetadata(BaseModel):
    frame_index: int = Field(ge=0)
    timestamp_ns: int = Field(gt=0, description="Nanoseconds since epoch or device boot")
    exposure_time_sec: float = Field(gt=0, lt=0.15)
    iso: int = Field(ge=10, le=25600)
    focal_length_px: float = Field(gt=0)
    laplacian_blur_score: float = Field(ge=0)
    is_keyframe: bool = False
    is_blurry: bool = False
    is_underexposed: bool = False
