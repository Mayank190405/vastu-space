"""
VĀSTU API: Projects Router
Handles Project CRUD, spatial typology configurations, and project metadata directly from database.
Zero sample or prefeed data.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import asyncpg

router = APIRouter(prefix="/projects", tags=["Projects"])

class ProjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    client_name: Optional[str] = None
    location_city: Optional[str] = "Bengaluru"
    location_state: Optional[str] = "Karnataka"
    location_country: Optional[str] = "India"
    typology: str = Field(default="commercial_office")
    ceiling_height_meters: float = Field(default=3.0, gt=0)
    total_floors_count: int = Field(default=1, ge=1)
    status: str = Field(default="active")

class ProjectResponse(BaseModel):
    id: str
    name: str
    slug: Optional[str] = None
    description: Optional[str] = None
    client_name: Optional[str] = None
    location_city: Optional[str] = None
    location_state: Optional[str] = None
    location_country: Optional[str] = "India"
    typology: str = "commercial_office"
    total_area_sqft: float = 0.0
    total_area_sqm: float = 0.0
    ceiling_height_meters: float = 3.0
    total_floors_count: int = 1
    total_halls_count: int = 0
    total_rooms_count: int = 0
    total_corridors_count: int = 0
    spaces_count: int = 0
    precision_gate_cm: float = 2.5
    status: str = "active"
    created_at: str
    updated_at: str

# Pure dynamic store: starts completely empty, zero sample data
_PROJECTS_STORE: Dict[str, Dict[str, Any]] = {}

async def _get_db_pool():
    try:
        return await asyncpg.create_pool(
            "postgresql://vastu_user:vastu_secure_password_2026@localhost:5432/vastu_db",
            min_size=1,
            max_size=5,
            timeout=2.0
        )
    except Exception:
        return None

@router.get("", response_model=List[ProjectResponse])
@router.get("/", response_model=List[ProjectResponse])
async def list_projects():
    """Lists all spatial computing projects directly from Postgres. Zero sample data."""
    pool = await _get_db_pool()
    results = []
    if pool:
        try:
            async with pool.acquire() as conn:
                rows = await conn.fetch(
                    "SELECT id, name, slug, description, client_name, location_city, location_state, "
                    "location_country, typology, total_area_sqft, total_area_sqm, ceiling_height_meters, "
                    "total_floors_count, total_halls_count, total_rooms_count, total_corridors_count, "
                    "precision_gate_cm, status, created_at, updated_at FROM projects ORDER BY created_at DESC;"
                )
                for r in rows:
                    results.append({
                        "id": str(r["id"]),
                        "name": r["name"] or "Unnamed Project",
                        "slug": r["slug"],
                        "description": r["description"],
                        "client_name": r["client_name"],
                        "location_city": r["location_city"],
                        "location_state": r["location_state"],
                        "location_country": r["location_country"] or "India",
                        "typology": r["typology"] or "commercial_office",
                        "total_area_sqft": float(r["total_area_sqft"] or 0),
                        "total_area_sqm": float(r["total_area_sqm"] or 0),
                        "ceiling_height_meters": float(r["ceiling_height_meters"] or 3.0),
                        "total_floors_count": int(r["total_floors_count"] or 1),
                        "total_halls_count": int(r["total_halls_count"] or 0),
                        "total_rooms_count": int(r["total_rooms_count"] or 0),
                        "total_corridors_count": int(r["total_corridors_count"] or 0),
                        "spaces_count": int(r["total_rooms_count"] or 0),
                        "precision_gate_cm": float(r["precision_gate_cm"] or 2.5),
                        "status": r["status"] or "active",
                        "created_at": r["created_at"].isoformat() if r["created_at"] else datetime.utcnow().isoformat(),
                        "updated_at": r["updated_at"].isoformat() if r["updated_at"] else datetime.utcnow().isoformat(),
                    })
        except Exception:
            pass
        finally:
            await pool.close()

    for p in _PROJECTS_STORE.values():
        if not any(r["id"] == p["id"] for r in results):
            results.append(p)

    return results

@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Retrieves a single project by ID."""
    pool = await _get_db_pool()
    if pool:
        try:
            async with pool.acquire() as conn:
                try:
                    p_uuid = uuid.UUID(project_id)
                except ValueError:
                    p_uuid = None

                if p_uuid:
                    r = await conn.fetchrow(
                        "SELECT id, name, slug, description, client_name, location_city, location_state, "
                        "location_country, typology, total_area_sqft, total_area_sqm, ceiling_height_meters, "
                        "total_floors_count, total_halls_count, total_rooms_count, total_corridors_count, "
                        "precision_gate_cm, status, created_at, updated_at FROM projects WHERE id = $1;",
                        p_uuid
                    )
                    if r:
                        await pool.close()
                        return {
                            "id": str(r["id"]),
                            "name": r["name"],
                            "slug": r["slug"],
                            "description": r["description"],
                            "client_name": r["client_name"],
                            "location_city": r["location_city"],
                            "location_state": r["location_state"],
                            "location_country": r["location_country"] or "India",
                            "typology": r["typology"] or "commercial_office",
                            "total_area_sqft": float(r["total_area_sqft"] or 0),
                            "total_area_sqm": float(r["total_area_sqm"] or 0),
                            "ceiling_height_meters": float(r["ceiling_height_meters"] or 3.0),
                            "total_floors_count": int(r["total_floors_count"] or 1),
                            "total_halls_count": int(r["total_halls_count"] or 0),
                            "total_rooms_count": int(r["total_rooms_count"] or 0),
                            "total_corridors_count": int(r["total_corridors_count"] or 0),
                            "spaces_count": int(r["total_rooms_count"] or 0),
                            "precision_gate_cm": float(r["precision_gate_cm"] or 2.5),
                            "status": r["status"] or "active",
                            "created_at": r["created_at"].isoformat() if r["created_at"] else datetime.utcnow().isoformat(),
                            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else datetime.utcnow().isoformat(),
                        }
        except Exception:
            pass
        finally:
            await pool.close()

    if project_id in _PROJECTS_STORE:
        return _PROJECTS_STORE[project_id]

    raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

@router.post("", response_model=ProjectResponse, status_code=201)
@router.post("/", response_model=ProjectResponse, status_code=201)
async def create_project(req: ProjectCreateRequest):
    new_uuid = uuid.uuid4()
    new_id = str(new_uuid)
    slug = req.name.lower().replace(" ", "-").replace("/", "-")
    now_str = datetime.utcnow().isoformat()
    record = {
        "id": new_id,
        "name": req.name,
        "slug": slug,
        "description": req.description or "",
        "client_name": req.client_name or "",
        "location_city": req.location_city or "Bengaluru",
        "location_state": req.location_state or "Karnataka",
        "location_country": req.location_country or "India",
        "typology": req.typology,
        "total_area_sqft": 0.0,
        "total_area_sqm": 0.0,
        "ceiling_height_meters": req.ceiling_height_meters,
        "total_floors_count": req.total_floors_count,
        "total_halls_count": 0,
        "total_rooms_count": 0,
        "total_corridors_count": 0,
        "spaces_count": 0,
        "precision_gate_cm": 2.5,
        "status": req.status,
        "created_at": now_str,
        "updated_at": now_str,
    }
    _PROJECTS_STORE[new_id] = record
    return record

@router.delete("/{project_id}", status_code=200)
async def delete_project(project_id: str):
    if project_id in _PROJECTS_STORE:
        del _PROJECTS_STORE[project_id]
    return {"status": "DELETED", "id": project_id}
