"""
Formal Schema for Tri-Representation Space Architecture:
Explicitly links Visual Model, Structural Model, and Collision Model
under a shared canonical metric transformation and version metadata.
"""

import uuid
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field
from core.schemas.metric_transform import MetricTransformSchema

class VisualRepresentationMeta(BaseModel):
    model_format: Literal["glTF_2.0", "GLB", "3DGS_PLY", "OBJ"]
    artifact_uri: str
    lod_level: str = "LOD0"
    element_count: int = Field(ge=0, description="Vertex count for meshes, or Gaussian count for splats")
    texture_resolution: Optional[str] = "2048x2048"
    file_size_bytes: int = Field(ge=0)
    render_pipeline: str = "PBR_METALLIC_ROUGHNESS"

class StructuralRepresentationMeta(BaseModel):
    plane_graph_uri: str
    bim_export_uri: Optional[str] = None
    wall_count: int = Field(ge=0)
    floor_count: int = Field(ge=0)
    ceiling_count: int = Field(ge=0)
    opening_count: int = Field(ge=0)
    room_count: int = Field(ge=0)
    total_surface_area_m2: float = Field(ge=0.0)
    format_type: str = "ANALYTICAL_PLANE_GRAPH"

class CollisionObstacle(BaseModel):
    obstacle_id: str
    obstacle_type: str
    center: List[float] = Field(min_length=3, max_length=3)
    extent: List[float] = Field(min_length=3, max_length=3)
    is_walkable: bool = False

class CollisionRepresentationMeta(BaseModel):
    navmesh_graph_uri: str
    collision_mesh_uri: Optional[str] = None
    walkable_surface_area_m2: float = Field(ge=0.0)
    nav_nodes_count: int = Field(ge=0)
    nav_edges_count: int = Field(ge=0)
    obstacles: List[CollisionObstacle] = Field(default_factory=list)
    max_wheelchair_slope_deg: float = 4.76
    is_collision_simplified: bool = True

class TriRepresentationBundle(BaseModel):
    bundle_id: str
    model_version_id: str
    project_id: uuid.UUID
    canonical_metric_transform: MetricTransformSchema
    visual_model: VisualRepresentationMeta
    structural_model: StructuralRepresentationMeta
    collision_model: CollisionRepresentationMeta
    created_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
