"""
VĀSTU Navigation Benchmark Schemas (Stage 28)
Formal contracts for navigation benchmark scenarios, quantitative performance metrics,
and validation reports.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from core.schemas.representation_bundle import CollisionObstacle


class NavigationScenarioType(str, Enum):
    """The 9 mandated navigation benchmark scenarios."""
    DIRECT_PATH = "direct_path"
    OBSTACLE_AROUND_LEFT = "obstacle_around_left"
    OBSTACLE_AROUND_RIGHT = "obstacle_around_right"
    NARROW_CORRIDOR = "narrow_corridor"
    FURNITURE_CLUSTER = "furniture_cluster"
    DOORWAY = "doorway"
    DISCONNECTED_REGION = "disconnected_region"
    START_NEAR_OBSTACLE = "start_near_obstacle"
    DESTINATION_NEAR_OBSTACLE = "destination_near_obstacle"


class NavigationScenarioConfig(BaseModel):
    """Configuration definition for a benchmark scenario."""
    scenario_type: NavigationScenarioType
    name: str
    description: str
    start_position: List[float] = Field(..., min_length=3, max_length=3)
    destination_position: List[float] = Field(..., min_length=3, max_length=3)
    obstacles: List[CollisionObstacle] = Field(default_factory=list)
    expected_to_succeed: bool = True
    human_radius_m: float = 0.35
    max_acceptable_path_length_m: Optional[float] = None
    min_required_clearance_m: float = 0.35


class NavigationScenarioResult(BaseModel):
    """Quantitative evaluation result for a single scenario."""
    scenario_type: NavigationScenarioType
    name: str
    success: bool
    rejection_reason: Optional[str] = None
    path_found: bool
    is_valid: bool
    collision_detected: bool
    path_length_meters: float
    direct_euclidean_distance_meters: float
    path_efficiency_ratio: float = 1.0  # path_length / direct_dist (1.0 = direct)
    computation_time_ms: float
    waypoint_count: int
    mean_turn_angle_degrees: float
    max_turn_angle_degrees: float
    waypoint_smoothness_score: float  # [0.0, 1.0], 1.0 = straight line
    rejection_correctly_enforced: bool
    waypoints: List[List[float]] = Field(default_factory=list)


class NavigationBenchmarkSummary(BaseModel):
    """Aggregated quantitative performance metrics across all test scenarios."""
    total_scenarios_evaluated: int
    valid_scenarios_count: int
    invalid_scenarios_count: int
    route_success_rate: float  # 0.0 to 1.0 (successful / valid_scenarios)
    collision_rate: float  # must be 0.0 (colliding_routes / total_generated)
    mean_path_length_meters: float
    mean_computation_time_ms: float
    max_computation_time_ms: float
    mean_waypoint_smoothness: float  # 0.0 to 1.0
    mean_turn_angle_degrees: float
    invalid_route_rejection_rate: float  # 1.0 = 100% of invalid routes rejected
    quantitative_validation_passed: bool
    acceptance_criterion_met: bool


class NavigationBenchmarkReport(BaseModel):
    """Full benchmark report containing individual scenario results and summary."""
    benchmark_id: str
    timestamp: str
    summary: NavigationBenchmarkSummary
    scenarios: List[NavigationScenarioResult]
    acceptance_criterion: str = "Navigation is validated quantitatively rather than judged only visually."
    acceptance_criterion_met: bool
    narrative: str
