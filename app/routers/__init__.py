"""API routers package."""

from app.routers.audit import router as audit_router
from app.routers.chat import router as chat_router
from app.routers.consistency import router as consistency_router
from app.routers.disputes import router as disputes_router
from app.routers.documents import router as documents_router
from app.routers.health import router as health_router
from app.routers.loans import router as loans_router
from app.routers.pipeline import router as pipeline_router
from app.routers.recompute import router as recompute_router
from app.routers.serviceability import router as serviceability_router
from app.routers.vernacular import router as vernacular_router
from app.routers.verify import router as verify_router

__all__ = [
    "audit_router",
    "chat_router",
    "consistency_router",
    "disputes_router",
    "documents_router",
    "health_router",
    "loans_router",
    "pipeline_router",
    "recompute_router",
    "serviceability_router",
    "vernacular_router",
    "verify_router",
]
