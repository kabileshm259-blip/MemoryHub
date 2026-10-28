from typing import Any, Dict
from fastapi import FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from app.chroma import check_chroma_connection
from app.database import check_postgres_connection
from app.routers import auth, handoffs, integrations, notifications, projects, rag, search, sources

app = FastAPI(
    title="MemoryHub API",
    description="Backend API for MemoryHub knowledge management platform",
    version="0.1.0",
)

# Enable CORS for local frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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
    postgres_ok = check_postgres_connection()
    chroma_ok = check_chroma_connection()

    if not postgres_ok:
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
        "chroma": "connected" if chroma_ok else "unavailable",
    }
