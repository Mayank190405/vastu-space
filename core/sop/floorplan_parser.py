"""
VĀSTU Capture SOP Engine: Floorplan-to-SOP Blueprint Parser
Parses 2D vector floorplans (drawing data, walls, doors, windows) or metric floor specs
into structured architectural capture SOPs attached to the capture session.
Runs 100% offline with zero cloud API dependencies.
"""

from typing import Dict, Any, List, Optional, Tuple
import math
from pydantic import BaseModel, Field


class WallSegment(BaseModel):
    id: str
    start: Tuple[float, float]
    end: Tuple[float, float]
    length_m: float
    angle_deg: float
    wall_type: str = "interior"


class FloorplanTargetZone(BaseModel):
    id: str
    name: str
    sequence: int
    sector_bbox: Dict[str, float]  # {"x": ..., "y": ..., "width": ..., "height": ...}
    instructions: str
    zone_mistakes: str
    target_duration_sec: int
    key_features: List[str]
    status: str = "PENDING"
    wall_ids: List[str] = Field(default_factory=list)


class FloorplanCaptureSOP(BaseModel):
    summary: str
    recommended_start_zone: str
    global_guidelines: Dict[str, str]
    mistakes_to_avoid: List[Dict[str, str]]
    zones: List[FloorplanTargetZone]
    metric_targets: Dict[str, Any]


