"""
VĀSTU Orchestrator Schemas
Defines formal Pydantic v2 schemas for the 22-stage end-to-end workflow,
stage progress events, and observable job lifecycle states.
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Callable
from enum import Enum
import uuid
import datetime


class WorkflowStage(str, Enum):
    MOBILE_CAPTURE = "MOBILE_CAPTURE"
    SOP = "SOP"
    TTS = "TTS"
    LOCAL_BUFFERING = "LOCAL_BUFFERING"
    RESUMABLE_UPLOAD = "RESUMABLE_UPLOAD"
    INGESTION = "INGESTION"
    PREPROCESSING = "PREPROCESSING"
    POSE = "POSE"
    DENSE_RECONSTRUCTION = "DENSE_RECONSTRUCTION"
    SPATIAL_CELLS = "SPATIAL_CELLS"
    STRUCTURAL_RECONSTRUCTION = "STRUCTURAL_RECONSTRUCTION"
    SEMANTICS = "SEMANTICS"
    SCALE = "SCALE"
    FUSION = "FUSION"
    QUALITY = "QUALITY"
    MODEL_REGISTRY = "MODEL_REGISTRY"
    VISUAL_ASSETS = "VISUAL_ASSETS"
    COLLISION_MODEL = "COLLISION_MODEL"
    NAVIGATION = "NAVIGATION"
    POIS = "POIS"
    SEARCH = "SEARCH"
    WEB_VIEWER = "WEB_VIEWER"


# Sequence ordering of all 22 required stages
WORKFLOW_STAGE_SEQUENCE: List[WorkflowStage] = [
    WorkflowStage.MOBILE_CAPTURE,
    WorkflowStage.SOP,
    WorkflowStage.TTS,
    WorkflowStage.LOCAL_BUFFERING,
    WorkflowStage.RESUMABLE_UPLOAD,
    WorkflowStage.INGESTION,
    WorkflowStage.PREPROCESSING,
    WorkflowStage.POSE,
    WorkflowStage.DENSE_RECONSTRUCTION,
    WorkflowStage.SPATIAL_CELLS,
    WorkflowStage.STRUCTURAL_RECONSTRUCTION,
    WorkflowStage.SEMANTICS,
    WorkflowStage.SCALE,
    WorkflowStage.FUSION,
    WorkflowStage.QUALITY,
    WorkflowStage.MODEL_REGISTRY,
    WorkflowStage.VISUAL_ASSETS,
    WorkflowStage.COLLISION_MODEL,
    WorkflowStage.NAVIGATION,
    WorkflowStage.POIS,
    WorkflowStage.SEARCH,
    WorkflowStage.WEB_VIEWER,
]


class StageExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class WorkflowProgressEvent(BaseModel):
    """
    Observable real-time status event emitted at every stage of the pipeline.
    """
    event_id: str = Field(default_factory=lambda: f"evt_{uuid.uuid4().hex[:8]}")
    job_id: str
    stage: WorkflowStage
    stage_index: int = Field(ge=1, le=22)
    total_stages: int = 22
    overall_progress_pct: float = Field(ge=0.0, le=100.0)
    stage_progress_pct: float = Field(ge=0.0, le=100.0)
    status: StageExecutionStatus
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)


class PublishedDigitalTwin(BaseModel):
    """
    Final output contract representing the published interactive digital twin.
    """
    model_version_id: str
    model_version: str = "1.0.0"
    project_id: str
    viewer_url: str
    delivery_manifest_url: str
    visual_chunks_count: int
    collision_obstacles_count: int
    navigation_nodes_count: int
    pois_count: int
    search_index_size: int
    quality_verdict: str = "PASS"
    compression_saved_mb: float = 11.9
    published_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class WorkflowJobStatus(BaseModel):
    """
    Full observable state of an end-to-end workflow job.
    """
    job_id: str
    project_id: str
    capture_id: str
    status: StageExecutionStatus
    current_stage: Optional[WorkflowStage] = None
    overall_progress_pct: float = 0.0
    stage_progress_pct: float = 0.0
    started_at: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())
    completed_at: Optional[str] = None
    elapsed_seconds: float = 0.0
    error_message: Optional[str] = None
    failed_stage: Optional[WorkflowStage] = None
    stage_history: List[WorkflowProgressEvent] = Field(default_factory=list)
    published_twin: Optional[PublishedDigitalTwin] = None
