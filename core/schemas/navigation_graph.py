"""
Contract 10: Navigation Graph Schema
Version: 1.0.0
Producer: Stage 09 NavMesh Generator / Navigation Service
Consumer: Routing Engine (A*) & Web/AR Viewers
"""

import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class NavigationNode(BaseModel):
    id: str
    position: List[float] = Field(min_length=3, max_length=3, description="[x, y, z] metric coordinates")
    is_wheelchair_accessible: bool = True
    floor_level: int = 1
    connected_edge_ids: List[str] = Field(default_factory=list)

class NavigationEdge(BaseModel):
    id: str
    from_node: str
    to_node: str
    distance_meters: float = Field(gt=0)
    edge_type: Literal["CORRIDOR", "DOORWAY", "STAIRS", "ELEVATOR", "RAMP", "OPEN_SPACE"] = "CORRIDOR"
    is_wheelchair_accessible: bool = True
    clearance_width_meters: float = Field(default=1.20, gt=0)
    slope_degrees: float = Field(default=0.0, ge=0.0, le=45.0)

class NavigationGraph(BaseModel):
    project_id: uuid.UUID
    nodes: List[NavigationNode]
    edges: List[NavigationEdge]
