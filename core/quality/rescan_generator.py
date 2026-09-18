"""
Targeted Rescan Task Generator:
Automates the 10-step targeted rescan workflow:
1. Identifies failure region
2. Identifies failure reason
3. Calculates required additional observations (pattern, distance, pitch, waypoints)
4. Generates Contract 12 RescanRequest with actionable instructions (Never generic 'scan again')
5. Computes expected improvements with measurable target values
"""

import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Literal

from core.schemas.rescan_request import (
    RescanRequest,
    RescanRegion,
    RescanBoundingBox,
    OperatorGuidance,
    RequiredCaptureAction,
    ExpectedImprovement
)

class TargetedRescanGenerator:
    """
    Translates quality failure diagnoses into specific, actionable rescan tasks.
    """

    DEFECT_PATTERNS = {
        "HOLE": {
            "pattern": "CORNER_DOWNWARD_45",
            "distance_m": 1.2,
            "pitch_deg": -45.0,
            "sweep_deg": 90.0,
            "min_frames": 50,
            "target_metric": "hole_fraction",
            "default_goal": 0.03,
            "visual_template": "Align guide crosshairs with the unobserved corner surface ({room}) and tilt camera 45° downward.",
            "tts_template": "Unobserved surface gap detected in {room}. Move to 1.2 meters, tilt camera 45 degrees down, and sweep slowly."
        },
        "LOW_DENSITY": {
            "pattern": "ORBIT_SWEEP",
            "distance_m": 1.5,
            "pitch_deg": -25.0,
            "sweep_deg": 120.0,
            "min_frames": 75,
            "target_metric": "point_density_pts_m3",
            "default_goal": 850.0,
            "visual_template": "Orbit 120° around target center {center} at 1.5m distance to build dense multi-view parallax.",
            "tts_template": "Low point density in {cell_id}. Walk a 120-degree arc around the center point while keeping features in frame."
        },
        "BLUR": {
            "pattern": "STANDOFF_WALL",
            "distance_m": 1.8,
            "pitch_deg": 0.0,
            "sweep_deg": 60.0,
            "min_frames": 60,
            "target_metric": "blur_score",
            "default_goal": 0.88,
            "visual_template": "Hold device steady at 1.8m standoff; slow rotational velocity below 15°/sec across target wall.",
            "tts_template": "Excessive motion blur detected. Hold the camera steady at 1.8 meters and pan across the wall at half speed."
        },
        "SPECULAR_PHANTOM": {
            "pattern": "STANDOFF_WALL",
            "distance_m": 2.0,
            "pitch_deg": -15.0,
            "sweep_deg": 45.0,
            "min_frames": 40,
            "target_metric": "phantom_geometry_count",
            "default_goal": 0.0,
            "visual_template": "Step 30° oblique to reflective surface to capture true wall geometry behind glass reflection.",
            "tts_template": "Specular reflection ghost detected. Step to the side at a 30-degree angle to reveal the real wall boundary."
        },
        "DISCONNECTED_WALL": {
            "pattern": "CORNER_DOWNWARD_45",
            "distance_m": 1.5,
            "pitch_deg": -30.0,
            "sweep_deg": 90.0,
            "min_frames": 60,
            "target_metric": "disconnected_geometry_count",
            "default_goal": 0.0,
            "visual_template": "Frame wall corner junction vertically from ceiling down to floor level to bind adjacent wall panels.",
            "tts_template": "Disconnected corner junction in {cell_id}. Sweep vertically from ceiling to floor to bind both walls."
        },
        "TRACKING_BREAK": {
            "pattern": "PLANAR_SWEEP",
            "distance_m": 1.6,
            "pitch_deg": -15.0,
            "sweep_deg": 90.0,
            "min_frames": 80,
            "target_metric": "tracking_continuity_ratio",
            "default_goal": 0.98,
            "visual_template": "Begin from verified adjacent feature anchor; pan slowly toward target cell to bridge tracking gap.",
            "tts_template": "Tracking continuity break. Aim at the previously scanned doorway and advance slowly into {cell_id}."
        }
    }

    def generate_rescan_task(
        self,
        project_id: uuid.UUID,
        cell_id: str,
        region_bounds: Dict[str, Any],
        defect_type: Literal["HOLE", "LOW_DENSITY", "BLUR", "SPECULAR_PHANTOM", "DISCONNECTED_WALL", "TRACKING_BREAK"],
        detailed_reason: str,
        current_metric_value: float,
        priority: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = "HIGH",
        quality_report_id: Optional[uuid.UUID] = None,
    ) -> RescanRequest:
        """
        Synthesizes a specific, non-generic Contract 12 RescanRequest.
        """
        cfg = self.DEFECT_PATTERNS.get(defect_type, self.DEFECT_PATTERNS["LOW_DENSITY"])

        center = region_bounds.get("center_xyz", [0.0, 0.0, 1.2])
        min_xyz = region_bounds.get("min_xyz", [center[0] - 1.0, center[1] - 1.0, 0.0])
        max_xyz = region_bounds.get("max_xyz", [center[0] + 1.0, center[1] + 1.0, 2.5])
        room_id = region_bounds.get("room_id", "Primary Room")

        # Compute volume
        vol_m3 = round(
            abs(max_xyz[0] - min_xyz[0]) * abs(max_xyz[1] - min_xyz[1]) * abs(max_xyz[2] - min_xyz[2]),
            2
        )

        region = RescanRegion(
            min_xyz=min_xyz,
            max_xyz=max_xyz,
            center_xyz=center,
            room_id=room_id,
            volume_m3=vol_m3
        )

        target_bbox = RescanBoundingBox(
            min_xyz=min_xyz,
            max_xyz=max_xyz,
            center_xyz=center
        )

        # Generate localized orbit waypoints around the cell center
        dist = cfg["distance_m"]
        cx, cy, cz = center
        waypoints = [
            [round(cx + dist, 3), round(cy, 3), round(cz, 3)],
            [round(cx + dist * 0.707, 3), round(cy + dist * 0.707, 3), round(cz, 3)],
            [round(cx, 3), round(cy + dist, 3), round(cz, 3)],
        ]

        # Actionable instructions
        visual_instr = cfg["visual_template"].format(
            cell_id=cell_id,
            room=room_id,
            center=f"[{center[0]:.1f}, {center[1]:.1f}]"
        )
        audio_prompt = cfg["tts_template"].format(
            cell_id=cell_id,
            room=room_id
        )

        required_action = RequiredCaptureAction(
            capture_pattern=cfg["pattern"],
            recommended_camera_distance_m=cfg["distance_m"],
            camera_pitch_deg=cfg["pitch_deg"],
            sweep_angle_deg=cfg["sweep_deg"],
            min_frames_required=cfg["min_frames"],
            visual_instruction=visual_instr,
            audio_tts_prompt=audio_prompt,
            recommended_waypoints=waypoints
        )

        # Expected improvement
        goal_val = cfg["default_goal"]
        gain = 0.35 if priority in ["HIGH", "CRITICAL"] else 0.20

        improvement = ExpectedImprovement(
            target_metric=cfg["target_metric"],
            current_value=round(current_metric_value, 3),
            target_value=round(goal_val, 3),
            expected_confidence_gain=gain
        )

        op_guidance = OperatorGuidance(
            audio_tts_prompt=audio_prompt,
            haptic_cue="DOUBLE_VIBRATION" if priority in ["HIGH", "CRITICAL"] else "SINGLE_PULSE",
            recommended_camera_distance_m=cfg["distance_m"],
            recommended_orbit_waypoints=waypoints
        )

        request_id = f"rescan_{cell_id}_{uuid.uuid4().hex[:6]}"

        return RescanRequest(
            request_id=request_id,
            project_id=project_id,
            quality_report_id=quality_report_id,
            cell_id=cell_id,
            target_cells=[cell_id],
            region=region,
            reason=detailed_reason,
            priority=priority,
            target_bounding_box=target_bbox,
            operator_guidance=op_guidance,
            required_capture_action=required_action,
            expected_improvement=improvement,
            status="PENDING",
            created_at=datetime.now(timezone.utc).isoformat()
        )
