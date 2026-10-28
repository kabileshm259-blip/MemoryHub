import uuid
from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import SourceRecordCreateRequest, SourceRecordListResponse, SourceRecordResponse
from app.services.ingestion_service import IngestionService

router = APIRouter(tags=["Knowledge Sources"])


@router.post(
    "/projects/{project_id}/sources",
    response_model=SourceRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest a new document or external knowledge source",
)
def ingest_document(
    project_id: uuid.UUID,
    data: SourceRecordCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceRecordResponse:
    return IngestionService.ingest_document(db, current_user, project_id, data)


@router.get(
    "/projects/{project_id}/sources",
    response_model=SourceRecordListResponse,
    summary="List all indexed sources for a project",
)
def list_sources(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> SourceRecordListResponse:
    items = IngestionService.list_sources(db, current_user, project_id)
    return SourceRecordListResponse(items=items, total=len(items))


@router.delete(
    "/projects/{project_id}/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a knowledge source and remove all vector index chunks",
)
def delete_source(
    project_id: uuid.UUID,
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    IngestionService.delete_source(db, current_user, project_id, source_id)
