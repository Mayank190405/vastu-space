"""
Contract 1: Versioned Capture Manifest Schema
Version: 2.0.0 (with 1.0.0 backward compatibility)
Producer: Mobile Capture App (iOS / Android)
Consumer: Backend API / Preprocessing Worker / Reproducibility Engine
"""

from typing import List, Literal, Optional, Dict, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator
import uuid
from core.domain.enums import (
    CoordinateSystem,
    ScaleSource,
    CaptureUploadStatus,
    CameraDistortionModel,
    CalibrationType,
)

# ---------------------------------------------------------------------------
# 1. Device Information
# ---------------------------------------------------------------------------
class DeviceInfo(BaseModel):
    manufacturer: str
    model: str
    os_name: Literal["iOS", "Android", "Linux", "macOS"]
    os_version: str
    app_version: str
    thermal_state: Optional[Literal["nominal", "fair", "serious", "critical"]] = "nominal"
    hardware_id: Optional[str] = None


# ---------------------------------------------------------------------------
# 2. Camera Parameters & Calibration
# ---------------------------------------------------------------------------
class CameraCalibration(BaseModel):
    fx: float = Field(gt=0, description="Focal length x in pixels")
    fy: float = Field(gt=0, description="Focal length y in pixels")
    cx: float = Field(gt=0, description="Principal point x in pixels")
    cy: float = Field(gt=0, description="Principal point y in pixels")
    image_width: int = Field(ge=640)
    image_height: int = Field(ge=480)
    sensor_width_mm: Optional[float] = Field(default=None, gt=0)
    sensor_height_mm: Optional[float] = Field(default=None, gt=0)
    pixel_pitch_um: Optional[float] = Field(default=None, gt=0)
    rolling_shutter_readout_sec: Optional[float] = Field(default=0.0, ge=0.0)
    distortion_model: Union[CameraDistortionModel, Literal["pinhole", "radtan", "brown_conrady", "fisheye"]] = "pinhole"
    distortion_coefficients: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 0.0])

    @field_validator("cx")
    def validate_cx(cls, v: float, values):
        w = values.data.get("image_width")
        if w and not (0.35 * w <= v <= 0.65 * w):
            raise ValueError(f"Principal point cx={v} outside expected range [0.35*W, 0.65*W]")
        return v

    @field_validator("cy")
    def validate_cy(cls, v: float, values):
        h = values.data.get("image_height")
        if h and not (0.35 * h <= v <= 0.65 * h):
            raise ValueError(f"Principal point cy={v} outside expected range [0.35*H, 0.65*H]")
        return v


class CalibrationMetadata(BaseModel):
    calibration_type: Union[CalibrationType, str] = CalibrationType.FACTORY
    calibrated_at: Optional[str] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    reprojection_error_px: Optional[float] = Field(default=None, ge=0.0)


# ---------------------------------------------------------------------------
# 3. Video Metadata
# ---------------------------------------------------------------------------
class VideoFileMeta(BaseModel):
    filename: str
    size_bytes: int = Field(ge=10240)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    duration_sec: float = Field(ge=1.0, le=1800.0)
    frame_count: int = Field(ge=30)
    fps: float = Field(ge=15.0, le=120.0)
    codec: Literal["h264", "h265", "hevc", "prores"] = "h264"
    bitrate_kbps: Optional[int] = None
    color_space: Optional[str] = "BT.709"
    is_hdr: bool = False

    @field_validator("frame_count")
    def validate_frame_count(cls, v: int, values):
        dur = values.data.get("duration_sec")
        fps = values.data.get("fps")
        if dur and fps:
            expected = dur * fps
            if abs(v - expected) > 0.15 * expected:
                raise ValueError(f"Frame count {v} deviates >15% from duration*fps ({expected})")
        return v


# ---------------------------------------------------------------------------
# 4. Frame Timestamps (Per-Frame High-Precision Metadata)
# ---------------------------------------------------------------------------
class FrameTimingRecord(BaseModel):
    frame_index: int = Field(ge=0)
    relative_timestamp_sec: float = Field(ge=0.0)
    monotonic_timestamp_ns: int = Field(ge=0)
    pts_timestamp_ns: Optional[int] = None
    exposure_time_sec: Optional[float] = Field(default=None, gt=0.0)
    iso_gain: Optional[float] = Field(default=None, ge=1.0)


class FrameTimestampsMeta(BaseModel):
    filename: Optional[str] = "frame_timestamps.json"
    size_bytes: Optional[int] = None
    sha256: Optional[str] = None
    sample_count: int = Field(default=0, ge=0)
    records: Optional[List[FrameTimingRecord]] = None


