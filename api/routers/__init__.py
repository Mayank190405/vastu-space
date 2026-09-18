"""
VĀSTU API Routers Package
"""

from api.routers.captures import router as captures_router
from api.routers.jobs import router as jobs_router
from api.routers.models import router as models_router
from api.routers.pois import router as pois_router
from api.routers.navigation import router as navigation_router
from api.routers.quality import router as quality_router
from api.routers.uploads import router as uploads_router
from api.routers.search import router as search_router
from api.routers.ar import router as ar_router
from api.routers.auth import router as auth_router
from api.routers.projects import router as projects_router
from api.routers.spaces import router as spaces_router
from api.routers.rescans import router as rescans_router
from api.routers.infrastructure import router as infrastructure_router
from api.routers.websocket import router as websocket_router

__all__ = [
    "captures_router",
    "jobs_router",
    "models_router",
    "pois_router",
    "navigation_router",
    "quality_router",
    "uploads_router",
    "search_router",
    "ar_router",
    "auth_router",
    "projects_router",
    "spaces_router",
    "rescans_router",
    "infrastructure_router",
    "websocket_router",
]
