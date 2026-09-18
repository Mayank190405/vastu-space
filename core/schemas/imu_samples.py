"""
Contract 3: IMU Samples Schema
Version: 1.0.0
Producer: Mobile Sensor Manager
Consumer: Stage 01 Preprocessor & Stage 03 Camera Tracker
"""

from typing import Optional
from pydantic import BaseModel, Field

class Vector3D(BaseModel):
    x: float
    y: float
    z: float

class IMUSample(BaseModel):
    timestamp_ns: int = Field(gt=0)
    accel_m_s2: Vector3D
    gyro_rad_s: Vector3D
    magnetic_field_ut: Optional[Vector3D] = None
    gravity_vector: Optional[Vector3D] = None
