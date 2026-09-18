"""
Contract 12: Rescan Request Schema
Version: 2.0.0
Producer: Quality Engine (Automated) / Operator (Manual)
Consumer: Backend Rescan Service & Mobile Capture App (Guided Retake)

Mandates:
- cell_id: Targeted spatial cell identifier
- region: 3D bounding coordinates, center, and room context
- reason: Specific physical and algorithmic diagnosis
- priority: LOW | MEDIUM | HIGH | CRITICAL
- required_capture_action: Actionable capture pattern, stand-off distance, pitch angle, visual instructions, and audio TTS
- expected_improvement: Target metric, current value, goal value, and confidence gain
"""

import uuid
from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

class RescanBoundingBox(BaseModel):
    min_xyz: List[float] = Field(min_length=3, max_length=3)
    max_xyz: List[float] = Field(min_length=3, max_length=3)
    center_xyz: List[float] = Field(min_length=3, max_length=3)

class RescanRegion(BaseModel):
    min_xyz: List[float] = Field(min_length=3, max_length=3)
    max_xyz: List[float] = Field(min_length=3, max_length=3)
    center_xyz: List[float] = Field(min_length=3, max_length=3)
    room_id: Optional[str] = None
    volume_m3: Optional[float] = None

class OperatorGuidance(BaseModel):
    audio_tts_prompt: str
    haptic_cue: Literal["SINGLE_PULSE", "DOUBLE_VIBRATION", "CONTINUOUS_WARNING"] = "DOUBLE_VIBRATION"
    recommended_camera_distance_m: float = Field(default=1.5, gt=0)
    recommended_orbit_waypoints: List[List[float]] = Field(default_factory=list)

class RequiredCaptureAction(BaseModel):
    capture_pattern: Literal["ORBIT_SWEEP", "PLANAR_SWEEP", "CORNER_DOWNWARD_45", "STANDOFF_WALL", "DOORWAY_PASS"] = "ORBIT_SWEEP"
    recommended_camera_distance_m: float = Field(default=1.5, gt=0)
    camera_pitch_deg: float = Field(default=-30.0, description="Recommended downward/upward tilt in degrees")
    sweep_angle_deg: float = Field(default=90.0, description="Horizontal rotational sweep angle in degrees")
    min_frames_required: int = Field(default=60, ge=10)
    visual_instruction: str = Field(description="Actionable screen HUD reticle instructions")
    audio_tts_prompt: str = Field(description="Spoken guidance for the mobile operator")
    recommended_waypoints: List[List[float]] = Field(default_factory=list)

class ExpectedImprovement(BaseModel):
    target_metric: str = Field(description="Metric to be improved, e.g. point_density_pts_m3, hole_fraction")
    current_value: float
    target_value: float
    expected_confidence_gain: float = Field(ge=0.0, le=1.0)

class RescanRequest(BaseModel):
    request_id: str
    project_id: uuid.UUID
    quality_report_id: Optional[uuid.UUID] = None
    cell_id: str = Field(default="")
    target_cells: List[str] = Field(default_factory=list)
    region: Optional[RescanRegion] = None
    reason: str
    priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH"
    target_bounding_box: RescanBoundingBox
    operator_guidance: OperatorGuidance
    required_capture_action: Optional[RequiredCaptureAction] = None
    expected_improvement: Optional[ExpectedImprovement] = None
    status: Literal["PENDING", "ASSIGNED", "CAPTURING", "UPLOADED", "FUSED", "DISCARDED"] = "PENDING"
    created_at: str

    @model_validator(mode="before")
    @classmethod
    def populate_defaults_and_cross_fields(cls, values: Any) -> Any:
        if isinstance(values, dict):
            # Synchronize cell_id and target_cells
            if not values.get("cell_id") and values.get("target_cells"):
                values["cell_id"] = values["target_cells"][0]
            elif values.get("cell_id") and not values.get("target_cells"):
                values["target_cells"] = [values["cell_id"]]

            # Synchronize region and target_bounding_box
            if not values.get("region") and values.get("target_bounding_box"):
                tb = values["target_bounding_box"]
                if isinstance(tb, dict):
                    values["region"] = {
                        "min_xyz": tb.get("min_xyz", [0, 0, 0]),
                        "max_xyz": tb.get("max_xyz", [1, 1, 1]),
                        "center_xyz": tb.get("center_xyz", [0.5, 0.5, 0.5])
                    }
            elif values.get("region") and not values.get("target_bounding_box"):
                reg = values["region"]
                if isinstance(reg, dict):
                    values["target_bounding_box"] = {
                        "min_xyz": reg.get("min_xyz", [0, 0, 0]),
                        "max_xyz": reg.get("max_xyz", [1, 1, 1]),
                        "center_xyz": reg.get("center_xyz", [0.5, 0.5, 0.5])
                    }

            # Synchronize operator_guidance and required_capture_action
            if not values.get("required_capture_action") and values.get("operator_guidance"):
                og = values["operator_guidance"]
                if isinstance(og, dict):
                    values["required_capture_action"] = {
                        "capture_pattern": "ORBIT_SWEEP",
                        "recommended_camera_distance_m": og.get("recommended_camera_distance_m", 1.5),
                        "camera_pitch_deg": -30.0,
                        "sweep_angle_deg": 90.0,
                        "min_frames_required": 60,
                        "visual_instruction": og.get("audio_tts_prompt", "Perform orbital sweep"),
                        "audio_tts_prompt": og.get("audio_tts_prompt", "Perform orbital sweep"),
                        "recommended_waypoints": og.get("recommended_orbit_waypoints", [])
                    }
        return values
