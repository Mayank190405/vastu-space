"""
Contract 9: Point of Interest (POI) Schema
Version: 2.0.0
Producer: User UI / Semantic Auto-Promotion / Raycast Placement Engine
Consumer: Web Viewer, Search Engine, Navigation Routing, BIM Sync
"""

import uuid
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, model_validator

class POICoordinates(BaseModel):
    x: float
    y: float
    z: float

    def to_list(self) -> List[float]:
        return [self.x, self.y, self.z]

class POICameraViewpoint(BaseModel):
    position: List[float] = Field(min_length=3, max_length=3)
    look_at: List[float] = Field(min_length=3, max_length=3)

class POIAttachment(BaseModel):
    filename: str
    s3_key: str
    content_type: Optional[str] = None

class PointOfInterest(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    poi_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    name: str = Field(default="Point of Interest")
    title: str = Field(default="Point of Interest")
    aliases: List[str] = Field(default_factory=list)
    category: str = "GENERAL"
    coordinates: POICoordinates
    coordinates_m: POICoordinates
    room: Optional[str] = None
    geometry: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    custom_metadata: Dict[str, str] = Field(default_factory=dict)
    model_version: str = "1.0.0"

    # Optional spatial attachments and viewpoints
    surface_normal: Optional[POICoordinates] = None
    camera_viewpoint: Optional[POICameraViewpoint] = None
    tags: List[str] = Field(default_factory=list)
    attachments: List[POIAttachment] = Field(default_factory=list)
    level_id: Optional[uuid.UUID] = None
    section_id: Optional[uuid.UUID] = None
    description: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def sync_poi_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            # 1. ID synchronization
            if "id" not in data and "poi_id" in data:
                data["id"] = data["poi_id"]
            elif "poi_id" not in data and "id" in data:
                data["poi_id"] = data["id"]
            elif "id" not in data and "poi_id" not in data:
                gen_id = uuid.uuid4()
                data["id"] = gen_id
                data["poi_id"] = gen_id

            if isinstance(data.get("id"), str):
                data["id"] = uuid.UUID(data["id"])
            if isinstance(data.get("poi_id"), str):
                data["poi_id"] = uuid.UUID(data["poi_id"])

            # 2. Name & Title synchronization
            if "name" not in data and "title" in data:
                data["name"] = data["title"]
            elif "title" not in data and "name" in data:
                data["title"] = data["name"]
            elif "name" not in data and "title" not in data:
                data["name"] = "Point of Interest"
                data["title"] = "Point of Interest"

            # 3. Coordinates synchronization
            if "coordinates" not in data and "coordinates_m" in data:
                data["coordinates"] = data["coordinates_m"]
            elif "coordinates_m" not in data and "coordinates" in data:
                data["coordinates_m"] = data["coordinates"]

            # Handle list [x, y, z] or dict input for coordinates
            for coord_key in ["coordinates", "coordinates_m"]:
                val = data.get(coord_key)
                if isinstance(val, (list, tuple)) and len(val) >= 3:
                    data[coord_key] = {"x": float(val[0]), "y": float(val[1]), "z": float(val[2])}

            # 4. Metadata synchronization
            if "metadata" not in data and "custom_metadata" in data:
                data["metadata"] = data["custom_metadata"]
            elif "custom_metadata" not in data and "metadata" in data:
                data["custom_metadata"] = {str(k): str(v) for k, v in data["metadata"].items()}

            # 5. Geometry defaulting from surface_normal if available
            if "geometry" not in data:
                data["geometry"] = {}
            if "surface_normal" in data and data["surface_normal"] and "surface_normal" not in data["geometry"]:
                data["geometry"]["surface_normal"] = data["surface_normal"]

            # 6. Tags & aliases mutual inclusion
            if "aliases" in data and "tags" not in data:
                data["tags"] = list(data["aliases"])
            elif "tags" in data and "aliases" not in data:
                data["aliases"] = list(data["tags"])

        return data
