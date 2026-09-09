from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Numeric, String
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
