import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.errors import APIError
from app.models import CyberSaathiConversation
from app.repositories.cyber_saathi_repository import CyberSaathiRepository
from app.schemas.cyber_saathi import ConversationState


SENSITIVE_PATTERNS = (
    (re.compile(r"(?<!\w)[\w.+-]+@[a-z0-9.-]+\.[a-z]{2,}(?!\w)", re.I), "[REDACTED_EMAIL]"),
    (re.compile(r"(?<!\d)(?:\+91[ -]?)?[6-9]\d{4}[ -]?\d{5}(?!\d)"), "[REDACTED_PHONE]"),
    (re.compile(r"(?<!\d)\d{12,16}(?!\d)"), "[REDACTED_IDENTIFIER]"),
    (re.compile(r"(?<![\w.])[a-z0-9._-]{2,}@(upi|ybl|paytm|okaxis|okhdfcbank|oksbi|ibl|axl)(?![\w.])", re.I), "[REDACTED_UPI]"),
)
UUID_PATTERN = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.I)


def redact_text(value: str) -> str:
    if UUID_PATTERN.fullmatch(value):
        return value
    redacted = value
    for pattern, replacement in SENSITIVE_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def _redact(value):
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, list):
        return [_redact(item) for item in value]
    if isinstance(value, dict):
        return {key: _redact(item) for key, item in value.items()}
    return value


class CyberSaathiPersistence:
    @staticmethod
    def save(session: Session, state: ConversationState) -> None:
        if not state.storage_consent:
            return
        now = datetime.now(timezone.utc)
        existing = CyberSaathiRepository.get(session, state.id)
        record = existing or CyberSaathiConversation(
            id=state.id,
            state={},
            feedback=[],
            consented_at=now,
            expires_at=now + timedelta(days=30),
        )
        record.state = _redact(state.model_dump(mode="json"))
        record.expires_at = now + timedelta(days=30)
        CyberSaathiRepository.save(session, record)
        session.commit()

    @staticmethod
    def load(session: Session, conversation_id) -> ConversationState:
        record = CyberSaathiRepository.get(session, conversation_id)
        if record is None or record.expires_at < datetime.now(timezone.utc):
            raise APIError(status_code=404, code="CONVERSATION_NOT_FOUND", message="Saved conversation not found.")
        return ConversationState.model_validate(record.state)

    @staticmethod
    def add_feedback(session: Session, conversation_id, rating: int, comment: str | None) -> None:
        record = CyberSaathiRepository.get(session, conversation_id)
        if record is None:
            raise APIError(status_code=404, code="CONVERSATION_NOT_FOUND", message="Saved conversation not found.")
        feedback = list(record.feedback or [])
        feedback.append({"rating": rating, "comment": redact_text(comment or "")[:1000]})
        record.feedback = feedback[-20:]
        record.quality_score = Decimal(str(sum(item["rating"] for item in record.feedback) / len(record.feedback)))
        record.review_status = "PENDING"
        record.eligible_for_reviewed_cache = False
        session.commit()
