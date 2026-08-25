from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import Notification, User
from app.repositories.engagement_repository import NotificationRepository


class NotificationService:
    @staticmethod
    def create(
        session: Session,
        *,
        user_id: UUID,
        notification_type: str,
        title: str,
        message: str,
        data: dict[str, object] | None = None,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            message=message,
            data=data,
        )
        return NotificationRepository.add(session, notification)

    @staticmethod
    def list_for_current_user(
        session: Session,
        current_user: User,
    ) -> list[Notification]:
        return NotificationRepository.list_for_user(session, current_user.id)

    @staticmethod
    def mark_read(
        session: Session,
        notification_id: UUID,
        current_user: User,
    ) -> Notification:
        notification = NotificationRepository.get_by_id(session, notification_id)
        if notification is None:
            raise APIError(
                status_code=404,
                code="NOT_FOUND",
                message="Notification not found.",
            )
        if notification.user_id != current_user.id:
            raise APIError(
                status_code=403,
                code="FORBIDDEN",
                message="You do not have permission to access this notification.",
            )
        if not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(notification)
        return notification
