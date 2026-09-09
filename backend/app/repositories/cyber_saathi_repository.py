from uuid import UUID

from sqlalchemy.orm import Session

from app.models import CyberSaathiConversation


class CyberSaathiRepository:
    @staticmethod
    def get(session: Session, conversation_id: UUID) -> CyberSaathiConversation | None:
        return session.get(CyberSaathiConversation, conversation_id)

    @staticmethod
    def save(session: Session, conversation: CyberSaathiConversation) -> CyberSaathiConversation:
        return session.merge(conversation)
