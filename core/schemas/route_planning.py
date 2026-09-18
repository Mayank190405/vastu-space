"""
Contract: Route Planning Schemas
Version: 1.0.0
Producer: Route Planning Engine (Stage 22)
Consumer: Indoor A* Router, Navigation Control Plane, Web/AR Viewers

Defines:
1. RoutePlanningRequest (start point, destination POI, wheelchair & cost preferences).
2. RouteTurnStep (turn-by-turn navigation instructions with metric distances).
3. RoutePlanningResult (smoothed collision-free 3D waypoints, turn counts, and validation proof).
"""

from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
import uuid


class RoutePlanningRequest(BaseModel):
    """Input payload for multi-criteria indoor route planning."""
    start_position: List[float] = Field(min_length=3, max_length=3, description="[x, y, z] start coordinates in metric space")
    destination_poi_id: Optional[str] = Field(None, description="Target POI ID (resolved via POIService)")
    destination_coordinates: Optional[List[float]] = Field(None, min_length=3, max_length=3, description="Target [x, y, z] if not using POI ID")
    model_version: Optional[str] = Field("1.0.0", description="Digital twin model version")
    require_wheelchair: bool = Field(default=False, description="Enforce ADA slope (<=4.76 deg), width (>=0.90m), no stairs")
    avoid_stairs: bool = Field(default=False, description="Strictly exclude stair transitions")
    human_radius_m: float = Field(default=0.35, gt=0.0, description="Human body clearance radius in meters")
    enable_smoothing: bool = Field(default=True, description="Enable string-pulling line-of-sight path smoothing")
    turn_penalty_weight: float = Field(default=1.5, ge=0.0, description="Cost penalty weight for sharp turns")
    narrow_passage_penalty_weight: float = Field(default=2.0, ge=0.0, description="Cost penalty weight for narrow passages (<1.20m)")


class RouteTurnStep(BaseModel):
    """A discrete turn-by-turn guidance instruction."""
    step_number: int = Field(ge=1)
    instruction: str = Field(..., description="Human-readable instruction (e.g. 'Turn left toward Meeting Room 4')")
    distance_meters: float = Field(ge=0.0)
    action: Literal["START", "CONTINUE", "TURN_LEFT", "TURN_RIGHT", "SLIGHT_LEFT", "SLIGHT_RIGHT", "U_TURN", "ARRIVE"]
    turn_angle_deg: float = Field(default=0.0)
    coordinate: List[float] = Field(min_length=3, max_length=3)


class RoutePlanningResult(BaseModel):
    """
    Authoritative route planning result.
    Guarantees strict rejection of invalid paths and verified zero collision.
    """
    success: bool = Field(..., description="True if a valid, collision-free route was found")
    route_id: str = Field(..., description="Unique route instance identifier")
    rejection_reason: Optional[str] = Field(None, description="Diagnostic reason if route was rejected")
    start_position: List[float] = Field(min_length=3, max_length=3)
    destination_poi_id: Optional[str] = None
    destination_poi_name: Optional[str] = None
    destination_position: List[float] = Field(min_length=3, max_length=3)
    waypoints: List[List[float]] = Field(default_factory=list, description="Smoothed, collision-free 3D waypoints")
    raw_waypoints: List[List[float]] = Field(default_factory=list, description="Unsmoothed NavMesh graph node waypoints")
    total_distance_meters: float = Field(default=0.0, ge=0.0)
    estimated_duration_seconds: int = Field(default=0, ge=0)
    turn_count: int = Field(default=0, ge=0)
    narrow_passage_count: int = Field(default=0, ge=0)
    is_wheelchair_accessible: bool = Field(default=True)
    max_slope_degrees: float = Field(default=0.0, ge=0.0)
    min_obstacle_clearance_meters: float = Field(default=1.0, ge=0.0)
    collision_validated: bool = Field(default=True, description="Strictly True: Verified collision-free against collision model")
    steps: List[RouteTurnStep] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
