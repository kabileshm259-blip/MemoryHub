from contextlib import asynccontextmanager
import logging
import os
from typing import Any, Dict
from fastapi import FastAPI, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from app.chroma import check_chroma_connection
from app.database import IS_SQLITE_FALLBACK, check_postgres_connection, init_db
from app.routers import auth, handoffs, integrations, notifications, projects, rag, search, sources

logger = logging.getLogger("memoryhub.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager ensuring schema tables are created upon startup."""
    init_db()
    yield


app = FastAPI(
    title="MemoryHub API",
    description="Backend API for MemoryHub knowledge management platform",
    version="0.1.0",
    lifespan=lifespan,
)

# Allowed origins for CORS (default local dev + configured production origins)
_DEFAULT_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:3001",
    "http://127.0.0.1:3001",
]
_cors_env = os.getenv("CORS_ORIGINS", "").strip()
_allowed_origins = list(_DEFAULT_ORIGINS)
if _cors_env:
    for origin in _cors_env.split(","):
        cleaned = origin.strip().rstrip("/")
        if cleaned and cleaned not in _allowed_origins:
            _allowed_origins.append(cleaned)

# Optional regex for Vercel preview deployments (e.g. https://memoryhub-*.vercel.app)
_allow_origin_regex = None
if os.getenv("ALLOW_VERCEL_PREVIEWS", "").strip().lower() in ("true", "1", "yes"):
    _allow_origin_regex = r"^https:\/\/[a-zA-Z0-9_-]+\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Handle database exceptions gracefully with appropriate CORS-enabled status."""
    logger.error("Database operational error: %s", exc)
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Database service is temporarily unavailable. Please try again shortly."},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected server exceptions gracefully without leaking sensitive traces."""
    logger.error("Unhandled server exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected server error occurred. Please try again later."},
    )


# Register API routers under /api prefix
app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(handoffs.router, prefix="/api")
app.include_router(sources.router, prefix="/api")
app.include_router(integrations.router, prefix="/api")
app.include_router(rag.router, prefix="/api")
app.include_router(notifications.router, prefix="/api")
app.include_router(search.router, prefix="/api")


@app.get("/", summary="Root endpoint")
def read_root() -> Dict[str, str]:
    return {
        "message": "Welcome to MemoryHub API",
        "service": "memoryhub-api",
        "version": "0.1.0",
    }


@app.get("/health", summary="Liveness check endpoint")
@app.get("/health/liveness", summary="Process liveness check endpoint")
def health_liveness() -> Dict[str, str]:
    return {
        "status": "ok",
        "service": "memoryhub-api",
    }


@app.get(
    "/health/readiness",
    summary="Readiness check endpoint (PostgreSQL & ChromaDB)",
)
@app.get("/ready", summary="Readiness check alias")
def health_readiness(response: Response) -> Dict[str, Any]:
    db_ok = check_postgres_connection()
    chroma_ok = check_chroma_connection()

    if not db_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "service": "memoryhub-api",
            "postgres": "unavailable",
            "chroma": "connected" if chroma_ok else "unavailable",
        }

    return {
        "status": "ready",
        "service": "memoryhub-api",
        "postgres": "connected",
        "database_mode": "postgresql" if not IS_SQLITE_FALLBACK else "local_sqlite_fallback",
        "chroma": "connected" if chroma_ok else "unavailable",
    }
