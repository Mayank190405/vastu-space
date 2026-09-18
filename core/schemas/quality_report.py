"""
Contract 11: Quality Report Schema
Version: 1.0.0
Producer: Stage 10 Quality Engine
Consumer: Orchestrator Service, Rescan Manager, Project Dashboard
"""

import uuid
from typing import List, Literal, Optional
from pydantic import BaseModel, Field

class QualityScores(BaseModel):
    overall: float = Field(ge=0.0, le=1.0)
    geometry_watertightness: float = Field(ge=0.0, le=1.0)
    tracking_vio_drift: float = Field(ge=0.0, le=1.0)
    spatial_coverage: float = Field(ge=0.0, le=1.0)
    texture_sharpness: float = Field(ge=0.0, le=1.0)
    semantic_consistency: float = Field(ge=0.0, le=1.0)
    cell_continuity: float = Field(ge=0.0, le=1.0)
    navigation_connectivity: float = Field(ge=0.0, le=1.0)

class QualityReport(BaseModel):
    report_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    job_id: uuid.UUID
    project_id: uuid.UUID
    verdict: Literal["PASS", "WARNING", "FAIL"]
    scores: QualityScores
    low_confidence_cells: List[str] = Field(default_factory=list)
    failure_reasons: List[str] = Field(default_factory=list)
    recommended_actions: List[str] = Field(default_factory=list)
