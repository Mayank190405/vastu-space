"""
Formal Schema for Geometry Correction & Architectural QA Audits
Producer: Stage 12 Geometry Correction Engine
Consumer: Quality Engine, CAD/BIM Exporter, NavMesh Generator
"""

import uuid
from typing import List, Dict, Any, Literal, Optional
from pydantic import BaseModel, Field

class CorrectionRecord(BaseModel):
    correction_id: str
    correction_type: Literal[
        "SNAP_ORTHOGONAL_ANGLE",
        "SNAP_FLOOR_INTERSECTION",
        "SNAP_CEILING_INTERSECTION",
        "ESTIMATE_WALL_THICKNESS",
        "CLIP_EXTENTS",
        "REGULARIZE_OPENING",
        "REMOVE_PHANTOM_GEOMETRY",
        "REMOVE_FLOATING_SURFACE",
        "REMOVE_FLOATING_VERTICES",
        "SKIPPED_LOW_CONFIDENCE"
    ]
    target_id: str
    delta_metric_value: float = Field(description="Measurable improvement metric (e.g. mm moved, points pruned, volume clipped)")
    delta_metric_unit: str = Field(description="Unit of measurement: mm, deg, points, m2, m3")
    confidence: float = Field(ge=0.0, le=1.0)
    description: str

class ValidationAuditResult(BaseModel):
    watertightness_status: Literal["PASS", "WARNING", "FAIL", "NOT_REQUIRED"]
    boundary_edges_count: int = Field(ge=0)
    non_manifold_edges_count: int = Field(ge=0)

    self_intersections_count: int = Field(ge=0)
    self_intersecting_pairs: List[str] = Field(default_factory=list)

    disconnected_walls_count: int = Field(ge=0)
    disconnected_wall_ids: List[str] = Field(default_factory=list)

    floating_vertices_count: int = Field(ge=0)

    rounded_architectural_corners_count: int = Field(ge=0)
    rounded_corner_details: List[str] = Field(default_factory=list)

    excessive_smoothing_detected: bool
    max_smoothing_displacement_mm: float = Field(ge=0.0)

    incorrect_wall_extents_count: int = Field(ge=0)
    incorrect_extent_wall_ids: List[str] = Field(default_factory=list)

class GeometryQAReport(BaseModel):
    report_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    project_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    verdict: Literal["PASS", "WARNING", "FAIL"]

    cleanliness_score_before: float = Field(ge=0.0, le=1.0)
    cleanliness_score_after: float = Field(ge=0.0, le=1.0)
    measurable_improvement_percent: float = Field(ge=0.0)

    corrections_count: int = Field(ge=0)
    corrections_by_type: Dict[str, int] = Field(default_factory=dict)
    corrections: List[CorrectionRecord] = Field(default_factory=list)

    audits: ValidationAuditResult
    metadata: Dict[str, Any] = Field(default_factory=dict)
