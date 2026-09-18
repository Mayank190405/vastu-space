"""
Formal Schemas for Controlled Physical Benchmark Environment & Accuracy Verification
Defines exact ground truth geometric measurements and comparative metrics for:
- Wall lengths
- Room dimensions
- Corner positions
- Door positions
- Ceiling height
- Furniture positions
"""

import uuid
import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class GroundTruthWall(BaseModel):
    name: str
    length_m: float = Field(gt=0.0)
    plane_normal: List[float] = Field(min_length=3, max_length=3)
    plane_offset_d: float
    start_corner: str
    end_corner: str


class GroundTruthCorner(BaseModel):
    name: str
    position_xyz: List[float] = Field(min_length=3, max_length=3)
    adjacent_walls: List[str]


class GroundTruthOpening(BaseModel):
    name: str
    opening_type: str = "DOOR"
    center_xyz: List[float] = Field(min_length=3, max_length=3)
    width_m: float = Field(gt=0.0)
    height_m: float = Field(gt=0.0)
    host_wall: str


class GroundTruthObject(BaseModel):
    name: str
    category: str
    center_xyz: List[float] = Field(min_length=3, max_length=3)
    dimensions_xyz: List[float] = Field(min_length=3, max_length=3)


class GroundTruthRoom(BaseModel):
    room_id: str = "Lab-Alpha-8x6"
    name: str = "Executive Spatial Test Lab (8m x 6m x 3m)"
    dimensions_xyz: List[float] = Field(default_factory=lambda: [8.000, 6.000, 3.000])
    ceiling_height_m: float = 3.000
    floor_elevation_z_m: float = 0.000
    walls: Dict[str, GroundTruthWall] = Field(default_factory=dict)
    corners: Dict[str, GroundTruthCorner] = Field(default_factory=dict)
    openings: Dict[str, GroundTruthOpening] = Field(default_factory=dict)
    objects: Dict[str, GroundTruthObject] = Field(default_factory=dict)


class MetricMeasurement(BaseModel):
    metric_name: str
    target_dimension: str
    unit: str
    baseline_value: float
    upgraded_value: float
    absolute_improvement: float
    relative_improvement_pct: float
    passed: bool
    empirical_evidence: Dict[str, Any] = Field(default_factory=dict)


class BenchmarkComparisonReport(BaseModel):
    benchmark_id: str = Field(default_factory=lambda: f"bench_{uuid.uuid4().hex[:8]}")
    environment_name: str
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    ground_truth_dimensions: Dict[str, float]
    measurements: List[MetricMeasurement]
    all_metrics_improved: bool
    acceptance_criterion_met: bool
    summary_narrative: str
