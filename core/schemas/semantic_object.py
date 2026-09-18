"""
Contract 8: Semantic Object Schema
Version: 1.1.0
Producer: Semantic Reconstruction Engine
Consumer: Search Service, POI Auto-Generator, Spatial Query API, Indoor Navigation
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, model_validator

class OrientedBoundingBox(BaseModel):
    center: List[float] = Field(min_length=3, max_length=3)
    extent_dx_dy_dz: List[float] = Field(min_length=3, max_length=3)
    rotation_quaternion: List[float] = Field(min_length=4, max_length=4)

class SemanticObject(BaseModel):
    object_id: str
    class_name: str
    label: str = ""
    category: str = "GENERAL"
    position: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3)
    oriented_bounding_box: OrientedBoundingBox
    room_id: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    source_observations: List[str] = Field(default_factory=list)
    is_ground_truth_candidate: bool = True
    status: Literal["PROVISIONAL", "CONFIRMED", "GROUND_TRUTH_REJECTED"] = "CONFIRMED"
    associated_cell_ids: List[str] = Field(default_factory=list)
    parent_surface_id: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def populate_defaults(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # Auto-populate label if not provided
            if not data.get("label"):
                class_name = data.get("class_name", "object")
                data["label"] = class_name.replace("_", " ").title()
            
            # Auto-populate position from oriented_bounding_box.center if missing or zero
            obb = data.get("oriented_bounding_box")
            if obb and "position" not in data:
                if isinstance(obb, dict) and "center" in obb:
                    data["position"] = list(obb["center"])
                elif hasattr(obb, "center"):
                    data["position"] = list(obb.center)

            # Ground truth policy: if confidence < 0.70, never mark as ground truth candidate
            conf = data.get("confidence", 1.0)
            if conf < 0.70:
                data["is_ground_truth_candidate"] = False
                data["status"] = "PROVISIONAL"
        return data

class RoomSemanticVolume(BaseModel):
    room_id: str
    name: str
    room_type: str = "ROOM"
    boundary_min: List[float] = Field(min_length=3, max_length=3)
    boundary_max: List[float] = Field(min_length=3, max_length=3)
    center: List[float] = Field(min_length=3, max_length=3)
    surface_area_m2: float = Field(ge=0.0)
    confidence: float = Field(ge=0.0, le=1.0)
    associated_cell_ids: List[str] = Field(default_factory=list)

class SemanticSceneManifest(BaseModel):
    scene_id: str
    rooms: List[RoomSemanticVolume] = Field(default_factory=list)
    objects: List[SemanticObject] = Field(default_factory=list)
    unconfirmed_provisional_count: int = Field(default=0, ge=0)
    ground_truth_objects_count: int = Field(default=0, ge=0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
