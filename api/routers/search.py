"""
VĀSTU API: Hybrid Spatial Search Router
Multi-stage search: exact, fuzzy, semantic, and spatial relational queries.
"""

from fastapi import APIRouter, Query
from typing import Optional, List
import uuid

from core.schemas.search import SpatialSearchQuery, SpatialSearchResponse
from core.search.hybrid import HybridSpatialSearchEngine
from api.routers.pois import poi_service

router = APIRouter(prefix="/search", tags=["Search"])

# Initialize hybrid search engine using shared POI service instance
search_engine = HybridSpatialSearchEngine(poi_service=poi_service)

@router.post("/spatial", response_model=SpatialSearchResponse)
async def hybrid_spatial_search(search_req: SpatialSearchQuery):
    """
    Executes 5-stage hybrid spatial search pipeline:
    query -> lexical matching -> semantic matching -> spatial filtering -> ranking -> result coordinates
    """
    return search_engine.search(search_req)

@router.get("/spatial", response_model=SpatialSearchResponse)
async def hybrid_spatial_search_get(
    q: str = Query(..., description="Natural language search query, e.g. 'chairs near reception'"),
    model_version: Optional[str] = None,
    room_filter: Optional[str] = None,
    max_distance_meters: float = 15.0,
    limit: int = 20
):
    """GET convenience endpoint for hybrid spatial search."""
    req = SpatialSearchQuery(
        query=q,
        model_version=model_version,
        room_filter=room_filter,
        max_distance_meters=max_distance_meters,
        limit=limit
    )
    return search_engine.search(req)
