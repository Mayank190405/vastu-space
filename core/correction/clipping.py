"""
Structural Clipper & Opening Handler:
Clips wall polygon extents to adjacent plane intersection half-spaces,
and regularizes architectural openings (doors flush with floor, window sills).
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

class StructuralClipper:
    def __init__(self, default_door_height_m: float = 2.10, default_door_width_m: float = 0.90):
        self.default_door_height_m = default_door_height_m
        self.default_door_width_m = default_door_width_m

    def clip_wall_extents(
        self,
        wall_id: str,
        corners_3d: List[List[float]],
        bounding_box_min: List[float],
        bounding_box_max: List[float]
    ) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
        """
        Clips wall vertices that overshoot outside the room boundary bounding box.
        """
        corrections = []
        if len(corners_3d) == 0:
            return corners_3d, corrections

        clipped = []
        overshoot_clipped_count = 0
        total_overshoot_mm = 0.0

        for pt in corners_3d:
            orig = list(pt)
            new_pt = list(pt)
            for ax in range(3):
                if new_pt[ax] < bounding_box_min[ax]:
                    delta = (bounding_box_min[ax] - new_pt[ax]) * 1000.0
                    new_pt[ax] = bounding_box_min[ax]
                    total_overshoot_mm += delta
                    overshoot_clipped_count += 1
                elif new_pt[ax] > bounding_box_max[ax]:
                    delta = (new_pt[ax] - bounding_box_max[ax]) * 1000.0
                    new_pt[ax] = bounding_box_max[ax]
                    total_overshoot_mm += delta
                    overshoot_clipped_count += 1
            clipped.append(new_pt)

        if overshoot_clipped_count > 0:
            avg_overshoot_mm = total_overshoot_mm / overshoot_clipped_count
            corrections.append({
                "correction_id": f"corr_clip_extents_{wall_id}",
                "correction_type": "CLIP_EXTENTS",
                "target_id": wall_id,
                "delta_metric_value": float(round(avg_overshoot_mm, 2)),
                "delta_metric_unit": "mm",
                "confidence": 0.90,
                "description": f"Clipped {overshoot_clipped_count} overshooting vertex coordinates to bounding volume (avg: {avg_overshoot_mm:.1f}mm)"
            })

        return clipped, corrections

    def regularize_openings(
        self,
        wall_id: str,
        openings: List[Dict[str, Any]],
        floor_z: float
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Regularizes door and window openings:
        - Doors snapped to floor level: center_z = floor_z + height / 2.
        - Window sills clamped to valid sill heights (> floor_z + 0.5m).
        """
        regularized = []
        corrections = []

        for idx, op in enumerate(openings):
            op_type = op.get("opening_type", "DOOR")
            w = op.get("width_m", 0.9)
            h = op.get("height_m", 2.1)
            center = list(op.get("center_3d", [0.0, 0.0, 1.0]))

            if op_type == "DOOR":
                # Doors must touch the floor
                expected_center_z = floor_z + (h / 2.0)
                diff_mm = abs(center[2] - expected_center_z) * 1000.0
                if diff_mm > 10.0:  # > 1cm deviation
                    center[2] = float(round(expected_center_z, 4))
                    corrections.append({
                        "correction_id": f"corr_op_door_{wall_id}_{idx}",
                        "correction_type": "REGULARIZE_OPENING",
                        "target_id": f"{wall_id}_door_{idx}",
                        "delta_metric_value": float(round(diff_mm, 2)),
                        "delta_metric_unit": "mm",
                        "confidence": 0.95,
                        "description": f"Aligned door threshold to floor level (adjusted {diff_mm:.1f}mm)"
                    })
            elif op_type == "WINDOW":
                sill_z = center[2] - (h / 2.0)
                if sill_z < floor_z + 0.3:
                    # Sill too low to floor; regularize to standard 0.85m sill height
                    target_sill_z = floor_z + 0.85
                    diff_mm = abs(sill_z - target_sill_z) * 1000.0
                    center[2] = float(round(target_sill_z + h / 2.0, 4))
                    corrections.append({
                        "correction_id": f"corr_op_window_{wall_id}_{idx}",
                        "correction_type": "REGULARIZE_OPENING",
                        "target_id": f"{wall_id}_window_{idx}",
                        "delta_metric_value": float(round(diff_mm, 2)),
                        "delta_metric_unit": "mm",
                        "confidence": 0.90,
                        "description": f"Adjusted window sill height to standard 0.85m above floor (delta: {diff_mm:.1f}mm)"
                    })

            regularized.append({
                "opening_type": op_type,
                "width_m": float(round(w, 3)),
                "height_m": float(round(h, 3)),
                "center_3d": center
            })

        return regularized, corrections
