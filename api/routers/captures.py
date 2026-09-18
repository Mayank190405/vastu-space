"""
VĀSTU API: Captures Router
Handles physical capture session registration and Contract 1 manifest ingestion.
Zero prefeed or mock data.
"""

from fastapi import APIRouter, HTTPException, Depends
import uuid
from typing import List, Dict, Any, Optional
from core.schemas.capture_manifest import CaptureManifest

router = APIRouter(prefix="/captures", tags=["Captures"])

# Runtime store for captures: starts empty, zero prefeed
_CAPTURES_STORE: Dict[str, Dict[str, Any]] = {}

@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
async def list_captures():
    """Lists all registered physical capture sessions."""
    return list(_CAPTURES_STORE.values())

@router.get("/project/{project_id}", response_model=List[Dict[str, Any]])
async def list_captures_by_project(project_id: str):
    """Lists all capture sessions associated with a project."""
    if project_id == "all":
        return list(_CAPTURES_STORE.values())
    return [c for c in _CAPTURES_STORE.values() if str(c.get("project_id")) == project_id]

@router.post("", status_code=201)
@router.post("/", status_code=201)
async def register_capture(manifest: CaptureManifest):
    """
    Ingests physical capture session metadata and validates Contract 1 constraints.
    """
    data = manifest.model_dump()
    data["id"] = str(manifest.capture_id)
    _CAPTURES_STORE[str(manifest.capture_id)] = data
    return {
        "status": "ACCEPTED",
        "message": "Capture session registered and manifest validated",
        "capture_id": str(manifest.capture_id)
    }

@router.get("/{capture_id}")
async def get_capture(capture_id: str):
    cid = str(capture_id)
    if cid not in _CAPTURES_STORE:
        raise HTTPException(status_code=404, detail="Capture session not found")
    return _CAPTURES_STORE[cid]

@router.get("/{capture_id}/artifacts")
async def get_capture_artifact_paths(capture_id: uuid.UUID, project_id: uuid.UUID):
    """
    Returns deterministic storage keys for all assets of this capture.
    """
    from storage.naming import CaptureArtifactNaming
    return {
        "manifest": CaptureArtifactNaming.get_manifest_key(project_id, capture_id),
        "video": CaptureArtifactNaming.get_video_key(project_id, capture_id),
        "imu": CaptureArtifactNaming.get_imu_key(project_id, capture_id),
        "timestamps": CaptureArtifactNaming.get_timestamps_key(project_id, capture_id),
        "depth": CaptureArtifactNaming.get_depth_key(project_id, capture_id),
        "package": CaptureArtifactNaming.get_package_archive_key(project_id, capture_id),
    }

@router.post("/{capture_id}/validate")
async def validate_capture_session(capture_id: uuid.UUID):
    """
    Triggers the validation engine against the registered capture manifest.
    """
    from core.validation.capture_validator import CaptureValidator
    cid = str(capture_id)
    if cid not in _CAPTURES_STORE:
        raise HTTPException(status_code=404, detail="Capture session not found")

    manifest = CaptureManifest.model_validate(_CAPTURES_STORE[cid])
    # Metadata-only validation for in-memory manifests without disk
    errors = []
    warnings = []
    checks_passed = []
    CaptureValidator._validate_metadata(manifest, errors, warnings, checks_passed)

    return {
        "is_valid": len(errors) == 0,
        "capture_id": cid,
        "errors": errors,
        "warnings": warnings,
        "checks_passed": checks_passed
    }
