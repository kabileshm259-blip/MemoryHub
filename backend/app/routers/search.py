import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import SearchResponse
from app.services.search_service import SearchService

router = APIRouter(tags=["Search"])


@router.get(
    "/search",
    response_model=SearchResponse,
    summary="Global search across accessible projects, handoffs, tasks, and sources",
)
def search_global(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    return SearchService.search(db, current_user, query=q, project_id=None, limit=limit)


@router.get(
    "/projects/{project_id}/search",
    response_model=SearchResponse,
    summary="Project-scoped search across handoffs, tasks, documents, and vector memory",
)
def search_project(
    project_id: uuid.UUID,
    q: str = Query(..., min_length=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SearchResponse:
    return SearchService.search(db, current_user, query=q, project_id=project_id, limit=limit)
