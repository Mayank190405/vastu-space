"""
Contract: Navigation Representation & Geometric Causality Schema
Producer: Stage 08 Navigation Representation Generator
Consumer: Indoor A* Router, Web Viewer, Mobile AR Pathfinder

Defines:
1. Walkable surface geometry and boundaries.
2. Identifiable geometric causality for every non-traversable / blocked region.
3. Topological NavMesh graph (Contract 10).
4. Strict guarantee: Zero derivation from Gaussian splats.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
import uuid

from core.schemas.navigation_graph import NavigationGraph


class BlockedRegionCause(str, Enum):
    """Identifiable geometric causes for blocked / non-walkable space."""
    WALL = "WALL"
    FURNITURE = "FURNITURE"
    COLUMN = "COLUMN"
    DOOR_CLOSED = "DOOR_CLOSED"
    NARROW_PASSAGE = "NARROW_PASSAGE"
    DISCONNECTED_FLOOR = "DISCONNECTED_FLOOR"
    INACCESSIBLE_ISLAND = "INACCESSIBLE_ISLAND"


class BlockedRegion(BaseModel):
    """
    Explicit representation of a non-walkable spatial zone with its identifiable geometric cause.
    Fulfills Acceptance Criterion: Every blocked region has an identifiable geometric cause.
    """
    id: str = Field(..., description="Unique blocked region identifier")
    cause: BlockedRegionCause = Field(..., description="Primary geometric root cause")
    source_entity_id: Optional[str] = Field(None, description="Identifier of the blocking structural or collision entity")
    source_entity_type: Optional[str] = Field(None, description="Type of the blocking entity (e.g. 'WALL', 'TABLE', 'COLUMN')")
    geometry_2d: List[List[float]] = Field(default_factory=list, description="2D polygon contour in metric floor space [[x1, y1], [x2, y2], ...]")
    center_3d: List[float] = Field(min_length=3, max_length=3, description="Centroid [x, y, z] in canonical metric space")
    extent_3d: Optional[List[float]] = Field(None, min_length=3, max_length=3, description="Bounding dimensions [dx, dy, dz]")
    clearance_m: Optional[float] = Field(None, description="Measured passable clearance (if narrow passage)")
    required_clearance_m: float = Field(default=0.70, description="Required clearance based on human radius (2 * r_human)")
    explanation: str = Field(..., description="Deterministic diagnostic explaining WHY this region is blocked")


class WalkablePolygon(BaseModel):
    """
    Continuous 2D/3D walkable floor surface patch.
    """
    id: str = Field(..., description="Unique polygon identifier")
    floor_level: int = Field(default=1, description="Building floor level (1, 2, ...)")
    elevation_z: float = Field(default=0.0, description="Metric elevation of the floor surface (+Z canonical)")
    boundary: List[List[float]] = Field(..., description="Outer counter-clockwise contour [[x, y], ...]")
    holes: List[List[List[float]]] = Field(default_factory=list, description="Inner voids / cutout footprints")
    surface_area_m2: float = Field(ge=0.0, description="Calculated walkable surface area in square meters")


class DoorwayChokepoint(BaseModel):
    """
    Doorway transit portal connecting rooms / zones.
    """
    id: str = Field(..., description="Chokepoint identifier")
    door_id: str = Field(..., description="Structural opening ID")
    center_3d: List[float] = Field(min_length=3, max_length=3)
    width_m: float = Field(gt=0.0)
    height_m: float = Field(default=2.10, gt=0.0)
    is_passable: bool = Field(default=True)
    connected_rooms: List[str] = Field(default_factory=list)


class NavigationRepresentation(BaseModel):
    """
    Authoritative Navigation Representation derived exclusively from Structural & Collision geometry.
    Guarantees independent visualization and verifiable geometric causality.
    """
    model_id: str = Field(..., description="Associated digital twin model ID")
    version: str = Field(default="1.0.0", description="Model version")
    human_radius_m: float = Field(default=0.35, gt=0.0, description="Body clearance radius used for inflation")
    floors_count: int = Field(default=1, ge=1)
    walkable_regions: List[WalkablePolygon] = Field(default_factory=list)
    blocked_regions: List[BlockedRegion] = Field(default_factory=list)
    navmesh_graph: NavigationGraph = Field(..., description="Contract 10 topological navigation nodes and edges")
    doorways: List[DoorwayChokepoint] = Field(default_factory=list)
    total_floor_area_m2: float = Field(ge=0.0)
    walkable_area_m2: float = Field(ge=0.0)
    blocked_area_m2: float = Field(ge=0.0)
    derived_from_gaussian_splats: bool = Field(
        default=False,
        description="Strictly False: Navigation is NEVER derived directly from Gaussian splats"
    )
    structural_source: Optional[str] = Field(None, description="Structural plane graph URI")
    collision_source: Optional[str] = Field(None, description="Collision model URI")
    metadata: Dict[str, Any] = Field(default_factory=dict)
