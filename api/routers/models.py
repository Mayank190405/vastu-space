"""
VĀSTU API: Models Router
3D spatial digital twin asset registry, LOD versions, immutable release lineage,
and 4-way differential model comparison.
"""

from fastapi import APIRouter, HTTPException, status
import uuid
from typing import List, Optional, Dict, Any

from core.schemas.model_version import ModelVersion
from core.schemas.representation_bundle import (
    TriRepresentationBundle,
    VisualRepresentationMeta,
    StructuralRepresentationMeta,
    CollisionRepresentationMeta,
)
from core.versioning.registry import ImmutableModelRegistry, ImmutableVersionError
from core.versioning.comparator import ModelComparator
from core.schemas.model_comparison import ModelComparisonResult

router = APIRouter(prefix="/models", tags=["Models"])

# Global Immutable Model Registry and Comparator instances
model_registry = ImmutableModelRegistry()
model_comparator = ModelComparator(model_registry)

# In-memory dictionary for legacy backward compatibility
_MODELS_STORE = {}
_BUNDLE_STORE = {}

@router.post("/", status_code=201)
async def register_model_version(version: ModelVersion):
    """
    Registers a new immutable model version.
    Raises 409 Conflict if this version already exists.
    """
    try:
        model_registry.register_version(version)
    except ImmutableVersionError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))

    _MODELS_STORE[version.model_version_id] = version.model_dump()
    return {"status": "REGISTERED", "model_version": version.model_version_id}

@router.get("/project/{project_id}")
async def list_models_by_project(project_id: str):
    """Lists all registered model versions for a project or space."""
    results = []
    for vid, m in _MODELS_STORE.items():
        if project_id == "all" or str(m.get("project_id")) == project_id or str(m.get("space_id")) == project_id:
            results.append(m)
    return results

@router.get("/project/{project_id}/active")
async def get_active_model_by_project(project_id: str):
    """Retrieves the active published model version for a project or space."""
    for vid, m in _MODELS_STORE.items():
        if (project_id == "all" or str(m.get("project_id")) == project_id or str(m.get("space_id")) == project_id) and m.get("status") in ["ACTIVE", "PUBLISHED"]:
            return m
    # If any model exists, return the latest
    if _MODELS_STORE:
        return list(_MODELS_STORE.values())[-1]
    raise HTTPException(status_code=404, detail="No active model found for space")

@router.get("/{version_id}")
async def get_model_version(version_id: str):
    """Retrieves an immutable model version metadata independently."""
    v = model_registry.get_version(version_id)
    if v is not None:
        return v.model_dump()
    if version_id in _MODELS_STORE:
        return _MODELS_STORE[version_id]
    raise HTTPException(status_code=404, detail="Model version not found")


@router.post("/{version_id}/bundle", status_code=201)
async def register_representation_bundle(version_id: str, bundle: TriRepresentationBundle):
    """Associates a decoupled tri-representation bundle with a model version."""
    v = model_registry.get_version(version_id)
    if v is not None and version_id not in model_registry._bundles:
        model_registry._bundles[version_id] = bundle

    _BUNDLE_STORE[version_id] = bundle.model_dump()
    return {"status": "REGISTERED", "version_id": version_id, "bundle_id": bundle.bundle_id}

@router.get("/{version_id}/bundle")
async def get_representation_bundle(version_id: str):
    """Retrieves the complete representation bundle for a specific version."""
    b = model_registry.get_bundle(version_id)
    if b is not None:
        return b.model_dump()
    if version_id in _BUNDLE_STORE:
        return _BUNDLE_STORE[version_id]
    raise HTTPException(status_code=404, detail="Representation bundle not found")

@router.get("/{version_id}/visual")
async def get_visual_representation(version_id: str):
    """Web viewer endpoint: retrieves only visual model assets (0 collision/structural overhead)."""
    b = model_registry.get_bundle(version_id)
    if b is not None:
        return b.visual_model.model_dump()
    if version_id in _BUNDLE_STORE:
        return _BUNDLE_STORE[version_id]["visual_model"]
    raise HTTPException(status_code=404, detail="Representation bundle not found")

@router.get("/{version_id}/structural")
async def get_structural_representation(version_id: str):
    """BIM/Architectural endpoint: retrieves only structural floors, walls, openings, and objects."""
    b = model_registry.get_bundle(version_id)
    if b is not None:
        return b.structural_model.model_dump()
    if version_id in _BUNDLE_STORE:
        return _BUNDLE_STORE[version_id]["structural_model"]
    raise HTTPException(status_code=404, detail="Representation bundle not found")

@router.get("/{version_id}/collision")
async def get_collision_representation(version_id: str):
    """Navigation endpoint: retrieves only simplified walkable surfaces and obstacle colliders (0 visual overhead)."""
    b = model_registry.get_bundle(version_id)
    if b is not None:
        return b.collision_model.model_dump()
    if version_id in _BUNDLE_STORE:
        return _BUNDLE_STORE[version_id]["collision_model"]
    raise HTTPException(status_code=404, detail="Representation bundle not found")

@router.get("/{version_id}/compare/{target_version_id}", response_model=ModelComparisonResult)
async def compare_model_versions(version_id: str, target_version_id: str):
    """
    Computes 4-way differential analysis between two model versions:
    - Changed Geometry
    - Changed POIs
    - Changed Navigation
    - Changed Confidence
    """
    try:
        return model_comparator.compare(version_id, target_version_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{model_id}/lineage")
async def get_model_lineage(model_id: str):
    """Returns the chronological lineage graph of versions for a model."""
    versions = model_registry.list_versions(model_id)
    return {
        "model_id": model_id,
        "version_count": len(versions),
        "versions": [v.model_dump() for v in versions]
    }


# Stage 24: High-Performance Delivery Optimization & Telemetry Endpoints
from core.schemas.delivery_optimization import DeliveryManifest, PerformanceTelemetryReport
from core.spatial.delivery_engine import SpatialDeliveryEngine

delivery_engine = SpatialDeliveryEngine()
_TELEMETRY_LOGS: List[Dict[str, Any]] = []

@router.get("/{version_id}/delivery-manifest", response_model=DeliveryManifest)
async def get_delivery_manifest(version_id: str):
    """
    Returns spatial chunks, 3-tier LOD metadata, and CDN endpoints
    for progressive, lazy-loading web viewer streaming.
    """
    manifest = delivery_engine.generate_delivery_manifest(
        model_version_id=version_id,
        bounds_min=[-10.0, 0.0, -10.0],
        bounds_max=[10.0, 3.5, 10.0],
        chunk_grid_size_meters=5.0
    )
    return manifest

@router.post("/{version_id}/telemetry")
async def ingest_performance_telemetry(version_id: str, report: PerformanceTelemetryReport):
    """
    Ingests 7-metric runtime telemetry report from web viewer client
    and verifies competition / demo performance criteria.
    """
    verdict = delivery_engine.evaluate_telemetry_verdict(report)
    _TELEMETRY_LOGS.append({
        "version_id": version_id,
        "report": report.model_dump(),
        "verdict": verdict
    })
    return {
        "status": verdict["status"],
        "overall_verdict": verdict["overall_verdict"],
        "passed_metrics": verdict["passed_metrics"],
        "total_metrics": verdict["total_metrics"],
        "verdict": verdict
    }
