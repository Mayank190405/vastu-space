"""
Formal Schemas for Hybrid Spatial Search Subsystem:
Defines requests and enriched spatial search results containing:
- POI entity
- Confidence
- 3D Location coordinates [x, y, z]
- Room name / containment
- Preview metadata (match type, distance to anchor, explanation)
"""

import uuid
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field

from core.schemas.poi import PointOfInterest

class SpatialSearchQuery(BaseModel):
    query: str = Field(description="Search query string (e.g. 'Meeting Room 4', '3-seater sofas', 'chairs near reception')")
    model_version: Optional[str] = None
    project_id: Optional[uuid.UUID] = None
    room_filter: Optional[str] = None
    user_location: Optional[List[float]] = Field(default=None, min_length=3, max_length=3, description="Optional user [x,y,z] for relative proximity")
    max_distance_meters: float = Field(default=15.0, gt=0)
    limit: int = Field(default=20, ge=1, le=100)

class SearchPreviewMetadata(BaseModel):
    match_type: Literal["EXACT", "FUZZY", "SEMANTIC", "SPATIAL_PROXIMITY"]
    category: str
    match_explanation: str
    distance_to_anchor_m: Optional[float] = None
    anchor_name: Optional[str] = None
    lexical_score: float = Field(ge=0.0, le=1.0)
    semantic_score: float = Field(ge=0.0, le=1.0)
    spatial_score: float = Field(ge=0.0, le=1.0)
    composite_rank_score: float = Field(ge=0.0, le=1.0)

class SearchResultItem(BaseModel):
    poi: PointOfInterest
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence of the spatial match")
    location: List[float] = Field(min_length=3, max_length=3, description="Authoritative 3D metric coordinates [x, y, z]")
    room: Optional[str] = Field(default="Unassigned Room")
    preview_metadata: SearchPreviewMetadata

class SpatialSearchResponse(BaseModel):
    query: str
    parsed_target: str
    parsed_anchor: Optional[str] = None
    total_results: int
    results: List[SearchResultItem]
    model_version: Optional[str] = None
    execution_time_ms: float
