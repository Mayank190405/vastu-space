"""
VĀSTU v3.0 — Capture Package Schema v1.0
=========================================
Formal Pydantic v2 contract for the standardized zero-LiDAR capture package.
Defines the shared data contract between the iOS capture client (Swift)
and the backend reconstruction pipeline (Python).

Logical package structure:
capture_<session_id>/
  manifest.json
  session_metadata.json
  calibration/
    camera_intrinsics.json
    lens_metadata.json
  tracking/
    camera_poses.jsonl
    tracking_events.jsonl
    anchors.json
  frames/
    frame_000001.jpg
    ...
  observations/
    floor_boundaries.jsonl
    coverage.json
  checksums.sha256
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union, Literal
import math
import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from core.coordinates.conventions import CameraConvention, WorldConvention


class TrackingState(str, Enum):
    """ARKit Tracking State classifications."""
    NORMAL = "NORMAL"
    LIMITED_INITIALIZING = "LIMITED_INITIALIZING"
    LIMITED_EXCESSIVE_MOTION = "LIMITED_EXCESSIVE_MOTION"
    LIMITED_INSUFFICIENT_FEATURES = "LIMITED_INSUFFICIENT_FEATURES"
    LIMITED_RELOCALIZING = "LIMITED_RELOCALIZING"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class LensMetadata(BaseModel):
    """Optional optical and hardware metadata."""
    lens_model: Optional[str] = None
    sensor_width_mm: Optional[float] = None
    sensor_height_mm: Optional[float] = None
    pixel_pitch_um: Optional[float] = None
    rolling_shutter_readout_sec: Optional[float] = None


class CameraIntrinsicsRecord(BaseModel):
    """Pinhole camera intrinsic parameters for calibration/camera_intrinsics.json."""
    calibration_id: str = "calib_default"
    model_config = ConfigDict(allow_inf_nan=False)
    fx: float = Field(gt=0.0, description="Focal length in x (pixels)")
    fy: float = Field(gt=0.0, description="Focal length in y (pixels)")
    cx: float = Field(gt=0.0, description="Principal point x (pixels)")
    cy: float = Field(gt=0.0, description="Principal point y (pixels)")
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    distortion_model: str = "PINHOLE"
    distortion_coefficients: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0, 0.0])

    @model_validator(mode="after")
    def validate_principal_points(self):
        w = self.image_width
        h = self.image_height
        if not (0.25 * w <= self.cx <= 0.75 * w):
            raise ValueError(f"Principal point cx={self.cx} is outside plausible optical center range [0.25*W, 0.75*W] for width={w}")
        if not (0.25 * h <= self.cy <= 0.75 * h):
            raise ValueError(f"Principal point cy={self.cy} is outside plausible optical center range [0.25*H, 0.75*H] for height={h}")
        if self.distortion_model != "PINHOLE" or any(self.distortion_coefficients):
            raise ValueError("V1 ingestion supports rectified PINHOLE images only")
        return self


class CameraPoseRecord(BaseModel):
    """
    Per-frame camera pose line in tracking/camera_poses.jsonl.
    Represents T_world_camera (camera-to-world transform in meters).
    """
    frame_id: str = Field(description="Filename of the corresponding keyframe, e.g. frame_000001.jpg")
    timestamp_ns: int = Field(ge=0, description="Monotonic timestamp in nanoseconds")
    T_world_camera: List[List[float]] = Field(
        description="4x4 homogeneous camera-to-world matrix in meters"
    )
    intrinsics_id: str = "calib_default"
    image_width: int = Field(gt=0)
    image_height: int = Field(gt=0)
    tracking_state: TrackingState = TrackingState.NORMAL
    model_config = ConfigDict(allow_inf_nan=False)
    image_orientation: str = "sensor_native"
    device_orientation: Optional[str] = None
    
    # Optional capture telemetry (preserved if available, ignored if unsupported by device)
    exposure_time_s: Optional[float] = None
    iso: Optional[float] = None
    white_balance_kelvin: Optional[float] = None
    focus_lens_position: Optional[float] = None

    @field_validator("T_world_camera")
    def validate_transform_matrix(cls, matrix: List[List[float]]):
        T = np.asarray(matrix, dtype=np.float64)
        if T.shape != (4, 4):
            raise ValueError(f"T_world_camera must be 4x4 matrix, got shape {T.shape}")
        if not np.all(np.isfinite(T)):
            raise ValueError("T_world_camera contains non-finite values")
        
        # Check bottom row is [0, 0, 0, 1]
        bottom_row = T[3, :]
        if not np.allclose(bottom_row, [0.0, 0.0, 0.0, 1.0], atol=1e-4):
            raise ValueError(f"Bottom row of T_world_camera must be [0, 0, 0, 1], got {bottom_row}")
        
        # Check translation elements are finite
        translation = T[:3, 3]
        if not np.all(np.isfinite(translation)):
            raise ValueError(f"Translation contains non-finite values: {translation}")
        
        # Check 3x3 rotation block is orthonormal with det = +1
        R = T[:3, :3]
        err = np.linalg.norm(R @ R.T - np.eye(3))
        if err > 1e-3:
            raise ValueError(f"Rotation submatrix is not orthonormal (deviation={err:.6e})")
        
        det = np.linalg.det(R)
        if not np.isclose(det, 1.0, atol=1e-3):
            raise ValueError(f"Rotation submatrix determinant must be +1.0, got {det:.4f}")

        return matrix


class TrackingStateEvent(BaseModel):
    """Event record in tracking/tracking_events.jsonl."""
    timestamp_ns: int = Field(ge=0)
    previous_state: TrackingState
    current_state: TrackingState
    reason: Optional[str] = None


class FloorAnchorObservation(BaseModel):
    """Observation in tracking/anchors.json."""
    anchor_id: str = "floor_anchor_0"
    plane_type: Literal["FLOOR", "CEILING", "WALL"] = "FLOOR"
    elevation_y_m: float = 0.0
    normal_vector: List[float] = Field(default_factory=lambda: [0.0, 1.0, 0.0])
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    source: str = "ARKIT_PLANE_DETECTION"


class FloorBoundaryObservation(BaseModel):
    """Record in observations/floor_boundaries.jsonl."""
    frame_id: str
    timestamp_ns: int
    boundary_points_world: List[List[float]] = Field(
        description="List of 3D floor boundary coordinates [X, Y, Z] in meters"
    )
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)


class CaptureManifestV1(BaseModel):
    """
    Top-level manifest in manifest.json.
    Authoritative v3.0 Capture Data Contract.
    """
    schema_version: Literal["1.0.0"] = "1.0.0"
    session_id: str = Field(description="Unique capture session UUID or identifier")
    device_model: str = Field(description="Hardware model name, e.g. iPhone14,2")
    os_name: str = "iOS"
    os_version: Optional[str] = None
    app_version: Optional[str] = None
    
    # Coordinate conventions contract
    camera_convention: CameraConvention = CameraConvention.ARKIT_RUB
    world_convention: Literal[WorldConvention.RIGHT_HANDED_Y_UP] = WorldConvention.RIGHT_HANDED_Y_UP
    units: Literal["meters"] = "meters"
    image_orientation: str = "sensor_native"
    timestamp_domain: Literal["monotonic_boot_ns"] = "monotonic_boot_ns"
    
    # Session lifecycle & statistics
    calibration_id: str = "calib_default"
    frame_count: int = Field(ge=1, description="Total keyframes recorded")
    capture_start_ns: int = Field(ge=0)
    capture_end_ns: int = Field(ge=0)
    
    # File integrity checksums (filename -> sha256)
    checksums: Dict[str, str] = Field(default_factory=dict)
    
    # Optional extensions
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_session_timestamps(self):
        if self.capture_end_ns < self.capture_start_ns:
            raise ValueError(
                f"capture_end_ns ({self.capture_end_ns}) must be >= capture_start_ns ({self.capture_start_ns})"
            )
        return self
