"""
VĀSTU Mobile Capture: Telemetry Models
Captures lossless per-frame metadata, IMU samples, and device configuration.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import time
from core.capture.lifecycle import CaptureState

class DeviceOrientation(BaseModel):
    roll_rad: float = 0.0
    pitch_rad: float = 0.0
    yaw_rad: float = 0.0
    quaternion: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])  # [qx, qy, qz, qw]


class ExposureMetadata(BaseModel):
    exposure_duration_sec: float = Field(default=0.016, gt=0.0)
    iso: float = Field(default=100.0, ge=1.0)
    f_number: Optional[float] = 1.8
    lens_position: Optional[float] = Field(default=0.5, ge=0.0, le=1.0)


class FrameTelemetryRecord(BaseModel):
    monotonic_timestamp_ns: int = Field(default=0, description="Monotonic host clock in nanoseconds")
    relative_timestamp_sec: float = Field(default=0.0, description="Relative session time in seconds")
    timestamp_ns: Optional[int] = Field(default=None, description="Alias for monotonic_timestamp_ns")
    timestamp_sec: Optional[float] = Field(default=None, description="Alias for relative_timestamp_sec")
    frame_index: int = Field(ge=0, description="Sequential contiguous frame index")
    sensor_timestamp_ns: int = Field(..., description="Hardware camera sensor exposure timestamp")
    device_orientation: DeviceOrientation = Field(default_factory=DeviceOrientation)
    exposure_metadata: Optional[ExposureMetadata] = Field(default_factory=ExposureMetadata)
    capture_state: CaptureState = CaptureState.RECORDING
    segment_index: int = Field(default=0, ge=0)

    def model_post_init(self, __context: Any) -> None:
        if self.timestamp_ns is not None and self.monotonic_timestamp_ns == 0:
            self.monotonic_timestamp_ns = self.timestamp_ns
        elif self.timestamp_ns is None:
            self.timestamp_ns = self.monotonic_timestamp_ns

        if self.timestamp_sec is not None and self.relative_timestamp_sec == 0.0:
            self.relative_timestamp_sec = self.timestamp_sec
        elif self.timestamp_sec is None:
            self.timestamp_sec = self.relative_timestamp_sec



class IMUSampleRecord(BaseModel):
    timestamp_ns: int = Field(..., description="Monotonic host clock in nanoseconds")
    sensor_timestamp_ns: int = Field(..., description="Hardware IMU clock in nanoseconds")
    accel_mps2: List[float] = Field(default_factory=lambda: [0.0, 9.81, 0.0])  # [ax, ay, az]
    gyro_radps: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0])    # [gx, gy, gz]
    orientation: Optional[DeviceOrientation] = None


class MobileDeviceMetadata(BaseModel):
    manufacturer: str = "Apple"
    model: str = "iPhone 15 Pro"
    os_name: str = "iOS"
    os_version: str = "17.5"
    app_version: str = "2.0.0"
    hardware_id: Optional[str] = None
    thermal_state: str = "nominal"
    battery_level: float = 0.95
    fx: float = 1450.0
    fy: float = 1450.0
    cx: float = 960.0
    cy: float = 540.0
    image_width: int = 1920
    image_height: int = 1080
    rolling_shutter_readout_sec: float = 0.015
