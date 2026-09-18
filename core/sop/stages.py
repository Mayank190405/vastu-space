"""
VĀSTU Capture SOP Engine: Procedural Stages
Defines the 11 canonical sequential stages for complete indoor space capture.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class SOPStage(str, Enum):
    ROOM_ENTRY = "ROOM_ENTRY"
    PERIMETER_COVERAGE = "PERIMETER_COVERAGE"
    WALL_COVERAGE = "WALL_COVERAGE"
    CORNERS = "CORNERS"
    DOORWAY = "DOORWAY"
    WINDOWS = "WINDOWS"
    FLOOR = "FLOOR"
    CEILING = "CEILING"
    CENTER_TRAVERSAL = "CENTER_TRAVERSAL"
    RETURN_LOOP_CLOSURE = "RETURN_LOOP_CLOSURE"
    COMPLETION_VERIFICATION = "COMPLETION_VERIFICATION"


class SOPStageDefinition(BaseModel):
    stage: SOPStage
    step_number: int
    title: str
    guidance_instruction: str
    completion_instruction: str
    target_metric_key: str
    target_metric_threshold: float
    timeout_sec: float = 120.0


SOP_STAGES_SEQUENCE: List[SOPStageDefinition] = [
    SOPStageDefinition(
        stage=SOPStage.ROOM_ENTRY,
        step_number=1,
        title="Room Entry",
        guidance_instruction="Stand at the main doorway entrance and hold the camera steady to establish baseline tracking.",
        completion_instruction="Baseline tracking established. Proceed forward into the room.",
        target_metric_key="baseline_frames_accumulated",
        target_metric_threshold=45.0,  # ~1.5s at 30fps
        timeout_sec=15.0
    ),
    SOPStageDefinition(
        stage=SOPStage.PERIMETER_COVERAGE,
        step_number=2,
        title="Perimeter Coverage",
        guidance_instruction="Walk slowly clockwise along the room perimeter, maintaining steady overlapping views.",
        completion_instruction="Perimeter path complete. Now focus directly on wall surfaces.",
        target_metric_key="perimeter_path_length_m",
        target_metric_threshold=8.0,
        timeout_sec=90.0
    ),
    SOPStageDefinition(
        stage=SOPStage.WALL_COVERAGE,
        step_number=3,
        title="Wall Coverage",
        guidance_instruction="Sweep all vertical wall surfaces at roughly two meters distance.",
        completion_instruction="Wall surfaces covered. Prepare to inspect room corners.",
        target_metric_key="wall_surface_observed_fraction",
        target_metric_threshold=0.80,
        timeout_sec=90.0
    ),
    SOPStageDefinition(
        stage=SOPStage.CORNERS,
        step_number=4,
        title="Corners Inspection",
        guidance_instruction="At each corner, tilt the camera at forty-five degrees and sweep from ceiling to floor.",
        completion_instruction="All room corners recorded. Move toward the doorway threshold.",
        target_metric_key="corners_captured_count",
        target_metric_threshold=4.0,
        timeout_sec=60.0
    ),
    SOPStageDefinition(
        stage=SOPStage.DOORWAY,
        step_number=5,
        title="Doorway Capture",
        guidance_instruction="Frame the entrance doorway, threshold, and jambs from both interior sides.",
        completion_instruction="Doorway geometry resolved. Advance to window openings.",
        target_metric_key="doorway_frames_captured",
        target_metric_threshold=30.0,
        timeout_sec=40.0
    ),
    SOPStageDefinition(
        stage=SOPStage.WINDOWS,
        step_number=6,
        title="Windows Inspection",
        guidance_instruction="Capture window frames, sills, and blinds while avoiding direct glare reflections.",
        completion_instruction="Window boundaries captured. Now angle camera down toward the floor.",
        target_metric_key="windows_frames_captured",
        target_metric_threshold=30.0,
        timeout_sec=45.0
    ),
    SOPStageDefinition(
        stage=SOPStage.FLOOR,
        step_number=7,
        title="Floor Plane",
        guidance_instruction="Angle the camera downward at forty-five degrees to scan the floor plane and baseboards.",
        completion_instruction="Floor plane captured. Now tilt camera upward toward the ceiling.",
        target_metric_key="floor_surface_observed_fraction",
        target_metric_threshold=0.75,
        timeout_sec=60.0
    ),
    SOPStageDefinition(
        stage=SOPStage.CEILING,
        step_number=8,
        title="Ceiling & Fixtures",
        guidance_instruction="Tilt camera upward to record the ceiling surface, light fixtures, and beams.",
        completion_instruction="Ceiling coverage verified. Move toward the center of the room.",
        target_metric_key="ceiling_surface_observed_fraction",
        target_metric_threshold=0.70,
        timeout_sec=60.0
    ),
    SOPStageDefinition(
        stage=SOPStage.CENTER_TRAVERSAL,
        step_number=9,
        title="Center Traversal",
        guidance_instruction="Walk across the center of the space to link all opposing wall visual sightlines.",
        completion_instruction="Center crossing complete. Prepare for loop closure.",
        target_metric_key="center_cross_distance_m",
        target_metric_threshold=3.0,
        timeout_sec=45.0
    ),
    SOPStageDefinition(
        stage=SOPStage.RETURN_LOOP_CLOSURE,
        step_number=10,
        title="Return & Loop Closure",
        guidance_instruction="Return to your exact starting position at the doorway to close the visual loop.",
        completion_instruction="Loop closure confirmed. Hold steady for final quality check.",
        target_metric_key="distance_to_origin_m",
        target_metric_threshold=0.50,  # Distance must be <= 0.50m
        timeout_sec=40.0
    ),
    SOPStageDefinition(
        stage=SOPStage.COMPLETION_VERIFICATION,
        step_number=11,
        title="Completion Verification",
        guidance_instruction="Hold still while the system verifies full spatial coverage and tracking integrity.",
        completion_instruction="Capture complete. Space successfully digitized.",
        target_metric_key="overall_spatial_completeness",
        target_metric_threshold=0.85,
        timeout_sec=20.0
    ),
]
