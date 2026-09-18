"""
VĀSTU API: AR Localization Router (Stage 29)
Provides HTTP endpoints for spatial marker registration, real-time AR camera relocalization,
perspective route projection, and quantitative alignment benchmarking.
"""

from fastapi import APIRouter, HTTPException
from typing import List, Optional

from core.schemas.ar_localization import (
    SpatialMarkerAnchor,
    ARLocalizationRequest,
    ARLocalizationResult,
    ARRouteProjectionRequest,
    ARRouteProjectionResult,
    ARValidationReport,
)
from core.ar.localization_engine import ARLocalizationEngine
from core.ar.validator import ARLocalizationValidator

router = APIRouter(prefix="/ar", tags=["Augmented Reality"])

ar_engine = ARLocalizationEngine(filter_alpha=0.35)
ar_validator = ARLocalizationValidator()


@router.post("/markers", response_model=SpatialMarkerAnchor, status_code=201)
async def register_spatial_marker(anchor: SpatialMarkerAnchor):
    """Registers a physical spatial marker anchor into a digital twin model coordinate frame."""
    ar_engine.register_marker_anchor(anchor)
    return anchor


@router.get("/markers/{model_id}", response_model=List[SpatialMarkerAnchor])
async def get_model_spatial_markers(model_id: str):
    """Retrieves all registered spatial marker anchors for a digital twin model."""
    return ar_engine.get_marker_anchors(model_id)


@router.post("/localize", response_model=ARLocalizationResult)
async def localize_ar_device(req: ARLocalizationRequest):
    """
    Localizes an AR device frame against registered spatial anchors in the digital twin.
    Calculates T_model_AR rigid transform and T_model_device device pose.
    Falls back to VIO dead-reckoning continuation when markers are outside FOV.
    """
    result = ar_engine.localize(req)
    if not result.success:
        raise HTTPException(status_code=422, detail=result.rejection_reason)
    return result


@router.post("/project-route", response_model=ARRouteProjectionResult)
async def project_route_endpoint(req: ARRouteProjectionRequest):
    """
    Projects 3D digital twin route waypoints into AR camera coordinates and 2D pixel coordinates.
    """
    return ar_engine.project_route(req)


@router.post("/benchmark/run", response_model=ARValidationReport)
async def run_ar_benchmark(model_id: str = "benchmark_room_alpha"):
    """
    Executes quantitative AR localization benchmark across 5 dimensions:
    translation error (<= 5.0cm), rotation error (<= 2.0 deg), relocalization time (<= 15.0ms),
    walking stability jitter (<= 1.0cm), and route alignment (<= 2.5px).
    """
    return ar_validator.run_benchmark(model_id=model_id)
