"""
Formal Pydantic v2 Schemas for Central Quality Engine:
Evaluates reconstruction across 6 core subsystems:
1. CAPTURE: blur, exposure, coverage, overlap
2. POSE: reprojection error, tracking continuity, loop closure, pose confidence
3. DEPTH: depth consistency, density, holes
4. GEOMETRY: plane confidence, corner integrity, disconnected geometry, phantom geometry, structural consistency
5. SEMANTICS: object confidence, room confidence
6. NAVIGATION: floor continuity, obstacle validity, route feasibility

Enforces:
- Global and per-cell quality scores
- Spatial confidence map
- Hard failure detection (no arbitrary numerical score as sole decision)
- Detailed narrative explaining WHY a reconstruction passed or failed
"""

import uuid
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field

class CaptureQualityMetrics(BaseModel):
    blur_score: float = Field(ge=0.0, le=1.0, description="1.0 is perfectly sharp, < 0.70 has blur issues")
    exposure_score: float = Field(ge=0.0, le=1.0, description="1.0 is well balanced, < 0.70 under/over exposed")
    coverage_fraction: float = Field(ge=0.0, le=1.0, description="Observed area fraction of target volume")
    overlap_ratio: float = Field(ge=0.0, le=1.0, description="Mean consecutive keyframe overlap")
    issues: List[str] = Field(default_factory=list)

class PoseQualityMetrics(BaseModel):
    reprojection_error_px: float = Field(ge=0.0, description="Root-mean-square reprojection error in pixels")
    tracking_continuity_ratio: float = Field(ge=0.0, le=1.0, description="Fraction of trajectory without tracking loss")
    loop_closure_detected: bool = True
    loop_closure_residual_m: float = Field(ge=0.0, description="Residual position drift at loop closure point in meters")
    mean_pose_confidence: float = Field(ge=0.0, le=1.0, description="Mean pose estimator confidence")
    issues: List[str] = Field(default_factory=list)

class DepthQualityMetrics(BaseModel):
    consistency_ratio: float = Field(ge=0.0, le=1.0, description="Multi-view consistent depth pixel fraction")
    density_pts_per_m3: float = Field(ge=0.0, description="Dense point cloud volumetric density")
    hole_fraction: float = Field(ge=0.0, le=1.0, description="Fraction of target surface with missing depth evidence")
    issues: List[str] = Field(default_factory=list)

class GeometryQualityMetrics(BaseModel):
    plane_confidence: float = Field(ge=0.0, le=1.0, description="Mean inlier ratio of fitted architectural planes")
    corner_integrity_score: float = Field(ge=0.0, le=1.0, description="Sharp corner preservation score (1.0 = sharp, < 0.70 = rounded)")
    disconnected_geometry_count: int = Field(ge=0, description="Number of orphan/disconnected walls")
    phantom_geometry_count: int = Field(ge=0, description="Number of detected specular reflection phantom surfaces")
    structural_consistency_score: float = Field(ge=0.0, le=1.0, description="Planar regularity, perpendicularity and watertightness")
    issues: List[str] = Field(default_factory=list)

class SemanticsQualityMetrics(BaseModel):
    mean_object_confidence: float = Field(ge=0.0, le=1.0, description="Mean detection confidence of semantic objects")
    room_confidence: float = Field(ge=0.0, le=1.0, description="Certainty of room partition boundaries and containment")
    unclassified_ratio: float = Field(ge=0.0, le=1.0, description="Fraction of structural elements without semantic label")
    issues: List[str] = Field(default_factory=list)

class NavigationQualityMetrics(BaseModel):
    floor_continuity_ratio: float = Field(ge=0.0, le=1.0, description="Fraction of walkable floor without abrupt step dislocations")
    obstacle_validity_ratio: float = Field(ge=0.0, le=1.0, description="Valid collider boundaries not encroaching open corridors")
    route_feasibility_ratio: float = Field(ge=0.0, le=1.0, description="Fraction of POIs reachable via collision-free path")
    wheelchair_ada_compliant: bool = True
    issues: List[str] = Field(default_factory=list)

class CellQualityRecord(BaseModel):
    cell_id: str
    score: float = Field(ge=0.0, le=1.0)
    verdict: Literal["PASS", "WARNING", "FAIL"]
    dominant_issue: Optional[str] = None
    rescan_required: bool = False
    metrics: Dict[str, float] = Field(default_factory=dict)

class SpatialConfidenceVoxel(BaseModel):
    center_xyz: List[float] = Field(min_length=3, max_length=3)
    confidence: float = Field(ge=0.0, le=1.0)
    primary_modality: str = "MULTI_VIEW_DEPTH"

class CentralQualityEvaluation(BaseModel):
    evaluation_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    project_id: uuid.UUID
    model_version_id: str
    verdict: Literal["PASS", "WARNING", "FAIL"]
    global_score: float = Field(ge=0.0, le=1.0)
    subsystem_scores: Dict[str, float]
    
    capture: CaptureQualityMetrics
    pose: PoseQualityMetrics
    depth: DepthQualityMetrics
    geometry: GeometryQualityMetrics
    semantics: SemanticsQualityMetrics
    navigation: NavigationQualityMetrics
    
    per_cell_scores: Dict[str, CellQualityRecord] = Field(default_factory=dict)
    spatial_confidence_map: List[SpatialConfidenceVoxel] = Field(default_factory=list)
    
    hard_failures: List[str] = Field(default_factory=list, description="Critical blocking failures preventing publication")
    warnings: List[str] = Field(default_factory=list, description="Non-blocking advisories")
    recommended_actions: List[str] = Field(default_factory=list, description="Targeted remediation steps")
    
    explanation: str = Field(description="Explanatory narrative detailing WHY the model passed, warned, or failed")
    created_at: str
