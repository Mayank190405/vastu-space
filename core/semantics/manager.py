"""
Semantic Scene Manager:
Maintains the global semantic scene graph, links objects to spatial cells and rooms,
and produces auditable SemanticSceneManifest artifacts.
"""

from typing import List, Dict, Any, Optional
import uuid
import numpy as np

from core.schemas.semantic_object import (
    SemanticObject,
    RoomSemanticVolume,
    SemanticSceneManifest
)
from core.semantics.room_partitioner import RoomSemanticDetector

class SemanticSceneManager:
    def __init__(self, scene_id: Optional[str] = None):
        self.scene_id = scene_id or f"scene_{uuid.uuid4().hex[:8]}"
        self.room_detector = RoomSemanticDetector()
        self.objects: Dict[str, SemanticObject] = {}

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
        """Registers a room volume in the scene."""
        return self.room_detector.register_room(
            room_id=room_id,
            name=name,
            boundary_min=boundary_min,
            boundary_max=boundary_max,
            room_type=room_type,
            confidence=confidence,
            associated_cell_ids=associated_cell_ids
        )

    def add_object(self, obj: SemanticObject) -> None:
        """Adds or updates a semantic object."""
        # Ensure room_id is set if not already present
        if not obj.room_id:
            obj.room_id = self.room_detector.find_enclosing_room(obj.position)
        self.objects[obj.object_id] = obj

    def get_object(self, object_id: str) -> Optional[SemanticObject]:
        return self.objects.get(object_id)

    def get_objects_by_class(self, class_name: str) -> List[SemanticObject]:
        return [obj for obj in self.objects.values() if obj.class_name == class_name]

    def get_objects_by_room(self, room_id: str) -> List[SemanticObject]:
        return [obj for obj in self.objects.values() if obj.room_id == room_id]

    def get_ground_truth_objects(self) -> List[SemanticObject]:
        """Returns only confirmed ground truth candidates (never low-confidence provisional items)."""
        return [obj for obj in self.objects.values() if obj.is_ground_truth_candidate]

    def get_provisional_objects(self) -> List[SemanticObject]:
        """Returns low-confidence provisional detections."""
        return [obj for obj in self.objects.values() if not obj.is_ground_truth_candidate]

    def find_objects_near(self, position_3d: List[float], radius_m: float = 2.0) -> List[SemanticObject]:
        """Finds objects within a radius in meters from the given 3D position."""
        target = np.array(position_3d)
        matched = []
        for obj in self.objects.values():
            pos = np.array(obj.position)
            if np.linalg.norm(pos - target) <= radius_m:
                matched.append(obj)
        return matched

    def export_manifest(self) -> SemanticSceneManifest:
        """Produces a validated Pydantic SemanticSceneManifest."""
        all_objs = list(self.objects.values())
        gt_count = sum(1 for o in all_objs if o.is_ground_truth_candidate)
        prov_count = len(all_objs) - gt_count

        return SemanticSceneManifest(
            scene_id=self.scene_id,
            rooms=self.room_detector.get_all_rooms(),
            objects=all_objs,
            unconfirmed_provisional_count=prov_count,
            ground_truth_objects_count=gt_count,
            metadata={
                "total_objects": len(all_objs),
                "total_rooms": len(self.room_detector.get_all_rooms())
            }
        )
