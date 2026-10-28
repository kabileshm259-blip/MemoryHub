import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    GenerateHandoffRequest,
    GenerateHandoffResponse,
    HandoffCommentCreateRequest,
    HandoffCommentResponse,
    HandoffCreateRequest,
    HandoffListResponse,
    HandoffResponse,
    HandoffStatusUpdateRequest,
    HandoffUpdateRequest,
)
from app.services.handoff_service import HandoffService
from app.services.rag_service import RAGService

router = APIRouter(tags=["Handoffs"])


@router.post(
    "/projects/{project_id}/handoffs",
    response_model=HandoffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new operational handoff",
)
def create_handoff(
    project_id: uuid.UUID,
    data: HandoffCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HandoffResponse:
    return HandoffService.create_handoff(db, current_user, project_id, data)


@router.get(
    "/projects/{project_id}/handoffs",
    response_model=HandoffListResponse,
    summary="List handoffs for a project",
)
def list_handoffs(
    project_id: uuid.UUID,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HandoffListResponse:
    return HandoffService.list_handoffs(db, current_user, project_id, limit, offset)


@router.get(
    "/projects/{project_id}/handoffs/{handoff_id}",
    response_model=HandoffResponse,
    summary="Get handoff details by ID",
)
def get_handoff(
    project_id: uuid.UUID,
    handoff_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HandoffResponse:
    return HandoffService.get_handoff(db, current_user, project_id, handoff_id)


@router.patch(
    "/projects/{project_id}/handoffs/{handoff_id}",
    response_model=HandoffResponse,
    summary="Update handoff contents or structured summary",
)
def update_handoff(
    project_id: uuid.UUID,
    handoff_id: uuid.UUID,
    data: HandoffUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HandoffResponse:
    return HandoffService.update_handoff(db, current_user, project_id, handoff_id, data)


@router.post(
    "/projects/{project_id}/handoffs/{handoff_id}/status",
    response_model=HandoffResponse,
    summary="Transition handoff status with lifecycle state machine guards",
)
def transition_status(
    project_id: uuid.UUID,
    handoff_id: uuid.UUID,
    data: HandoffStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HandoffResponse:
    return HandoffService.transition_status(
        db, current_user, project_id, handoff_id, data.status, data.comment
    )


@router.post(
    "/projects/{project_id}/handoffs/{handoff_id}/acknowledge",
    response_model=HandoffResponse,
    summary="Successor acknowledges receiving operational handoff",
)
def acknowledge_handoff(
    project_id: uuid.UUID,
    handoff_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HandoffResponse:
    return HandoffService.acknowledge_handoff(db, current_user, project_id, handoff_id)


@router.post(
    "/projects/{project_id}/handoffs/{handoff_id}/comments",
    response_model=HandoffCommentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a review comment or blocker report",
)
def add_comment(
    project_id: uuid.UUID,
    handoff_id: uuid.UUID,
    data: HandoffCommentCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> HandoffCommentResponse:
    return HandoffService.add_comment(db, current_user, project_id, handoff_id, data)


@router.post(
    "/projects/{project_id}/handoffs/generate",
    response_model=GenerateHandoffResponse,
    status_code=status.HTTP_201_CREATED,
    summary="AI-assisted structured handoff generator from project sources",
)
def generate_handoff_draft(
    project_id: uuid.UUID,
    data: GenerateHandoffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GenerateHandoffResponse:
    return RAGService.generate_handoff_draft(db, current_user, project_id, data)