# ---------------------------------------------------------------------------
# 5. IMU Metadata
# ---------------------------------------------------------------------------
class IMUFileMeta(BaseModel):
    filename: str
    size_bytes: int = Field(ge=512)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    sample_count: int = Field(ge=100)
    sampling_rate_hz: float = Field(ge=25.0, le=1000.0)
    accel_range_g: Optional[float] = 16.0
    gyro_range_dps: Optional[float] = 2000.0
    accel_noise_density: Optional[float] = None
    gyro_noise_density: Optional[float] = None
    start_timestamp_ns: Optional[int] = None
    end_timestamp_ns: Optional[int] = None
    camera_to_imu_matrix: Optional[List[List[float]]] = Field(
        default_factory=lambda: [
            [1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )


class DepthFileMeta(BaseModel):
    filename: str = "sparse_depth.bin"
    size_bytes: int = 0
    sha256: Optional[str] = None
    point_count: int = 0
    sensor_type: str = "lidar_sparse"


class CaptureFiles(BaseModel):
    video: VideoFileMeta
    imu: IMUFileMeta
    timestamps: Optional[FrameTimestampsMeta] = None
    depth: Optional[DepthFileMeta] = None


# ---------------------------------------------------------------------------
# 6. Coordinate System & Scale Information
# ---------------------------------------------------------------------------
class CoordinateSystemMeta(BaseModel):
    convention: Union[CoordinateSystem, str] = CoordinateSystem.OPENCV_RDF
    gravity_aligned: bool = True
    gravity_vector: List[float] = Field(default_factory=lambda: [0.0, 9.81, 0.0])

    @field_validator("gravity_vector")
    def validate_gravity_norm(cls, v: List[float]):
        if len(v) != 3:
            raise ValueError("gravity_vector must have exactly 3 components [gx, gy, gz]")
        norm = sum(x**2 for x in v) ** 0.5
        # Norm should be either normalized (approx 1.0) or earth gravity (approx 9.81 m/s^2)
        if not (0.8 <= norm <= 1.2 or 8.0 <= norm <= 11.5):
            raise ValueError(f"Gravity vector norm {norm:.2f} is outside physically plausible range")
        return v


class ScaleInformation(BaseModel):
    scale_factor: float = Field(default=1.0, gt=0.0, description="Multiplier to convert model units to meters")
    scale_source: Union[ScaleSource, str] = ScaleSource.LIDAR_SPARSE
    scale_uncertainty: Optional[float] = Field(default=0.02, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# 7. Quality Metrics & Coverage Information
# ---------------------------------------------------------------------------
class CaptureQualityMetrics(BaseModel):
    dropped_frames: int = Field(ge=0, default=0)
    imu_packet_drops: int = Field(ge=0, default=0)
    average_lux: float = Field(ge=0, default=100.0)
    motion_blur_score: Optional[float] = Field(default=0.05, ge=0.0, le=1.0)
    operator_speed_mps: Optional[float] = Field(default=0.6, ge=0.0)
    feature_density_score: Optional[float] = Field(default=0.85, ge=0.0, le=1.0)


class SpatialBoundingBox(BaseModel):
    min_xyz: List[float] = Field(default_factory=lambda: [-5.0, 0.0, -5.0])
    max_xyz: List[float] = Field(default_factory=lambda: [5.0, 3.0, 5.0])


class CoverageInformation(BaseModel):
    estimated_area_m2: float = Field(default=25.0, ge=0.0)
    estimated_path_length_m: float = Field(default=15.0, ge=0.0)
    spatial_bounding_box: SpatialBoundingBox = Field(default_factory=SpatialBoundingBox)
    keyframe_count: int = Field(default=60, ge=0)
    loop_closure_detected: bool = False


# ---------------------------------------------------------------------------
# 8. Complete Versioned Manifest
# ---------------------------------------------------------------------------
class CaptureManifest(BaseModel):
    manifest_version: Literal["1.0.0", "2.0.0"] = "1.0.0"
    capture_id: uuid.UUID
    project_id: uuid.UUID
    device_info: DeviceInfo
    camera_calibration: CameraCalibration
    calibration: CalibrationMetadata = Field(default_factory=CalibrationMetadata)
    files: CaptureFiles
    coordinate_system: CoordinateSystemMeta = Field(default_factory=CoordinateSystemMeta)
    scale_info: ScaleInformation = Field(default_factory=ScaleInformation)
    sop_version: str = Field(default="vastu_sop_v2.0_indoor_continuous")
    metrics: CaptureQualityMetrics = Field(default_factory=CaptureQualityMetrics)
    coverage: CoverageInformation = Field(default_factory=CoverageInformation)
    upload_status: Union[CaptureUploadStatus, str] = CaptureUploadStatus.UPLOADED
    checksums: Dict[str, str] = Field(default_factory=dict)
    package_digest: Optional[str] = None
    created_at: str

    @model_validator(mode="after")
    def compute_defaults(self):
        # Automatically populate checksums dict from files if empty
        if not self.checksums:
            if self.files.video and self.files.video.sha256:
                self.checksums[self.files.video.filename] = self.files.video.sha256
            if self.files.imu and self.files.imu.sha256:
                self.checksums[self.files.imu.filename] = self.files.imu.sha256
        return self
