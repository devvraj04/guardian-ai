import httpx
from fastapi import APIRouter, status
from pydantic import BaseModel
from supabase import create_client, Client
from app.core.config import settings
from app.core.logging import logger
from rag.chroma_client import get_chroma_client

router = APIRouter(prefix="/health", tags=["Health"])


class HealthStatus(BaseModel):
    status: str
    supabase: str
    chromadb: str
    environment: str


@router.get("", response_model=HealthStatus, status_code=status.HTTP_200_OK)
async def check_health() -> HealthStatus:
    """
    Verifies that the API service, hosted Supabase, and ChromaDB are all operational.
    """
    supabase_status = "unknown"
    chroma_status = "unknown"

    # Check Supabase connectivity
    try:
        supabase: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        # Verify connectivity by performing a lightweight query
        res = supabase.table("loans").select("id").limit(1).execute()
        if res is not None:
            supabase_status = "connected"
    except Exception as e:
        logger.warning(f"Supabase health check connection error: {type(e).__name__}")
        supabase_status = f"unreachable: {str(e)}"

    # Check ChromaDB connectivity
    try:
        client = get_chroma_client()
        heartbeat = client.heartbeat()
        if heartbeat > 0:
            chroma_status = "connected"
        else:
            chroma_status = "degraded"
    except Exception as e:
        logger.warning(f"ChromaDB health check connection error: {type(e).__name__}")
        chroma_status = f"unreachable: {str(e)}"

    overall_healthy = (supabase_status == "connected") and (chroma_status == "connected")

    return HealthStatus(
        status="healthy" if overall_healthy else "degraded",
        supabase=supabase_status,
        chromadb=chroma_status,
        environment=settings.ENVIRONMENT,
    )
