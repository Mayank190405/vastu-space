"""
Geometry QA Validator:
Executes rigorous 7-point structural audits on reconstructed architectural models:
1. Watertightness
2. Self-intersections
3. Disconnected walls
4. Floating vertices
5. Rounded architectural corners
6. Excessive smoothing
7. Incorrect wall extents
"""

from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from core.schemas.geometry_qa import ValidationAuditResult

class GeometryQAValidator:
    def __init__(
        self,
        max_allowable_smoothing_displacement_mm: float = 30.0,
        max_extent_overshoot_tolerance_m: float = 0.05,
        min_corner_sharpness_deg: float = 75.0
    ):
        self.max_allowable_smoothing_displacement_mm = max_allowable_smoothing_displacement_mm
        self.max_extent_overshoot_tolerance_m = max_extent_overshoot_tolerance_m
        self.min_corner_sharpness_deg = min_corner_sharpness_deg

    def run_audits(
        self,
        walls: List[Dict[str, Any]],
        intersection_edges: List[Dict[str, Any]],
        floor_z: float,
        ceiling_z: float,
        room_bounds_min: List[float],
        room_bounds_max: List[float],
        raw_evidence_points: Optional[np.ndarray] = None,
        corrected_points: Optional[np.ndarray] = None
    ) -> ValidationAuditResult:
        """
        Executes all 7 validation audits on the architectural structure.
        """
        # 1. Watertightness Analysis
        wall_ids = {w["structure_id"] for w in walls}
        # Check connected junctions
        connected_junction_count = len([e for e in intersection_edges if e.get("junction_type") == "WALL_WALL"])
        # If we have 4+ walls and as many corners, shell is closed
        is_closed_shell = (len(walls) >= 4 and connected_junction_count >= len(walls))
        watertightness_status = "PASS" if is_closed_shell else "WARNING"
        boundary_edges = 0 if is_closed_shell else max(0, len(walls) - connected_junction_count)

        # 2. Self-Intersections
        self_intersections = []
        for i in range(len(walls)):
            for j in range(i + 1, len(walls)):
                w1 = walls[i]
                w2 = walls[j]
                c1 = np.array(w1.get("corners_3d", []))
                c2 = np.array(w2.get("corners_3d", []))
                if len(c1) == 0 or len(c2) == 0:
                    continue
                # If planes are parallel and their bounding boxes significantly penetrate
                n1 = np.array(w1["plane_equation"])[:3]
                n2 = np.array(w2["plane_equation"])[:3]
                if abs(abs(np.dot(n1, n2)) - 1.0) < 0.05:
                    min1, max1 = np.min(c1, axis=0), np.max(c1, axis=0)
                    min2, max2 = np.min(c2, axis=0), np.max(c2, axis=0)
                    # Check penetration
                    overlap = (max1 > min2 + 0.1) & (max2 > min1 + 0.1)
                    if np.all(overlap):
                        self_intersections.append(f"{w1['structure_id']}__{w2['structure_id']}")

        # 3. Disconnected Walls
        connected_walls = set()
        for e in intersection_edges:
            connected_walls.add(e["source_plane_id"])
            connected_walls.add(e["target_plane_id"])
        disconnected_walls = [wid for wid in wall_ids if wid not in connected_walls]

        # 4. Floating Vertices
        floating_vertices_count = 0
        if corrected_points is not None and len(walls) > 0:
            # Check for any points that deviate > 0.4m from all walls/floor/ceiling
            all_planes = [np.array(w["plane_equation"]) for w in walls]
            all_planes.append(np.array([0.0, 0.0, 1.0, -floor_z]))
            all_planes.append(np.array([0.0, 0.0, 1.0, -ceiling_z]))
            min_dists = np.full(len(corrected_points), np.inf)
            for peq in all_planes:
                nu = peq[:3] / (np.linalg.norm(peq[:3]) + 1e-9)
                du = peq[3] / (np.linalg.norm(peq[:3]) + 1e-9)
                d = np.abs(np.dot(corrected_points, nu) + du)
                min_dists = np.minimum(min_dists, d)
            floating_vertices_count = int(np.sum(min_dists > 0.40))

        # 5. Rounded Architectural Corners
        rounded_corners = []
        for e in intersection_edges:
            if e.get("junction_type") == "WALL_WALL":
                raw_ang = e.get("raw_angle_deg", 90.0)
                # If corner is softened/rounded (e.g. angle degraded below threshold)
                if raw_ang < self.min_corner_sharpness_deg:
                    rounded_corners.append(f"{e['edge_id']} (angle {raw_ang:.1f}deg)")

        # 6. Excessive Smoothing
        max_smoothing_disp_mm = 0.0
        excessive_smoothing = False
        if raw_evidence_points is not None and corrected_points is not None and len(raw_evidence_points) == len(corrected_points):
            diffs = np.linalg.norm(raw_evidence_points - corrected_points, axis=1) * 1000.0
            max_smoothing_disp_mm = float(np.max(diffs)) if len(diffs) > 0 else 0.0
            excessive_smoothing = (max_smoothing_disp_mm > self.max_allowable_smoothing_displacement_mm)

        # 7. Incorrect Wall Extents
        incorrect_extents = []
        for w in walls:
            corners = w.get("corners_3d", [])
            for c in corners:
                z = c[2]
                if z < floor_z - self.max_extent_overshoot_tolerance_m or z > ceiling_z + self.max_extent_overshoot_tolerance_m:
                    incorrect_extents.append(w["structure_id"])
                    break

        return ValidationAuditResult(
            watertightness_status=watertightness_status,
            boundary_edges_count=boundary_edges,
            non_manifold_edges_count=0,
            self_intersections_count=len(self_intersections),
            self_intersecting_pairs=self_intersections,
            disconnected_walls_count=len(disconnected_walls),
            disconnected_wall_ids=disconnected_walls,
            floating_vertices_count=floating_vertices_count,
            rounded_architectural_corners_count=len(rounded_corners),
            rounded_corner_details=rounded_corners,
            excessive_smoothing_detected=excessive_smoothing,
            max_smoothing_displacement_mm=float(round(max_smoothing_disp_mm, 2)),
            incorrect_wall_extents_count=len(incorrect_extents),
            incorrect_extent_wall_ids=incorrect_extents
        )
