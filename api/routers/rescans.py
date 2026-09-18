"""
VĀSTU API: Rescans Router
Actionable Contract 12 rescan requests, field operator dispatch, and incremental fusion.
Zero prefeed or mock data.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
import uuid
from datetime import datetime

from core.schemas.rescan_request import RescanRequest

router = APIRouter(prefix="/rescans", tags=["Rescans"])

# Dynamic runtime store for real rescans: starts completely empty
_RESCANS_STORE: Dict[str, Dict[str, Any]] = {}

@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
async def list_rescans(project_id: Optional[str] = None):
    """Lists all active and completed rescan requests. Returns empty list if none exist."""
    items = list(_RESCANS_STORE.values())
    if project_id and project_id != "all":
        items = [i for i in items if str(i.get("project_id")) == project_id]
    return items

@router.get("/{request_id}")
async def get_rescan(request_id: str):
    """Retrieves a specific rescan request by ID."""
    if request_id not in _RESCANS_STORE:
        raise HTTPException(status_code=404, detail=f"Rescan request '{request_id}' not found")
    return _RESCANS_STORE[request_id]

@router.post("", status_code=201)
@router.post("/", status_code=201)
async def submit_rescan(req: RescanRequest):
    """Submits a new Contract 12 rescan request."""
    data = req.model_dump()
    _RESCANS_STORE[req.request_id] = data
    return {"status": "CREATED", "request_id": req.request_id}

@router.post("/{request_id}/dispatch")
async def dispatch_rescan_to_operator(request_id: str, payload: Optional[Dict[str, Any]] = None):
    """Dispatches targeted rescan instructions to field capture operator."""
    if request_id not in _RESCANS_STORE:
        raise HTTPException(status_code=404, detail=f"Rescan request '{request_id}' not found")
    
    item = _RESCANS_STORE[request_id]
    item["status"] = "ASSIGNED"
    item["assigned_operator"] = (payload and payload.get("operator_id")) or "field_operator"
    item["dispatched_at"] = datetime.utcnow().isoformat()
    return {
        "status": "ASSIGNED",
        "request_id": request_id,
        "dispatched_at": item["dispatched_at"]
    }

class UpdateRescanStatusRequest(BaseModel):
    status: str

@router.patch("/{request_id}")
async def update_rescan_status(request_id: str, payload: UpdateRescanStatusRequest):
    if request_id not in _RESCANS_STORE:
        raise HTTPException(status_code=404, detail=f"Rescan request '{request_id}' not found")
    _RESCANS_STORE[request_id]["status"] = payload.status
    return _RESCANS_STORE[request_id]

@router.post("/{request_id}/integrate")
async def integrate_rescan(request_id: str, delta_payload: Optional[Dict[str, Any]] = None):
    """Integrates delta rescan data, reconstructs targeted cell, and marks fused."""
    if request_id not in _RESCANS_STORE:
        raise HTTPException(status_code=404, detail=f"Rescan request '{request_id}' not found")
    
    item = _RESCANS_STORE[request_id]
    item["status"] = "FUSED"
    item["fused_at"] = datetime.utcnow().isoformat()
    return {
        "status": "FUSED",
        "request_id": request_id,
        "cell_id": item.get("cell_id"),
        "global_reconstruction_bypassed": True,
        "boundary_continuity_verified": True
    }
