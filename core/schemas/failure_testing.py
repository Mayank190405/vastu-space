"""
Formal Schemas for Deliberate Pipeline Failure Injection & Verification
Defines the 14 required failure injection modes, error classifications,
and comprehensive 7-dimension verification reports.
"""

from enum import Enum
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import uuid
import datetime


class FailureInjectionType(str, Enum):
    NETWORK_INTERRUPTION = "NETWORK_INTERRUPTION"
    CORRUPTED_VIDEO = "CORRUPTED_VIDEO"
    MISSING_FRAMES = "MISSING_FRAMES"
    INVALID_TIMESTAMPS = "INVALID_TIMESTAMPS"
    INSUFFICIENT_OVERLAP = "INSUFFICIENT_OVERLAP"
    TRACKING_FAILURE = "TRACKING_FAILURE"
    COLMAP_FAILURE = "COLMAP_FAILURE"
    DEPTH_FAILURE = "DEPTH_FAILURE"
    CELL_RECONSTRUCTION_FAILURE = "CELL_RECONSTRUCTION_FAILURE"
    GPU_WORKER_FAILURE = "GPU_WORKER_FAILURE"
    GEOMETRY_FAILURE = "GEOMETRY_FAILURE"
    FUSION_FAILURE = "FUSION_FAILURE"
    NAVIGATION_FAILURE = "NAVIGATION_FAILURE"
    VIEWER_ASSET_FAILURE = "VIEWER_ASSET_FAILURE"


class ErrorCategory(str, Enum):
    NETWORK_ERROR = "NETWORK_ERROR"
    MEDIA_CORRUPTION = "MEDIA_CORRUPTION"
    DATA_INTEGRITY_ERROR = "DATA_INTEGRITY_ERROR"
    TIMESTAMP_INCONSISTENCY = "TIMESTAMP_INCONSISTENCY"
    COVERAGE_DEFECT = "COVERAGE_DEFECT"
    TRACKING_LOST = "TRACKING_LOST"
    SFM_CONVERGENCE_FAILURE = "SFM_CONVERGENCE_FAILURE"
    DEPTH_ESTIMATION_FAILURE = "DEPTH_ESTIMATION_FAILURE"
    SPATIAL_CELL_DEFECT = "SPATIAL_CELL_DEFECT"
    RESOURCE_EXHAUSTION = "RESOURCE_EXHAUSTION"
    GEOMETRIC_VALIDATION_FAILURE = "GEOMETRIC_VALIDATION_FAILURE"
    BOUNDARY_FUSION_FAILURE = "BOUNDARY_FUSION_FAILURE"
    NAVIGATION_GENERATION_FAILURE = "NAVIGATION_GENERATION_FAILURE"
    ASSET_DELIVERY_FAILURE = "ASSET_DELIVERY_FAILURE"


class FailureVerificationReport(BaseModel):
    """
    Comprehensive verification report evaluating a single failure injection
    across all 7 required dimensions.
    """
    test_id: str = Field(default_factory=lambda: f"fail_test_{uuid.uuid4().hex[:8]}")
    injection_type: FailureInjectionType
    pipeline_stage: str
    detected: bool
    detection_mechanism: str
    error_category: ErrorCategory
    error_code: str
    error_message: str
    recovery_behavior: str
    user_visible_state: str
    retry_behavior: str
    data_integrity_preserved: bool
    version_integrity_preserved: bool
    silent_corruption_prevented: bool
    diagnostic_evidence: Dict[str, Any] = Field(default_factory=dict)
    timestamp: str = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat())


class FailureInjectionRequest(BaseModel):
    failure_type: FailureInjectionType
    project_id: Optional[str] = None
    capture_id: Optional[str] = None
    severity: str = "CRITICAL"
    custom_params: Dict[str, Any] = Field(default_factory=dict)
