import uuid
from typing import List
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.models import Project, ProjectMembership, User
from app.schemas import (
    MemberAddRequest,
    ProjectCreateRequest,
    ProjectListResponse,
    ProjectMemberResponse,
    ProjectResponse,
    ProjectUpdateRequest,
)


def create_project(
    db: Session, current_user: User, data: ProjectCreateRequest
) -> ProjectResponse:
    """
    Create a new project and assign the creator the 'owner' role.
    Executed in a transaction to guarantee atomic ownership assignment.
    """
    project = Project(
        name=data.name,
        description=data.description,
        status="active",
    )
    db.add(project)
    db.flush()  # Populates project.id

    membership = ProjectMembership(
        user_id=current_user.id,
        project_id=project.id,
        role="owner",
    )
    db.add(membership)
    db.commit()
    db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        role="owner",
    )


def list_user_projects(
    db: Session, current_user: User, limit: int = 20, offset: int = 0
) -> ProjectListResponse:
    """
    List only projects where the authenticated user is a confirmed member.
    Includes pagination metadata.
    """
    # Count total projects user has access to
    count_stmt = (
        select(func.count(ProjectMembership.id))
        .where(ProjectMembership.user_id == current_user.id)
    )
    total = db.execute(count_stmt).scalar_one()

    # Fetch projects with membership role
    stmt = (
        select(Project, ProjectMembership.role)
        .join(ProjectMembership, Project.id == ProjectMembership.project_id)
        .where(ProjectMembership.user_id == current_user.id)
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    rows = db.execute(stmt).all()

    items = [
        ProjectResponse(
            id=proj.id,
            name=proj.name,
            description=proj.description,
            status=proj.status,
            created_at=proj.created_at,
            updated_at=proj.updated_at,
            role=role,
        )
        for proj, role in rows
    ]

    return ProjectListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


def get_project_for_user(
    db: Session, current_user: User, project_id: uuid.UUID
) -> ProjectResponse:
    """
    Retrieve project details only if the user is a member.
    Returns 404 if project does not exist OR if user is not a member,
    preventing private project existence enumeration.
    """
    stmt = (
        select(Project, ProjectMembership.role)
        .outerjoin(
            ProjectMembership,
            (Project.id == ProjectMembership.project_id)
            & (ProjectMembership.user_id == current_user.id),
        )
        .where(Project.id == project_id)
    )
    result = db.execute(stmt).first()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    project, role = result
    if role is None:
        # User is not a member; do not leak existence of private project
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        role=role,
    )


def update_project_settings(
    db: Session,
    current_user: User,
    project_id: uuid.UUID,
    data: ProjectUpdateRequest,
) -> ProjectResponse:
    """
    Update project settings (name, description, status).
    Restricted to project owners only. Editors and viewers cannot modify project settings.
    """
    stmt = (
        select(Project, ProjectMembership.role)
        .outerjoin(
            ProjectMembership,
            (Project.id == ProjectMembership.project_id)
            & (ProjectMembership.user_id == current_user.id),
        )
        .where(Project.id == project_id)
    )
    result = db.execute(stmt).first()

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    project, role = result
    if role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owners can modify project settings",
        )

    if data.name is not None:
        project.name = data.name
    if data.description is not None:
        project.description = data.description
    if data.status is not None:
        project.status = data.status

    db.commit()
    db.refresh(project)

    return ProjectResponse(
        id=project.id,
        name=project.name,
        description=project.description,
        status=project.status,
        created_at=project.created_at,
        updated_at=project.updated_at,
        role=role,
    )


def list_project_members(
    db: Session, current_user: User, project_id: uuid.UUID
) -> List[ProjectMemberResponse]:
    """
    List members of a project. Authorized for any member (owner, editor, viewer).
    Non-members receive 404 to avoid leaking project existence.
    """
    caller_stmt = select(ProjectMembership.role).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == current_user.id,
    )
    caller_role = db.execute(caller_stmt).scalar_one_or_none()

    if caller_role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    members_stmt = (
        select(ProjectMembership, User.email, User.display_name)
        .join(User, ProjectMembership.user_id == User.id)
        .where(ProjectMembership.project_id == project_id)
        .order_by(ProjectMembership.created_at.asc())
    )
    results = db.execute(members_stmt).all()

    return [
        ProjectMemberResponse(
            id=membership.id,
            user_id=membership.user_id,
            project_id=membership.project_id,
            role=membership.role,
            email=email,
            display_name=display_name,
            created_at=membership.created_at,
        )
        for membership, email, display_name in results
    ]


def add_project_member(
    db: Session,
    current_user: User,
    project_id: uuid.UUID,
    data: MemberAddRequest,
) -> ProjectMemberResponse:
    """
    Add an existing user to a project by email.
    Restricted strictly to project owners.
    Prevents duplicate memberships safely via checks and constraint handling.
    """
    caller_stmt = select(ProjectMembership.role).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == current_user.id,
    )
    caller_role = db.execute(caller_stmt).scalar_one_or_none()

    if caller_role is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if caller_role != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only project owners can add members",
        )

    target_email = data.email.strip().lower()
    user_stmt = select(User).where(User.email == target_email)
    target_user = db.execute(user_stmt).scalar_one_or_none()

    if target_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User with this email address does not exist",
        )

    # Check for existing membership
    existing_stmt = select(ProjectMembership).where(
        ProjectMembership.project_id == project_id,
        ProjectMembership.user_id == target_user.id,
    )
    existing_membership = db.execute(existing_stmt).scalar_one_or_none()

    if existing_membership is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this project",
        )

    membership = ProjectMembership(
        project_id=project_id,
        user_id=target_user.id,
        role=data.role,
    )

    try:
        db.add(membership)
        db.commit()
        db.refresh(membership)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already a member of this project",
        )

    return ProjectMemberResponse(
        id=membership.id,
        user_id=target_user.id,
        project_id=project_id,
        role=membership.role,
        email=target_user.email,
        display_name=target_user.display_name,
        created_at=membership.created_at,
    )
