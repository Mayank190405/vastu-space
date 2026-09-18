"""
Scale Evidence Containers & Priority Definitions:
Represents the 5 evidence tiers for metric scale estimation in strict descending priority order:
1. Metric LiDAR/AR data
2. Measured physical dimensions
3. Known floor-plan dimensions
4. Reliable known object dimensions
5. Manual correction
"""

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import numpy as np

from core.schemas.metric_transform import MetricScaleSource

@dataclass
class LiDAREvidence:
    """Priority 1: Metric LiDAR / ARKit / ARCore sensor tracking data."""
    scale_factor: float = 1.0
    confidence: float = 0.98
    sensor_model: str = "lidar_tof"
    point_count: int = 1000

@dataclass
class PhysicalMeasurementEvidence:
    """Priority 2: Physical laser tape measurement between two 3D landmarks."""
    measured_distance_m: float
    point_a_3d: np.ndarray
    point_b_3d: np.ndarray
    confidence: float = 0.92
    measurement_tool: str = "laser_rangefinder"

    def compute_scale(self) -> float:
        unscaled_dist = float(np.linalg.norm(self.point_b_3d - self.point_a_3d))
        if unscaled_dist < 1e-4:
            return 1.0
        return self.measured_distance_m / unscaled_dist

@dataclass
class FloorplanDimensionEvidence:
    """Priority 3: Known dimension from architectural CAD / floor-plan drawing."""
    reference_distance_m: float
    feature_a_3d: np.ndarray
    feature_b_3d: np.ndarray
    drawing_reference_id: str
    confidence: float = 0.85

    def compute_scale(self) -> float:
        unscaled_dist = float(np.linalg.norm(self.feature_b_3d - self.feature_a_3d))
        if unscaled_dist < 1e-4:
            return 1.0
        return self.reference_distance_m / unscaled_dist

@dataclass
class KnownObjectEvidence:
    """Priority 4: Standardized architectural object dimension (e.g. door width, desk height)."""
    object_class: str
    observed_dimension_m: float
    standard_dimension_m: float
    confidence: float = 0.75

    def compute_scale(self) -> float:
        if self.observed_dimension_m < 1e-4:
            return 1.0
        return self.standard_dimension_m / self.observed_dimension_m

@dataclass
class ManualCorrectionEvidence:
    """Priority 5: Manual operator scale correction."""
    manual_scale_factor: float
    operator_id: str
    reason: str
    confidence: float = 0.60
