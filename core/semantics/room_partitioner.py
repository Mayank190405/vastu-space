"""
Room Semantic Detector:
Partitions reconstructed space into discrete room volumes and maps objects to enclosing rooms.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from core.schemas.semantic_object import RoomSemanticVolume

class RoomSemanticDetector:
    def __init__(self, default_room_height_m: float = 2.80):
        self.default_room_height_m = default_room_height_m
        self.rooms: List[RoomSemanticVolume] = []

    def register_room(
        self,
        room_id: str,
        name: str,
        boundary_min: List[float],
        boundary_max: List[float],
        room_type: str = "ROOM",
        confidence: float = 0.95,
        associated_cell_ids: Optional[List[str]] = None
    ) -> RoomSemanticVolume:
        """Registers a defined architectural room volume."""
        b_min = np.array(boundary_min)
        b_max = np.array(boundary_max)
        center = ((b_min + b_max) / 2.0).tolist()
        dx = float(b_max[0] - b_min[0])
        dy = float(b_max[1] - b_min[1])
        area = max(dx * dy, 1.0)

        room = RoomSemanticVolume(
            room_id=room_id,
            name=name,
            room_type=room_type,
            boundary_min=[float(round(v, 3)) for v in boundary_min],
            boundary_max=[float(round(v, 3)) for v in boundary_max],
            center=[float(round(v, 3)) for v in center],
            surface_area_m2=float(round(area, 2)),
            confidence=confidence,
            associated_cell_ids=associated_cell_ids or []
        )
        self.rooms.append(room)
        return room

    def find_enclosing_room(self, position_3d: List[float]) -> Optional[str]:
        """
        Finds the room_id of the room containing the given 3D position [x, y, z].
        """
        p = np.array(position_3d)
        for r in self.rooms:
            b_min = np.array(r.boundary_min) - 0.05  # slight tolerance
            b_max = np.array(r.boundary_max) + 0.05
            if np.all(p >= b_min) and np.all(p <= b_max):
                return r.room_id

        # If not strictly inside, find closest room within 1 meter
        closest_room = None
        min_dist = 1.0
        for r in self.rooms:
            c = np.array(r.center)
            d = float(np.linalg.norm(p - c))
            if d < min_dist:
                min_dist = d
                closest_room = r.room_id

        return closest_room

    def get_all_rooms(self) -> List[RoomSemanticVolume]:
        return list(self.rooms)
