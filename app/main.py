import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from fastapi import FastAPI, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.logging import logger, request_id_ctx
from app.routers.health import router as health_router
from app.routers.loans import router as loans_router
from app.routers.documents import router as documents_router
from app.routers.recompute import router as recompute_router
from app.routers.serviceability import router as serviceability_router
from app.routers.consistency import router as consistency_router
from rag.chroma_client import get_or_create_collections

# Rate Limiter setup (RULES.md §3 S-10, S-11)
limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE_ANON}/minute"])


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for startup and shutdown routines."""
    logger.info("Initializing GUARDIAN application services...")
    try:
        # Initialize collections in ChromaDB container
        get_or_create_collections()
        logger.info("ChromaDB collections verified and ready.")
    except Exception as e:
        logger.warning(f"Could not connect to ChromaDB during startup: {e}")
    yield
    logger.info("Shutting down GUARDIAN application services...")


app = FastAPI(
    title="GUARDIAN API",
    description="Groundedness-Verified Agentic Financial Advocate for Loans",
    version="1.0.0",
    docs_url="/docs" if settings.ENVIRONMENT != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENVIRONMENT == "development" else [settings.SUPABASE_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next) -> Response:
    """
    Assigns a unique request_id to each incoming request (S-14).
    Injects request_id into contextvars for sanitized logging.
    """
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(req_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = req_id
        return response
    finally:
        request_id_ctx.reset(token)


# Standard Error Response Format: {error_code, message, request_id} (IMPLEMENTATION_PLAN.md line 110)
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    req_id = request_id_ctx.get()
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "message": exc.detail,
            "request_id": req_id,
        },
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    req_id = request_id_ctx.get()
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request payload failed strict Pydantic validation",
            "details": exc.errors(),
            "request_id": req_id,
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    req_id = request_id_ctx.get()
    logger.error(f"Unhandled exception in request: {type(exc).__name__}: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error_code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred while processing the request"
            if settings.ENVIRONMENT == "production"
            else str(exc),
            "request_id": req_id,
        },
    )


# Single gateway mounted at /api/v1
app.include_router(health_router, prefix="/api/v1")
app.include_router(loans_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(recompute_router, prefix="/api/v1")
app.include_router(serviceability_router, prefix="/api/v1")
app.include_router(consistency_router, prefix="/api/v1")
