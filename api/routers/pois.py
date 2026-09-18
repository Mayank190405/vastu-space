"""
VĀSTU API: Points of Interest (POI) Router
Interactive 3D POI pin CRUD, search, 3D spatial query, raycast placement,
and version-aware spatial validity migration.
"""

import uuid
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
import numpy as np

from core.schemas.poi import PointOfInterest
from core.poi.service import POIService

router = APIRouter(prefix="/pois", tags=["POIs"])

# Global POI service singleton for the control plane
poi_service = POIService()

class SpatialQueryRequest(BaseModel):
    center_xyz: List[float] = Field(min_length=3, max_length=3)
    radius_meters: float = Field(gt=0, default=5.0)
    model_version: Optional[str] = None
    k_nearest: Optional[int] = None

class RaycastPlacementRequest(BaseModel):
    ray_origin: List[float] = Field(min_length=3, max_length=3)
    ray_direction: List[float] = Field(min_length=3, max_length=3)
    name: str = "Placed POI"
    category: str = "GENERAL"
    room: Optional[str] = None
    model_version: str = "1.0.0"
    mesh_vertices: Optional[List[List[float]]] = None
    mesh_faces: Optional[List[List[int]]] = None
    metadata: Optional[Dict[str, Any]] = None

class MigratePOIsRequest(BaseModel):
    source_version: str
    target_version: str
    transformation_matrix: Optional[List[List[float]]] = None
    max_drift_threshold_m: float = 0.50

@router.post("/", status_code=201)
async def create_poi(poi: PointOfInterest):
    """Creates and persists a version-aware 3D POI."""
    created = poi_service.create_poi(poi)
    return {"status": "CREATED", "poi_id": str(created.id), "model_version": created.model_version}

@router.get("/{poi_id}")
async def get_poi(poi_id: uuid.UUID):
    """Retrieves a single POI by ID."""
    poi = poi_service.get_poi(poi_id)
    if not poi:
        raise HTTPException(status_code=404, detail="POI not found")
    return poi

@router.put("/{poi_id}")
async def edit_poi(poi_id: uuid.UUID, updates: Dict[str, Any]):
    """Edits metadata, name, category, room, or coordinates of an existing POI."""
    try:
        updated = poi_service.edit_poi(poi_id, updates)
        return {"status": "UPDATED", "poi": updated}
    except KeyError:
        raise HTTPException(status_code=404, detail="POI not found")

@router.delete("/{poi_id}")
async def delete_poi(poi_id: uuid.UUID):
    """Deletes a POI by ID."""
    deleted = poi_service.delete_poi(poi_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="POI not found")
    return {"status": "DELETED", "poi_id": str(poi_id)}

@router.get("/")
async def search_pois(
    query: str = Query("", description="Search term for name, alias, tags, or description"),
    category: Optional[str] = None,
    room: Optional[str] = None,
    model_version: Optional[str] = None
):
    """Searches POIs by keyword, category, room, and model version."""
    return poi_service.search_pois(query=query, category=category, room=room, model_version=model_version)

@router.get("/project/{project_id}")
async def list_pois_by_project(project_id: uuid.UUID):
    """Lists all POIs associated with a project ID."""
    pid = project_id
    all_pois = poi_service.list_pois()
    return [p for p in all_pois if p.project_id == pid]

@router.post("/spatial-query")
async def spatial_query(req: SpatialQueryRequest):
    """Queries POIs in 3D metric space within a spherical radius or k-nearest."""
    results = poi_service.spatial_query(
        center_xyz=req.center_xyz,
        radius_m=req.radius_meters,
        model_version=req.model_version,
        k_nearest=req.k_nearest
    )
    return [
        {"poi": p.model_dump(), "distance_meters": round(d, 3)}
        for p, d in results
    ]

@router.post("/raycast-placement", status_code=201)
async def raycast_placement(req: RaycastPlacementRequest):
    """
    Creates a POI visually via 3D raycast hit against surface mesh.
    Computes exact surface intersection point, normal vector, and attaches POI.
    """
    verts = np.array(req.mesh_vertices, dtype=np.float64) if req.mesh_vertices else np.empty((0, 3))
    faces = np.array(req.mesh_faces, dtype=np.int32) if req.mesh_faces else np.empty((0, 3))

    placed_poi = poi_service.raycast_placement(
        ray_origin=req.ray_origin,
        ray_direction=req.ray_direction,
        mesh_vertices=verts,
        mesh_faces=faces,
        name=req.name,
        category=req.category,
        room=req.room,
        model_version=req.model_version,
        metadata=req.metadata
    )
    return {"status": "PLACED", "poi": placed_poi}

@router.post("/migrate")
async def migrate_pois_across_versions(req: MigratePOIsRequest):
    """
    Migrates and preserves POI spatial validity when model versions change (e.g. V1 -> V2).
    """
    transform = np.array(req.transformation_matrix, dtype=np.float64) if req.transformation_matrix else None
    migrated = poi_service.migrate_pois_across_versions(
        source_version=req.source_version,
        target_version=req.target_version,
        transformation_matrix=transform,
        max_drift_threshold_m=req.max_drift_threshold_m
    )
    return {
        "status": "MIGRATED",
        "migrated_count": len(migrated),
        "source_version": req.source_version,
        "target_version": req.target_version
    }
