from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.user import User


class MockIdentityProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Synthetic-only identity data used by the local prototype eKYC flow."""

    __tablename__ = "mock_identity_profiles"

    demo_identity_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    synthetic_email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    registered_mobile: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    gender: Mapped[str] = mapped_column(String(32), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    state: Mapped[str] = mapped_column(String(128), nullable=False)
    postal_code: Mapped[str] = mapped_column(String(16), nullable=False)
    otp_code_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    otp_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    otp_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        unique=True,
    )

    user: Mapped[User | None] = relationship(back_populates="mock_identity_profile")