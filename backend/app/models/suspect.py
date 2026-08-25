from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ReportedSuspectIdentifierType, ReportedSuspectStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.user import User


class ReportedSuspect(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "reported_suspects"
    __table_args__ = (
        Index("ix_reported_suspects_identifier_type", "identifier_type"),
        Index("ix_reported_suspects_identifier_value", "identifier_value"),
        Index("ix_reported_suspects_status", "status"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    identifier_type: Mapped[ReportedSuspectIdentifierType] = mapped_column(
        Enum(ReportedSuspectIdentifierType, name="reported_suspect_identifier_type"),
        nullable=False,
    )
    identifier_value: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[ReportedSuspectStatus] = mapped_column(
        Enum(ReportedSuspectStatus, name="reported_suspect_status"),
        nullable=False,
        default=ReportedSuspectStatus.SUBMITTED,
    )

    user: Mapped[User] = relationship(back_populates="reported_suspects")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="suspect_report")
