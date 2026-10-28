import uuid
from typing import Any, Dict, List
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    IntegrationConnectionCreateRequest,
    IntegrationConnectionResponse,
    IntegrationSyncResponse,
)
from app.services.integration_service import IntegrationService

router = APIRouter(tags=["Integrations"])


@router.post(
    "/projects/{project_id}/integrations",
    response_model=IntegrationConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an integration connection (Jira, Slack, Confluence)",
)
def create_integration(
    project_id: uuid.UUID,
    data: IntegrationConnectionCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationConnectionResponse:
    return IntegrationService.create_connection(db, current_user, project_id, data)


@router.get(
    "/projects/{project_id}/integrations",
    response_model=List[IntegrationConnectionResponse],
    summary="List integrations for a project",
)
def list_integrations(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[IntegrationConnectionResponse]:
    return IntegrationService.list_connections(db, current_user, project_id)


@router.post(
    "/projects/{project_id}/integrations/{integration_id}/sync",
    response_model=IntegrationSyncResponse,
    summary="Trigger synchronization for an integration",
)
def sync_integration(
    project_id: uuid.UUID,
    integration_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> IntegrationSyncResponse:
    return IntegrationService.sync_integration(db, current_user, project_id, integration_id)


@router.post(
    "/projects/{project_id}/integrations/seed-demo",
    summary="Seed complete MemoryHub E-Commerce demonstration scenario",
)
def seed_demo_scenario(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    return IntegrationService.seed_ecommerce_demo_scenario(db, current_user, project_id)
