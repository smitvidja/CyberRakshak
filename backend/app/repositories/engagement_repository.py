from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Notification


class NotificationRepository:
    @staticmethod
    def add(session: Session, notification: Notification) -> Notification:
        session.add(notification)
        return notification

    @staticmethod
    def get_by_id(session: Session, notification_id: UUID) -> Notification | None:
        return session.get(Notification, notification_id)

    @staticmethod
    def list_for_user(session: Session, user_id: UUID) -> list[Notification]:
        statement = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
        )
        return list(session.scalars(statement))


class AuditLogRepository:
    @staticmethod
    def add(session: Session, audit_log: AuditLog) -> AuditLog:
        session.add(audit_log)
        return audit_log
