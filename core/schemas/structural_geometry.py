"""
Contract 7: Structural Geometry Schema
Version: 1.1.0
Producer: Architectural Structure Extraction Engine
Consumer: NavMesh Generator, Web Viewer, CAD / BIM Export, Spatial Graph
"""

from typing import List, Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

class PlaneEquation(BaseModel):
    a: float
    b: float
    c: float
    d: float

class StructuralOpening(BaseModel):
    opening_type: Literal["DOOR", "WINDOW", "PASSAGE", "RECESS"]
    width_m: float = Field(gt=0)
    height_m: float = Field(gt=0)
    center_3d: List[float] = Field(min_length=3, max_length=3)

class StructuralPlane(BaseModel):
    structure_id: str
    plane_type: Literal["WALL", "FLOOR", "CEILING", "OPENING", "FEATURE", "OTHER"]
    plane_equation: PlaneEquation
    normal_vector: List[float] = Field(min_length=3, max_length=3)
    inlier_points_count: int = Field(ge=0)
    surface_area_m2: float = Field(ge=0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    rmse_m: float = Field(default=0.0, ge=0.0)
    corners_3d: List[List[float]] = Field(default_factory=list)
    boundary_polygon_3d: List[List[float]] = Field(default_factory=list)
    openings: List[StructuralOpening] = Field(default_factory=list)

class PlaneIntersectionEdge(BaseModel):
    edge_id: str
    source_plane_id: str
    target_plane_id: str
    raw_angle_deg: float = Field(ge=0.0, le=180.0)
    adjusted_angle_deg: float = Field(ge=0.0, le=180.0)
    angle_confidence: float = Field(ge=0.0, le=1.0)
    is_orthogonal_prior_applied: bool
    intersection_line_start: List[float] = Field(min_length=3, max_length=3)
    intersection_line_end: List[float] = Field(min_length=3, max_length=3)
    junction_type: Literal["WALL_WALL", "WALL_FLOOR", "WALL_CEILING", "WALL_OTHER", "OTHER"]

class ArchitecturalPlaneGraphSchema(BaseModel):
    planes: List[StructuralPlane] = Field(default_factory=list)
    intersections: List[PlaneIntersectionEdge] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
