import uuid
from typing import List
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import (
    MemberAddRequest,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)
from app.services.project_service import (
    add_project_member,
    create_project,
    get_project_for_user,
    list_project_members,
    list_user_projects,
    update_project_settings,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new project",
)
def create_new_project(
    data: ProjectCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Create a project and automatically assign the creator the owner role."""
    return create_project(db, current_user, data)


@router.get(
    "",
    response_model=ProjectListResponse,
    status_code=status.HTTP_200_OK,
    summary="List projects the authenticated user belongs to",
)
def list_projects(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectListResponse:
    """List projects accessible to the caller with pagination."""
    return list_user_projects(db, current_user, limit=limit, offset=offset)


@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Get project details by ID",
)
def get_project(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Retrieve project details only if caller is an authorized member."""
    return get_project_for_user(db, current_user, project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectResponse,
    status_code=status.HTTP_200_OK,
    summary="Update project name, description, or status",
)
def update_project(
    project_id: uuid.UUID,
    data: ProjectUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectResponse:
    """Update project settings. Restricted strictly to project owners."""
    return update_project_settings(db, current_user, project_id, data)


@router.get(
    "/{project_id}/members",
    response_model=List[ProjectMemberResponse],
    status_code=status.HTTP_200_OK,
    summary="List project members",
)
def get_members(
    project_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[ProjectMemberResponse]:
    """List members of a project. Accessible to all confirmed members."""
    return list_project_members(db, current_user, project_id)


@router.post(
    "/{project_id}/members",
    response_model=ProjectMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an existing user to project",
)
def add_member(
    project_id: uuid.UUID,
    data: MemberAddRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ProjectMemberResponse:
    """Add an existing user by email with a designated role. Restricted to project owners."""
    return add_project_member(db, current_user, project_id, data)
