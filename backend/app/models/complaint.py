from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import ComplaintPriority, ComplaintStatus
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.user import User


class ComplaintCategory(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "complaint_categories"

    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    complaints: Mapped[list[Complaint]] = relationship(back_populates="category")


class Complaint(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "complaints"
    __table_args__ = (
        CheckConstraint(
            "(is_anonymous AND user_id IS NULL) OR "
            "(NOT is_anonymous AND user_id IS NOT NULL)",
            name="ck_complaints_anonymous_identity",
        ),
        Index("ix_complaints_user_id", "user_id"),
        Index("ix_complaints_category_id", "category_id"),
        Index("ix_complaints_status", "status"),
        Index("ix_complaints_created_at", "created_at"),
    )

    complaint_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("complaint_categories.id"),
        nullable=False,
    )
    is_anonymous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    incident_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    financial_loss_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaint_status"),
        nullable=False,
        default=ComplaintStatus.DRAFT,
    )
    priority: Mapped[ComplaintPriority] = mapped_column(
        Enum(ComplaintPriority, name="complaint_priority"),
        nullable=False,
        default=ComplaintPriority.NORMAL,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    user: Mapped[User | None] = relationship(back_populates="complaints")
    category: Mapped[ComplaintCategory] = relationship(back_populates="complaints")
    location: Mapped[ComplaintLocation | None] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
        uselist=False,
    )
    suspects: Mapped[list[ComplaintSuspect]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
    )
    status_history: Mapped[list[ComplaintStatusHistory]] = relationship(
        back_populates="complaint",
        cascade="all, delete-orphan",
    )
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="complaint")


class ComplaintLocation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "complaint_locations"

    complaint_id: Mapped[UUID] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(128))
    district: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str | None] = mapped_column(String(128))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))

    complaint: Mapped[Complaint] = relationship(back_populates="location")


class ComplaintSuspect(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "complaint_suspects"
    __table_args__ = (Index("ix_complaint_suspects_complaint_id", "complaint_id"),)

    complaint_id: Mapped[UUID] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str | None] = mapped_column(String(255))
    alias: Mapped[str | None] = mapped_column(String(255))
    contact_details: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)

    complaint: Mapped[Complaint] = relationship(back_populates="suspects")


class ComplaintStatusHistory(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "complaint_status_history"
    __table_args__ = (
        Index("ix_complaint_status_history_complaint_id", "complaint_id"),
    )

    complaint_id: Mapped[UUID] = mapped_column(
        ForeignKey("complaints.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[ComplaintStatus] = mapped_column(
        Enum(ComplaintStatus, name="complaint_status", create_type=False),
        nullable=False,
    )
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    complaint: Mapped[Complaint] = relationship(back_populates="status_history")
