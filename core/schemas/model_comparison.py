"""
Contract 14 / Schema: Model Comparison & Evolution Diff
Enables structured inspection of changes between model versions:
- Changed geometry (cells, vertices, faces, volume, surface displacement)
- Changed POIs (added, removed, relocated, metadata changes)
- Changed navigation (nodes, edges, wheelchair accessibility)
- Changed confidence (quality score delta, per-cell improvements, resolved failures)
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class GeometryComparison(BaseModel):
    changed_cells: List[str] = Field(default_factory=list)
    added_cells: List[str] = Field(default_factory=list)
    removed_cells: List[str] = Field(default_factory=list)
    vertex_count_delta: int = 0
    face_count_delta: int = 0
    bounding_box_volume_delta_m3: float = 0.0
    mean_surface_displacement_m: float = 0.0
    is_geometry_altered: bool = False

class RelocatedPOI(BaseModel):
    poi_id: str
    name: str
    old_coordinates: List[float]
    new_coordinates: List[float]
    displacement_meters: float

class POIComparison(BaseModel):
    added_pois: List[Dict[str, Any]] = Field(default_factory=list)
    removed_pois: List[Dict[str, Any]] = Field(default_factory=list)
    relocated_pois: List[RelocatedPOI] = Field(default_factory=list)
    unaltered_poi_count: int = 0
    is_poi_altered: bool = False

class NavigationComparison(BaseModel):
    added_nodes: List[str] = Field(default_factory=list)
    removed_nodes: List[str] = Field(default_factory=list)
    added_edges: List[str] = Field(default_factory=list)
    removed_edges: List[str] = Field(default_factory=list)
    walkable_nodes_delta: int = 0
    accessibility_changes: List[Dict[str, Any]] = Field(default_factory=list)
    is_navigation_altered: bool = False

class ConfidenceComparison(BaseModel):
    score_before: float
    score_after: float
    global_score_delta: float
    per_cell_confidence_deltas: Dict[str, float] = Field(default_factory=dict)
    resolved_hard_failures: List[str] = Field(default_factory=list)
    new_warnings: List[str] = Field(default_factory=list)
    confidence_gain_summary: str

class ModelComparisonResult(BaseModel):
    base_version_id: str
    target_version_id: str
    model_id: str
    geometry: GeometryComparison
    pois: POIComparison
    navigation: NavigationComparison
    confidence: ConfidenceComparison
    summary: str
    compared_at: str
