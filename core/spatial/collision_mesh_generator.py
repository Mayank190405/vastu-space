"""
VĀSTU Collision Mesh Generator (Phase 8)
Generates independent architectural collision geometry for first-person player physics:
- Floor constraints (Z = 0)
- Vertical wall collision barriers with open doorway traversal cutouts
- Furniture obstacle bounding boxes (AABBs / OBBs)
- Outer boundary restriction to prevent walking into unmapped voids
- Zero dependency on visual Gaussian splats
"""

import json
import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np

logger = logging.getLogger("vastu.spatial.collision_mesh_generator")


class CollisionMeshGenerator:
    """
    Constructs watertight collision geometry representation for Three.js capsule physics.
    """

    def __init__(
        self,
        wall_thickness_m: float = 0.15,
        player_clearance_m: float = 0.35
    ):
        self.wall_thickness_m = wall_thickness_m
        self.player_clearance_m = player_clearance_m

    def generate_room_collision(
        self,
        room_architecture: Dict[str, Any],
        world_transform: Optional[np.ndarray] = None
    ) -> Dict[str, Any]:
        """
        Generates collision primitives for a single room, transformed into world coordinates.
        
        Args:
            room_architecture: Dict produced by ArchitecturalGeometryBuilder.
            world_transform: 4x4 matrix mapping room coords to world coordinates.
            
        Returns:
            Dict containing:
                - room_id
                - floor_colliders: List of plane/box dicts
                - wall_colliders: List of box/plane colliders with doorway cutouts
                - furniture_colliders: List of AABB obstacle boxes
                - walkable_boundary_polygon: 2D polygon in world space
        """
        room_id = room_architecture["room_id"]
        ceiling_h = room_architecture.get("ceiling_height_m", 2.80)
        walls = room_architecture.get("walls", [])
        doorways = room_architecture.get("doorways", [])
        furniture = room_architecture.get("furniture_boxes", [])
        poly_2d = room_architecture.get("boundary_polygon_2d", [])

        T = world_transform if world_transform is not None else np.eye(4, dtype=np.float64)

        # 1. Transform 2D boundary polygon into world coordinates
        world_poly_2d = []
        for pt in poly_2d:
            p4 = np.array([pt[0], pt[1], 0.0, 1.0], dtype=np.float64)
            pw = T @ p4
            world_poly_2d.append([round(float(pw[0]), 3), round(float(pw[1]), 3)])

        # 2. Build wall colliders with doorway cutouts
        wall_colliders = []
        for w in walls:
            p0 = np.array([w["start_2d"][0], w["start_2d"][1], 0.0, 1.0])
            p1 = np.array([w["end_2d"][0], w["end_2d"][1], 0.0, 1.0])
            pw0 = (T @ p0)[:3]
            pw1 = (T @ p1)[:3]

            # Check if any doorway intersects this wall
            intersecting_doors = self._find_doorways_on_wall(w, doorways)

            if not intersecting_doors:
                # Solid wall collider
                wall_colliders.append({
                    "collider_id": f"col_{w['wall_id']}",
                    "type": "WALL_SEGMENT",
                    "p0": pw0.tolist(),
                    "p1": pw1.tolist(),
                    "height_m": ceiling_h,
                    "thickness_m": self.wall_thickness_m
                })
            else:
                # Wall with door opening: split wall into segments flanking the door
                # Leaving the doorway gap completely open for player transit!
                sub_segments = self._split_wall_for_doorways(pw0, pw1, intersecting_doors, T)
                for seg_idx, (sp0, sp1) in enumerate(sub_segments):
                    wall_colliders.append({
                        "collider_id": f"col_{w['wall_id']}_sub_{seg_idx}",
                        "type": "WALL_SEGMENT",
                        "p0": sp0.tolist(),
                        "p1": sp1.tolist(),
                        "height_m": ceiling_h,
                        "thickness_m": self.wall_thickness_m
                    })

        # 3. Transform furniture bounding boxes into world coordinates
        furniture_colliders = []
        for furn in furniture:
            c = np.array([furn["center_3d"][0], furn["center_3d"][1], furn["center_3d"][2], 1.0])
            cw = (T @ c)[:3]
            dims = furn.get("dimensions_m", [0.8, 0.8, 0.8])
            furniture_colliders.append({
                "collider_id": f"col_furn_{furn['object_id']}",
                "type": "FURNITURE_AABB",
                "category": furn.get("category", "FURNITURE"),
                "center_3d": cw.tolist(),
                "dimensions_m": dims,
                "min_3d": [cw[0] - dims[0]*0.5, cw[1] - dims[1]*0.5, cw[2] - dims[2]*0.5],
                "max_3d": [cw[0] + dims[0]*0.5, cw[1] + dims[1]*0.5, cw[2] + dims[2]*0.5]
            })

        # 4. Floor collider definition (plane at Z = 0)
        floor_collider = {
            "collider_id": f"col_floor_{room_id}",
            "type": "FLOOR_PLANE",
            "elevation_z": float(T[2, 3]),
            "boundary_polygon_2d": world_poly_2d
        }

        return {
            "room_id": room_id,
            "floor_collider": floor_collider,
            "wall_colliders": wall_colliders,
            "furniture_colliders": furniture_colliders,
            "walkable_boundary_polygon_2d": world_poly_2d
        }

    def _find_doorways_on_wall(
        self,
        wall: Dict[str, Any],
        doorways: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        p0 = np.array(wall["start_2d"])
        p1 = np.array(wall["end_2d"])
        wall_vec = p1 - p0
        wall_len = np.linalg.norm(wall_vec)
        if wall_len < 1e-4:
            return []

        wall_dir = wall_vec / wall_len
        matching = []

        for d in doorways:
            dc = np.array(d["center_3d"][:2])
            # Projection onto wall segment
            proj = np.dot(dc - p0, wall_dir)
            if 0.1 <= proj <= (wall_len - 0.1):
                # Perpendicular distance
                dist = np.linalg.norm((p0 + proj * wall_dir) - dc)
                if dist < 0.40:
                    matching.append({"door": d, "proj_m": proj})

        return sorted(matching, key=lambda x: x["proj_m"])

    def _split_wall_for_doorways(
        self,
        pw0: np.ndarray,
        pw1: np.ndarray,
        matching_doors: List[Dict[str, Any]],
        T: np.ndarray
    ) -> List[Tuple[np.ndarray, np.ndarray]]:
        segments = []
        curr_p = pw0
        wall_vec = pw1 - pw0
        wall_len = np.linalg.norm(wall_vec)
        if wall_len < 1e-4:
            return [(pw0, pw1)]

        wall_dir = wall_vec / wall_len

        for item in matching_doors:
            d = item["door"]
            w_half = d.get("width_m", 0.90) * 0.5
            proj = item["proj_m"]

            door_start = pw0 + wall_dir * max(0.0, proj - w_half)
            door_end = pw0 + wall_dir * min(wall_len, proj + w_half)

            if np.linalg.norm(door_start - curr_p) > 0.15:
                segments.append((curr_p, door_start))
            curr_p = door_end

        if np.linalg.norm(pw1 - curr_p) > 0.15:
            segments.append((curr_p, pw1))

        return segments if segments else [(pw0, pw1)]
