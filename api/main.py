"""
VĀSTU Spatial Computing Platform: FastAPI Control Plane
Main Application Bootstrap & Routing
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.config import settings
from api.routers import (
    captures_router,
    jobs_router,
    models_router,
    pois_router,
    navigation_router,
    quality_router,
    uploads_router,
    search_router,
    ar_router,
    auth_router,
    projects_router,
    spaces_router,
    rescans_router,
    infrastructure_router,
    websocket_router,
)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Canonical Control Plane for VĀSTU Indoor Spatial Computing & Digital Twin Infrastructure",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Healthcheck
@app.get("/health", tags=["System"])
async def health_check():
    return {
        "status": "healthy",
        "service": "vastu-canonical-control-plane",
        "version": settings.app_version
    }

# Register API v1 Routers
api_v1_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_v1_prefix)
app.include_router(projects_router, prefix=api_v1_prefix)
app.include_router(spaces_router, prefix=api_v1_prefix)
app.include_router(captures_router, prefix=api_v1_prefix)
app.include_router(jobs_router, prefix=api_v1_prefix)
app.include_router(models_router, prefix=api_v1_prefix)
app.include_router(pois_router, prefix=api_v1_prefix)
app.include_router(navigation_router, prefix=api_v1_prefix)
app.include_router(quality_router, prefix=api_v1_prefix)
app.include_router(rescans_router, prefix=api_v1_prefix)
app.include_router(uploads_router, prefix=api_v1_prefix)
app.include_router(search_router, prefix=api_v1_prefix)
app.include_router(ar_router, prefix=api_v1_prefix)
app.include_router(infrastructure_router, prefix=api_v1_prefix)
app.include_router(websocket_router, prefix=api_v1_prefix)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="0.0.0.0", port=settings.port, reload=True)