class FloorplanSOPParser:
    """
    Deterministically transforms 2D vector blueprint data or room metric parameters
    into an on-device Capture SOP graph with spatial targets.
    """

    DEFAULT_PIXELS_PER_METER = 50.0  # Default canvas scale if unspecified

    @classmethod
    def parse(
        cls,
        drawing_data: Optional[Dict[str, Any]] = None,
        canvas_width: float = 1200.0,
        canvas_height: float = 800.0,
        scale_ratio: float = 1.0,
        floor_name: str = "Main Floor",
        area_sqft: float = 400.0,
        height_ft: float = 10.0,
        project_type: str = "Residential"
    ) -> Dict[str, Any]:
        """
        Parses floorplan drawing data or dimensions into a standard Capture SOP dictionary.
        """
        objects = []
        if drawing_data and isinstance(drawing_data, dict):
            objects = drawing_data.get("objects", [])

        # Determine effective scale (canvas pixels to meters)
        # scale_ratio represents units per pixel or scale multiplier
        pixels_per_meter = cls.DEFAULT_PIXELS_PER_METER * (scale_ratio if scale_ratio > 0 else 1.0)

        walls: List[WallSegment] = []
        doors: List[Dict[str, Any]] = []
        windows: List[Dict[str, Any]] = []
        rooms: List[Dict[str, Any]] = []

        for idx, obj in enumerate(objects):
            obj_type = obj.get("type", "").lower()
            obj_id = obj.get("id", f"obj_{idx}")

            if obj_type == "wall":
                pts = obj.get("points", [])
                if len(pts) >= 2:
                    p1 = pts[0]
                    p2 = pts[1]
                    dx = (p2.get("x", 0) - p1.get("x", 0)) / pixels_per_meter
                    dy = (p2.get("y", 0) - p1.get("y", 0)) / pixels_per_meter
                    length = math.hypot(dx, dy)
                    angle = math.degrees(math.atan2(dy, dx)) % 360.0
                    walls.append(WallSegment(
                        id=obj_id,
                        start=(p1.get("x", 0) / pixels_per_meter, p1.get("y", 0) / pixels_per_meter),
                        end=(p2.get("x", 0) / pixels_per_meter, p2.get("y", 0) / pixels_per_meter),
                        length_m=round(length, 2),
                        angle_deg=round(angle, 1)
                    ))
            elif obj_type == "door":
                doors.append(obj)
            elif obj_type == "window":
                windows.append(obj)
            elif obj_type in ("room", "rect", "polygon"):
                rooms.append(obj)

        # If no walls or rooms were explicitly drawn, synthesize standard room walls from dimensions
        if not walls and not rooms:
            # Estimate metric dimensions from area_sqft (1 sqm = 10.7639 sqft)
            area_sqm = max(12.0, area_sqft / 10.7639)
            # Default aspect ratio 1.3:1
            width_m = round(math.sqrt(area_sqm * 1.3), 2)
            length_m = round(area_sqm / width_m, 2)
            height_m = round(height_ft * 0.3048, 2)

            walls = [
                WallSegment(id="wall_north", start=(0.0, 0.0), end=(width_m, 0.0), length_m=width_m, angle_deg=0.0),
                WallSegment(id="wall_east", start=(width_m, 0.0), end=(width_m, length_m), length_m=length_m, angle_deg=90.0),
                WallSegment(id="wall_south", start=(width_m, length_m), end=(0.0, length_m), length_m=width_m, angle_deg=180.0),
                WallSegment(id="wall_west", start=(0.0, length_m), end=(0.0, 0.0), length_m=length_m, angle_deg=270.0),
            ]
        else:
            # Calculate bounds
            xs = [w.start[0] for w in walls] + [w.end[0] for w in walls]
            ys = [w.start[1] for w in walls] + [w.end[1] for w in walls]
            min_x, max_x = min(xs, default=0.0), max(xs, default=5.0)
            min_y, max_y = min(ys, default=0.0), max(ys, default=5.0)
            width_m = round(max(3.0, max_x - min_x), 2)
            length_m = round(max(3.0, max_y - min_y), 2)
            height_m = round(height_ft * 0.3048, 2)

        # Generate Zones
        zones: List[FloorplanTargetZone] = []

        # Zone 1: Entry / Foyer
        entry_bbox = {
            "x": 40.0,
            "y": 40.0,
            "width": round(canvas_width * 0.3, 1),
            "height": round(canvas_height * 0.25, 1)
        }
        zones.append(FloorplanTargetZone(
            id="zone_1_entry",
            name=f"{floor_name} — Entrance Threshold & Baseline",
            sequence=1,
            sector_bbox=entry_bbox,
            instructions="Stand at the main room doorway. Hold phone steady at chest height for 3 seconds to establish initial visual SLAM baseline.",
            zone_mistakes="Do not step forward before the baseline confirms; avoid pointing directly into hallway bright glare.",
            target_duration_sec=15,
            key_features=["Doorway jamb", "Threshold boundary", "Baseboards"]
        ))

        # Zone 2: Perimeter Walls
        perimeter_bbox = {
            "x": 20.0,
            "y": 20.0,
            "width": round(canvas_width * 0.9, 1),
            "height": round(canvas_height * 0.9, 1)
        }
        zones.append(FloorplanTargetZone(
            id="zone_2_perimeter",
            name=f"{floor_name} — Outer Perimeter Wall Loop",
            sequence=2,
            sector_bbox=perimeter_bbox,
            instructions=f"Walk slowly in a continuous clockwise perimeter loop (~{round(2 * (width_m + length_m), 1)}m path). Maintain 1.5m distance from walls.",
            zone_mistakes="CRITICAL: Do NOT twist in place without translating! Walk sideways along the perimeter to maintain parallax baseline.",
            target_duration_sec=max(30, int((width_m + length_m) * 3)),
            key_features=["Wall planes", "Wall-floor junction", "Corners"],
            wall_ids=[w.id for w in walls]
        ))

        # Zone 3: Corners & Architectural Openings
        corners_bbox = {
            "x": 60.0,
            "y": 60.0,
            "width": round(canvas_width * 0.8, 1),
            "height": round(canvas_height * 0.8, 1)
        }
        zones.append(FloorplanTargetZone(
            id="zone_3_corners_openings",
            name=f"{floor_name} — Corners, Doors & Windows",
            sequence=3,
            sector_bbox=corners_bbox,
            instructions="At each of the 4 room corners and window frames, perform a slow vertical arc from floor baseboard to ceiling junction.",
            zone_mistakes="Do not pan faster than 15 deg/sec; angle phone 15° down when framing windows to avoid blowout.",
            target_duration_sec=25,
            key_features=["Wall corners", "Window frames", "Ceiling-wall joints"]
        ))

        # Zone 4: Floor & Baseboards
        floor_bbox = {
            "x": round(canvas_width * 0.2, 1),
            "y": round(canvas_height * 0.2, 1),
            "width": round(canvas_width * 0.6, 1),
            "height": round(canvas_height * 0.6, 1)
        }
        zones.append(FloorplanTargetZone(
            id="zone_4_floor_central",
            name=f"{floor_name} — Floor Surface & Center Traversal",
            sequence=4,
            sector_bbox=floor_bbox,
            instructions="Tilt camera 20° downward. Walk across the room center to capture floor surface and central furniture anchors.",
            zone_mistakes="Ensure floor pattern and skirting boards remain in lower 40% of frame to avoid floor mesh holes.",
            target_duration_sec=25,
            key_features=["Floor tiles/hardwood", "Furniture feet", "Central rug/carpet"]
        ))

        # Zone 5: Loop Closure Return
        zones.append(FloorplanTargetZone(
            id="zone_5_loop_closure",
            name=f"{floor_name} — Loop Closure & Verification",
            sequence=5,
            sector_bbox=entry_bbox,
            instructions="Return to the original entrance doorway. Align view with the initial start frame until loop closure confirms.",
            zone_mistakes="Do not stop capture early before 85% coverage is confirmed by the co-pilot.",
            target_duration_sec=15,
            key_features=["Original entry frame", "Starting anchor points"]
        ))

        # Global Mistakes
        mistakes_to_avoid = [
            {
                "id": "m_pure_rotation",
                "severity": "CRITICAL",
                "title": "Twisting In Place (No Translation Baseline)",
                "description": "Never pivot or rotate on your heels without walking. Monocular depth collapses without sideways translation.",
                "visual_trigger": "Angular velocity > 15 deg/s with linear velocity < 0.15 m/s"
            },
            {
                "id": "m_rapid_motion",
                "severity": "CRITICAL",
                "title": "Rapid Pan Motion Blur",
                "description": "Keep walking pace at 0.3 - 0.5 m/s. Avoid jerky turns.",
                "visual_trigger": "Linear speed > 0.8 m/s or gyro > 1.2 rad/s"
            },
            {
                "id": "m_skipped_floor",
                "severity": "HIGH",
                "title": "Skipped Floor Foreground",
                "description": "Do not keep the camera strictly horizontal. Keep floor and baseboards visible in lower frame to prevent floor cutouts.",
                "visual_trigger": "Floor coverage < 80%"
            },
            {
                "id": "m_window_glare",
                "severity": "MEDIUM",
                "title": "Window & Skylight Glare",
                "description": "Tilt phone slightly downward when facing bright windows to avoid sensor saturation.",
                "visual_trigger": "Direct sunlight / bright exterior glass"
            }
        ]

        metric_targets = {
            "room_dimensions_m": {
                "width": width_m,
                "length": length_m,
                "height": height_m,
                "area_sqm": round(width_m * length_m, 2)
            },
            "walls": [w.model_dump() for w in walls],
            "corners_count": len(walls),
            "floor_polygon_m": [
                {"x": 0.0, "y": 0.0},
                {"x": width_m, "y": 0.0},
                {"x": width_m, "y": length_m},
                {"x": 0.0, "y": length_m}
            ],
            "required_coverage_fraction": 0.85,
            "required_floor_fraction": 0.80,
            "required_wall_fraction": 0.70
        }

        sop_dict = {
            "summary": f"Architectural SOP for {floor_name} ({width_m}m x {length_m}m, {round(width_m * length_m, 1)} m²). 5 guided zones with translation baseline and 85% gated completion.",
            "recommended_start_zone": "zone_1_entry",
            "global_guidelines": {
                "speed": "0.3 - 0.5 m/s steady pacing",
                "phone_tilt": "15° downward tilt toward floor-wall boundary",
                "phone_height": "1.2 - 1.4 m chest height with dual hand stabilization",
                "overlap_percentage": "65-75% visual feature overlap",
                "lighting_note": "Keep room lights fully on; avoid direct backlight into bright windows"
            },
            "mistakes_to_avoid": mistakes_to_avoid,
            "zones": [z.model_dump() for z in zones],
            "metric_targets": metric_targets
        }

        return sop_dict
