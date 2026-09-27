"""API routers package."""
from app.routers.health import router as health_router
from app.routers.loans import router as loans_router
from app.routers.documents import router as documents_router
from app.routers.recompute import router as recompute_router
from app.routers.serviceability import router as serviceability_router

__all__ = [
    "health_router",
    "loans_router",
    "documents_router",
    "recompute_router",
    "serviceability_router",
]
