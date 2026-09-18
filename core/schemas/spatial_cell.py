"""
Contract 6: Spatial Cell Schema
Version: 1.0.0
Producer: Stage 05 Point Cloud Engine & Spatial Cell System
Consumer: Incremental Update Worker, Global Fusion Engine, Rescan Manager
"""

from typing import List, Optional
import uuid
from pydantic import BaseModel, Field

class CellCoordinates(BaseModel):
    cx: int
    cy: int
    cz: int

class CellBounds(BaseModel):
    min_xyz: List[float] = Field(min_length=3, max_length=3)
    max_xyz: List[float] = Field(min_length=3, max_length=3)
    center_xyz: List[float] = Field(min_length=3, max_length=3)

class LocalCoordinateSystem(BaseModel):
    """Local coordinate system defined by cell center/origin in world space."""
    origin_world_xyz: List[float] = Field(default_factory=lambda: [0.0, 0.0, 0.0], min_length=3, max_length=3)
    rotation_matrix: List[List[float]] = Field(
        default_factory=lambda: [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
        description="3x3 rotation matrix for local cell orientation"
    )

class CellBoundaryInfo(BaseModel):
    """Boundary halo and adjacency information to preserve spatial continuity."""
    neighbor_cell_ids: List[str] = Field(default_factory=list)
    margin_m: float = Field(default=0.08, ge=0.0)
    boundary_points_count: int = Field(default=0, ge=0)
    adjacent_plane_ids: List[str] = Field(default_factory=list)

class SpatialCell(BaseModel):
    cell_id: str
    model_id: uuid.UUID
    coordinates: CellCoordinates
    cell_size_m: float = Field(default=1.0, gt=0)
    bounds: CellBounds
    local_coordinate_system: LocalCoordinateSystem = Field(default_factory=LocalCoordinateSystem)
    boundary_info: Optional[CellBoundaryInfo] = None
    quality_score: float = Field(ge=0.0, le=1.0)
    is_low_confidence: bool = False
    density_points_per_m3: int = Field(ge=0, default=0)
    point_count: int = Field(ge=0, default=0)
    mean_point_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    triangle_count: int = Field(ge=0, default=0)
    source_frames: List[int] = Field(default_factory=list)
    source_poses_count: int = Field(default=0, ge=0)
    structural_plane_ids: List[str] = Field(default_factory=list)
    semantic_object_ids: List[str] = Field(default_factory=list)
    nav_node_ids: List[str] = Field(default_factory=list)
    version: int = Field(default=1, ge=1)
    is_dirty: bool = False

