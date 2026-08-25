from uuid import UUID

from sqlalchemy.orm import Session

from app.models import AuditLog
from app.repositories.engagement_repository import AuditLogRepository


class AuditService:
    @staticmethod
    def record(
        session: Session,
        *,
        action: str,
        entity_type: str,
        entity_id: UUID | str,
        user_id: UUID | None = None,
        details: dict[str, object] | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=str(entity_id),
            details=details,
        )
        return AuditLogRepository.add(session, audit_log)
