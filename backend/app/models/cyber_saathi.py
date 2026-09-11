from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin


class CyberSaathiConversation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cyber_saathi_conversations"

    state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    feedback: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    consented_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    review_status: Mapped[str] = mapped_column(String(24), nullable=False, default="PENDING")
    quality_score: Mapped[Decimal | None] = mapped_column(Numeric(4, 3))
    eligible_for_reviewed_cache: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class KnowledgeGapSignal(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A question the authoritative corpus could not answer.

    This is the input to growing the corpus, and it deliberately stores the
    *question*, never an answer. Citizen text is not an authoritative source: it
    is unverified, and anything that promoted it into the retrieval corpus would
    let whoever typed it write the guidance the next citizen receives. So a
    signal records that a domain came up short and what was asked, and a person
    then finds a real source. See 08-SECURITY.md.

    Rows are aggregated by question_digest, so a question asked forty times is
    one row with occurrences=40 rather than forty rows - which is also what makes
    "we have enough data about X now" a number a reviewer can sort by.
    """

    __tablename__ = "knowledge_gap_signals"

    # SHA-256 of the normalised redacted question. Groups repeats; never reversed.
    # No standalone index: the composite unique (question_digest, crime_domain)
    # in the migration covers digest lookups and is what makes recording an upsert.
    question_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    # Redacted sample of how it was asked, so a reviewer can see the real wording.
    sample_question: Mapped[str] = mapped_column(String(500), nullable=False)
    crime_domain: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    knowledge_domain: Mapped[str | None] = mapped_column(String(64))
    language: Mapped[str] = mapped_column(String(16), nullable=False)
    occurrences: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # OPEN -> REVIEWED -> ACTIONED, or DISMISSED.
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="OPEN", index=True)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
