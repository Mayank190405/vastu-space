"""
VĀSTU API: Spaces Router
Handles indoor spaces, sections, rooms, and halls within a project.
Zero prefeed or mock data.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Dict, Any
import uuid
from datetime import datetime

router = APIRouter(prefix="/spaces", tags=["Spaces"])

class SpaceCreateRequest(BaseModel):
    project_id: str
    name: str
    space_type: str = "Living room"
    area_m2: float = Field(default=30.0, gt=0)
    ceiling_height_meters: float = Field(default=3.0, gt=0)
    status: Literal["PUBLISHED", "PROCESSING", "RESCAN_REQUIRED", "DRAFT"] = "PROCESSING"

class SpaceResponse(BaseModel):
    id: str
    project_id: str
    name: str
    space_type: str
    status: Literal["PUBLISHED", "PROCESSING", "RESCAN_REQUIRED", "DRAFT"]
    active_version: str = "1.0.0"
    quality_score: float = 0.0
    objects_count: int = 0
    pois_count: int = 0
    area_m2: float = 30.0
    created_at: str
    updated_at: str

# Pure dynamic store: starts completely empty without any prefeed
_SPACES_STORE: Dict[str, Dict[str, Any]] = {}

@router.get("", response_model=List[SpaceResponse])
@router.get("/", response_model=List[SpaceResponse])
async def list_spaces():
    """Lists all registered spatial sections. Returns empty list if none exist."""
    return list(_SPACES_STORE.values())

@router.get("/project/{project_id}", response_model=List[SpaceResponse])
async def list_spaces_by_project(project_id: str):
    """Lists all spaces associated with a specific project."""
    if project_id == "all":
        return list(_SPACES_STORE.values())
    matches = [s for s in _SPACES_STORE.values() if s["project_id"] == project_id]
    return matches

@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(space_id: str):
    """Retrieves a single space by its identifier. Returns 404 if not found."""
    if space_id in _SPACES_STORE:
        return _SPACES_STORE[space_id]
    raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")

@router.post("", response_model=SpaceResponse, status_code=201)
@router.post("/", response_model=SpaceResponse, status_code=201)
async def create_space(req: SpaceCreateRequest):
    """Registers a new space section in a project."""
    new_id = f"sp_{uuid.uuid4().hex[:8]}"
    now_str = datetime.utcnow().isoformat()
    record = {
        "id": new_id,
        "project_id": req.project_id,
        "name": req.name,
        "space_type": req.space_type,
        "status": req.status,
        "active_version": "1.0.0",
        "quality_score": 0.0,
        "objects_count": 0,
        "pois_count": 0,
        "area_m2": req.area_m2,
        "created_at": now_str,
        "updated_at": now_str,
    }
    _SPACES_STORE[new_id] = record
    return record

@router.delete("/{space_id}", status_code=200)
async def delete_space(space_id: str):
    """Deletes a space."""
    if space_id in _SPACES_STORE:
        del _SPACES_STORE[space_id]
        return {"status": "DELETED", "id": space_id}
    raise HTTPException(status_code=404, detail=f"Space '{space_id}' not found")
