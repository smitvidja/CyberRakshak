from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import CyberSaathiConversation


class CyberSaathiRepository:
    @staticmethod
    def get(session: Session, conversation_id: UUID) -> CyberSaathiConversation | None:
        return session.get(CyberSaathiConversation, conversation_id)

    @staticmethod
    def save(session: Session, conversation: CyberSaathiConversation) -> CyberSaathiConversation:
        return session.merge(conversation)

    @staticmethod
    def count_expired(session: Session, now: datetime) -> int:
        return int(
            session.scalar(
                select(func.count())
                .select_from(CyberSaathiConversation)
                .where(CyberSaathiConversation.expires_at < now)
            )
            or 0
        )

    @staticmethod
    def delete_expired(session: Session, now: datetime) -> int:
        result = session.execute(
            delete(CyberSaathiConversation).where(CyberSaathiConversation.expires_at < now)
        )
        return int(result.rowcount or 0)
