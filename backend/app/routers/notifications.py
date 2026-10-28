import uuid
from typing import Dict
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import NotificationListResponse
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get(
    "",
    response_model=NotificationListResponse,
    summary="List notifications for the authenticated user",
)
def list_notifications(
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationListResponse:
    return NotificationService.list_notifications(db, current_user, limit)


@router.patch(
    "/{notification_id}/read",
    summary="Mark a notification as read",
)
def mark_read(
    notification_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, bool]:
    success = NotificationService.mark_as_read(db, current_user, notification_id)
    return {"success": success}


@router.post(
    "/read-all",
    summary="Mark all user notifications as read",
)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Dict[str, int]:
    count = NotificationService.mark_all_read(db, current_user)
    return {"marked_read_count": count}
