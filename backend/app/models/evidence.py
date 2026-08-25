from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.complaint import Complaint
    from app.models.suspect import ReportedSuspect
    from app.models.warrior import WarriorReport


class Evidence(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "evidence"
    __table_args__ = (
        CheckConstraint(
            "((complaint_id IS NOT NULL)::integer + "
            "(suspect_report_id IS NOT NULL)::integer + "
            "(warrior_report_id IS NOT NULL)::integer) = 1",
            name="ck_evidence_single_parent",
        ),
        Index("ix_evidence_complaint_id", "complaint_id"),
        Index("ix_evidence_suspect_report_id", "suspect_report_id"),
        Index("ix_evidence_warrior_report_id", "warrior_report_id"),
    )

    complaint_id: Mapped[UUID | None] = mapped_column(ForeignKey("complaints.id"))
    suspect_report_id: Mapped[UUID | None] = mapped_column(ForeignKey("reported_suspects.id"))
    warrior_report_id: Mapped[UUID | None] = mapped_column(ForeignKey("warrior_reports.id"))
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(255), nullable=False)
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128))
    description: Mapped[str | None] = mapped_column(Text)

    complaint: Mapped[Complaint | None] = relationship(back_populates="evidence_items")
    suspect_report: Mapped[ReportedSuspect | None] = relationship(
        back_populates="evidence_items"
    )
    warrior_report: Mapped[WarriorReport | None] = relationship(
        back_populates="evidence_items"
    )
