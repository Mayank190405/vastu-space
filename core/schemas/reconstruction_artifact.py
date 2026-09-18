"""
Contract 5: Reconstruction Artifact Schema
Version: 1.1.0
Producer: Processing Worker Pipeline
Consumer: Backend API (ModelService) & Storage Manager
"""

import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from core.schemas.metric_transform import MetricTransformSchema

class ArtifactStats(BaseModel):
    vertex_count: int = Field(ge=0)
    triangle_count: int = Field(ge=0)
    texture_width: Optional[int] = None
    texture_height: Optional[int] = None
    bounding_box_min: List[float] = Field(min_length=3, max_length=3)
    bounding_box_max: List[float] = Field(min_length=3, max_length=3)

class ReconstructionArtifact(BaseModel):
    artifact_id: uuid.UUID
    job_id: uuid.UUID
    project_id: uuid.UUID
    model_format: Literal["glTF_2.0", "GLB", "OBJ", "PLY", "3DGS_PLY"]
    lod_level: Literal["LOD0", "LOD1", "LOD2", "RAW"] = "LOD0"
    s3_bucket: str
    s3_key: str
    file_size_bytes: int = Field(gt=0)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    stats: ArtifactStats
    metric_transform: Optional[MetricTransformSchema] = None
    created_at: str
