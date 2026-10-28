import uuid
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.models import Notification, User
from app.schemas import NotificationListResponse, NotificationResponse


class NotificationService:
    """
    User notification management service for handoff status changes,
    successor assignments, reviews, and acknowledgements.
    """

    @classmethod
    def list_notifications(
        cls,
        db: Session,
        current_user: User,
        limit: int = 50,
    ) -> NotificationListResponse:
        """List notifications for the authenticated user."""
        stmt = (
            select(Notification)
            .where(Notification.user_id == current_user.id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
        )
        notifs = db.execute(stmt).scalars().all()

        unread_count_stmt = select(func.count(Notification.id)).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        unread_count = db.execute(unread_count_stmt).scalar_one()

        items = [
            NotificationResponse(
                id=n.id,
                user_id=n.user_id,
                project_id=n.project_id,
                title=n.title,
                message=n.message,
                notification_type=n.notification_type,
                link=n.link,
                is_read=n.is_read,
                created_at=n.created_at,
            )
            for n in notifs
        ]

        return NotificationListResponse(items=items, unread_count=unread_count)

    @classmethod
    def mark_as_read(
        cls,
        db: Session,
        current_user: User,
        notification_id: uuid.UUID,
    ) -> bool:
        """Mark a specific notification as read."""
        notif = db.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if notif:
            notif.is_read = True
            db.commit()
            return True
        return False

    @classmethod
    def mark_all_read(
        cls,
        db: Session,
        current_user: User,
    ) -> int:
        """Mark all notifications as read for current user."""
        stmt = select(Notification).where(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
        unread = db.execute(stmt).scalars().all()
        for n in unread:
            n.is_read = True
        db.commit()
        return len(unread)
