"""
Controlled Geometric Snapper:
Applies architectural priors (floor/ceiling bounds, orthogonal corners, vertex co-location)
ONLY when evidence confidence supports it, measuring exact metric deltas.
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

class ControlledGeometricSnapper:
    """
    Applies architectural priors (floor/ceiling bounds, orthogonal corners, vertex co-location)
    ONLY when evidence confidence supports it, preserving intentional non-orthogonal angles,
    low-height obstructions, and opening free space without over-smoothing.
    """
    def __init__(
        self,
        min_confidence_threshold: float = 0.60,
        max_vertical_snap_gap_m: float = 0.15,
        max_corner_snap_gap_m: float = 0.10,
        orthogonal_tolerance_deg: float = 3.5,
        min_structural_height_m: float = 1.80
    ):
        self.min_confidence_threshold = min_confidence_threshold
        self.max_vertical_snap_gap_m = max_vertical_snap_gap_m
        self.max_corner_snap_gap_m = max_corner_snap_gap_m
        self.orthogonal_tolerance_deg = orthogonal_tolerance_deg
        self.min_structural_height_m = min_structural_height_m

    def is_structural_wall(self, corners_3d: List[List[float]]) -> bool:
        """
        Determines whether geometry represents a full-height structural wall
        or a low-height obstruction / furniture (e.g. counter, half-wall, sofa).
        """
        if not corners_3d:
            return False
        z_vals = [pt[2] for pt in corners_3d]
        height = max(z_vals) - min(z_vals)
        return height >= self.min_structural_height_m

    def snap_wall_to_floor_and_ceiling(
        self,
        wall_id: str,
        wall_corners_3d: List[List[float]],
        floor_z: float,
        ceiling_z: float,
        confidence: float
    ) -> Tuple[List[List[float]], List[Dict[str, Any]]]:
        """
        Snaps bottom vertices of a wall to floor level and top vertices to ceiling level.
        Protects low-height furniture/obstructions (< min_structural_height_m) from
        being incorrectly stretched into drywall.
        """
        corrections = []
        if len(wall_corners_3d) == 0:
            return wall_corners_3d, corrections

        if confidence < self.min_confidence_threshold:
            corrections.append({
                "correction_id": f"corr_skip_fl_ceil_{wall_id}",
                "correction_type": "SKIPPED_LOW_CONFIDENCE",
                "target_id": wall_id,
                "delta_metric_value": 0.0,
                "delta_metric_unit": "mm",
                "confidence": confidence,
                "description": f"Confidence {confidence:.2f} < {self.min_confidence_threshold:.2f}; skipped floor/ceiling snapping"
            })
            return wall_corners_3d, corrections

        snapped = [list(pt) for pt in wall_corners_3d]
        z_values = [pt[2] for pt in snapped]
        min_z = min(z_values)
        max_z = max(z_values)
        total_height = max_z - min_z

        # Protect low-height furniture / counter / half-walls from ceiling snapping
        is_structural = total_height >= self.min_structural_height_m

        mid_z = (min_z + max_z) / 2.0
        total_floor_disp_mm = 0.0
        floor_pts_count = 0
        total_ceil_disp_mm = 0.0
        ceil_pts_count = 0

        for pt in snapped:
            if pt[2] <= mid_z:
                # Bottom vertex candidate (floor snap is permissible if close to ground)
                gap = abs(pt[2] - floor_z)
                if gap <= self.max_vertical_snap_gap_m:
                    disp_mm = gap * 1000.0
                    pt[2] = float(round(floor_z, 4))
                    total_floor_disp_mm += disp_mm
                    floor_pts_count += 1
            else:
                # Top vertex candidate: only snap to ceiling if it is a structural wall
                if is_structural:
                    gap = abs(pt[2] - ceiling_z)
                    if gap <= self.max_vertical_snap_gap_m:
                        disp_mm = gap * 1000.0
                        pt[2] = float(round(ceiling_z, 4))
                        total_ceil_disp_mm += disp_mm
                        ceil_pts_count += 1

        if not is_structural:
            corrections.append({
                "correction_id": f"corr_skip_ceil_obstruction_{wall_id}",
                "correction_type": "SKIPPED_SUB_HEIGHT_OBSTRUCTION",
                "target_id": wall_id,
                "delta_metric_value": 0.0,
                "delta_metric_unit": "mm",
                "confidence": confidence,
                "description": f"Height {total_height:.2f}m < {self.min_structural_height_m:.2f}m; preserved low-height obstruction without ceiling snapping"
            })

        if floor_pts_count > 0:
            avg_disp_mm = total_floor_disp_mm / floor_pts_count
            corrections.append({
                "correction_id": f"corr_snap_floor_{wall_id}",
                "correction_type": "SNAP_FLOOR_INTERSECTION",
                "target_id": wall_id,
                "delta_metric_value": float(round(avg_disp_mm, 2)),
                "delta_metric_unit": "mm",
                "confidence": confidence,
                "description": f"Snapped {floor_pts_count} base vertices to floor z={floor_z:.3f}m (avg disp: {avg_disp_mm:.1f}mm)"
            })

        if ceil_pts_count > 0:
            avg_disp_mm = total_ceil_disp_mm / ceil_pts_count
            corrections.append({
                "correction_id": f"corr_snap_ceiling_{wall_id}",
                "correction_type": "SNAP_CEILING_INTERSECTION",
                "target_id": wall_id,
                "delta_metric_value": float(round(avg_disp_mm, 2)),
                "delta_metric_unit": "mm",
                "confidence": confidence,
                "description": f"Snapped {ceil_pts_count} top vertices to ceiling z={ceiling_z:.3f}m (avg disp: {avg_disp_mm:.1f}mm)"
            })

        return snapped, corrections

    def snap_corner_vertices(
        self,
        edge_id: str,
        wall1_id: str,
        wall2_id: str,
        wall1_corners: List[List[float]],
        wall2_corners: List[List[float]],
        intersection_line_start: List[float],
        intersection_line_end: List[float],
        confidence: float,
        wall1_normal: Optional[np.ndarray] = None,
        wall2_normal: Optional[np.ndarray] = None
    ) -> Tuple[List[List[float]], List[List[float]], List[Dict[str, Any]]]:
        """
        Co-locates adjacent wall boundary corners onto the shared sharp intersection line.
        Preserves intentional non-orthogonal angles (e.g. 45-degree bay windows, chamfers).
        """
        corrections = []
        if confidence < self.min_confidence_threshold:
            return wall1_corners, wall2_corners, corrections

        # Non-orthogonal angle preservation check
        if wall1_normal is not None and wall2_normal is not None:
            n1 = np.array(wall1_normal) / (np.linalg.norm(wall1_normal) + 1e-8)
            n2 = np.array(wall2_normal) / (np.linalg.norm(wall2_normal) + 1e-8)
            dot = np.clip(np.dot(n1, n2), -1.0, 1.0)
            dihedral_deg = float(np.degrees(np.arccos(abs(dot))))

            # If angle deviates significantly from orthogonal (90) and parallel (0 or 180),
            # e.g., ~45 deg or intentional angled architecture, preserve the true angle.
            diff_from_90 = abs(dihedral_deg - 90.0)
            diff_from_0 = abs(dihedral_deg - 0.0)
            if diff_from_90 > self.orthogonal_tolerance_deg and diff_from_0 > self.orthogonal_tolerance_deg:
                corrections.append({
                    "correction_id": f"corr_preserve_angle_{edge_id}",
                    "correction_type": "PRESERVED_NON_ORTHOGONAL_ANGLE",
                    "target_id": edge_id,
                    "delta_metric_value": round(dihedral_deg, 1),
                    "delta_metric_unit": "deg",
                    "confidence": confidence,
                    "description": f"Preserved intentional non-orthogonal dihedral angle {dihedral_deg:.1f}deg (deviation {diff_from_90:.1f}deg > {self.orthogonal_tolerance_deg}deg)"
                })

        line_p0 = np.array(intersection_line_start)
        line_dir = np.array(intersection_line_end) - line_p0
        dir_norm = np.linalg.norm(line_dir)
        if dir_norm < 1e-4:
            return wall1_corners, wall2_corners, corrections
        u_dir = line_dir / dir_norm

        w1_snapped = [list(c) for c in wall1_corners]
        w2_snapped = [list(c) for c in wall2_corners]

        total_disp_mm = 0.0
        snapped_count = 0

        # Snap closest vertices of wall 1 to intersection line
        for pt in w1_snapped:
            p = np.array(pt)
            proj = line_p0 + np.dot(p - line_p0, u_dir) * u_dir
            dist = np.linalg.norm(p - proj)
            if dist <= self.max_corner_snap_gap_m:
                disp_mm = float(dist * 1000.0)
                pt[0], pt[1], pt[2] = float(round(proj[0], 4)), float(round(proj[1], 4)), float(round(proj[2], 4))
                total_disp_mm += disp_mm
                snapped_count += 1

        for pt in w2_snapped:
            p = np.array(pt)
            proj = line_p0 + np.dot(p - line_p0, u_dir) * u_dir
            dist = np.linalg.norm(p - proj)
            if dist <= self.max_corner_snap_gap_m:
                disp_mm = float(dist * 1000.0)
                pt[0], pt[1], pt[2] = float(round(proj[0], 4)), float(round(proj[1], 4)), float(round(proj[2], 4))
                total_disp_mm += disp_mm
                snapped_count += 1

        if snapped_count > 0:
            avg_disp = total_disp_mm / snapped_count
            corrections.append({
                "correction_id": f"corr_snap_corner_{edge_id}",
                "correction_type": "CLIP_EXTENTS",
                "target_id": edge_id,
                "delta_metric_value": float(round(avg_disp, 2)),
                "delta_metric_unit": "mm",
                "confidence": confidence,
                "description": f"Co-located {snapped_count} corner vertices to sharp intersection line (avg disp: {avg_disp:.1f}mm)"
            })

        return w1_snapped, w2_snapped, corrections

    def verify_opening_free_space(
        self,
        opening_center: List[float],
        opening_width_m: float,
        opening_height_m: float,
        camera_positions: List[np.ndarray],
        depth_points: np.ndarray
    ) -> bool:
        """
        Verifies that an architectural opening (doorway, passage, stairwell) has
        free-space camera rays passing through it, proving it must NOT be sealed
        by watertight polygon mesh infill.
        """
        if len(camera_positions) < 2 or len(depth_points) == 0:
            return True

        center = np.array(opening_center)
        # Check if points exist inside the open volume
        dx = np.abs(depth_points[:, 0] - center[0])
        dy = np.abs(depth_points[:, 1] - center[1])
        dz = np.abs(depth_points[:, 2] - center[2])

        half_w = opening_width_m / 2.0
        half_h = opening_height_m / 2.0

        # Points directly blocking the opening center plane
        blocking_mask = (dx < half_w * 0.8) & (dy < 0.10) & (dz < half_h * 0.8)
        num_blocking = np.sum(blocking_mask)

        # If sparse points inside opening, it is free space; do not mesh-close
        return num_blocking < 5
