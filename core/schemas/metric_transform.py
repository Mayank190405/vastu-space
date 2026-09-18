"""
Formal Schema for Metric Coordinate Alignment & Canonical World Transforms
Version: 1.0.0
Producer: Metric Alignment Engine
Consumer: Model Publishing Service, Web Viewer, CAD/BIM Exporter, NavMesh Generator
"""

from typing import List, Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel, Field

class MetricScaleSource(str, Enum):
    METRIC_LIDAR_AR = "METRIC_LIDAR_AR"
    MEASURED_PHYSICAL_DIMENSIONS = "MEASURED_PHYSICAL_DIMENSIONS"
    KNOWN_FLOORPLAN_DIMENSIONS = "KNOWN_FLOORPLAN_DIMENSIONS"
    RELIABLE_KNOWN_OBJECT_DIMENSIONS = "RELIABLE_KNOWN_OBJECT_DIMENSIONS"
    MANUAL_CORRECTION = "MANUAL_CORRECTION"
    UNSCALED = "UNSCALED"

class MetricTransformSchema(BaseModel):
    scale: float = Field(gt=0.0, description="Metric uniform scale factor s > 0")
    translation: List[float] = Field(min_length=3, max_length=3, description="Translation vector [tx, ty, tz] in meters")
    rotation_matrix: List[List[float]] = Field(description="3x3 orthonormal rotation matrix R")
    rotation_quaternion: List[float] = Field(min_length=4, max_length=4, description="Rotation quaternion [qx, qy, qz, qw]")
    matrix_4x4: List[List[float]] = Field(description="4x4 homogeneous Sim(3) transformation matrix")
    scale_source: MetricScaleSource
    scale_confidence: float = Field(ge=0.0, le=1.0)
    canonical_frame: str = "RIGHT_HANDED_Z_UP"
    floor_elevation_m: float = 0.0
    evidence_details: Dict[str, Any] = Field(default_factory=dict)
