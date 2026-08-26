from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import UserRole
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.complaint import Complaint
    from app.models.engagement import AuditLog, Notification
    from app.models.mock_identity import MockIdentityProfile
    from app.models.suspect import ReportedSuspect
    from app.models.warrior import CyberWarriorProfile


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (Index("ix_users_role", "role"),)

    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role"),
        nullable=False,
        default=UserRole.CITIZEN,
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    citizen_profile: Mapped[CitizenProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    mock_identity_profile: Mapped[MockIdentityProfile | None] = relationship(
        back_populates="user",
        uselist=False,
    )
    cyber_warrior_profile: Mapped[CyberWarriorProfile | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )
    complaints: Mapped[list[Complaint]] = relationship(back_populates="user")
    reported_suspects: Mapped[list[ReportedSuspect]] = relationship(back_populates="user")
    notifications: Mapped[list[Notification]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(back_populates="user")


class CitizenProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "citizen_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    date_of_birth: Mapped[date | None] = mapped_column(Date)
    gender: Mapped[str | None] = mapped_column(String(32))
    address: Mapped[str | None] = mapped_column(String(500))
    city: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str | None] = mapped_column(String(128))
    postal_code: Mapped[str | None] = mapped_column(String(16))
    alternate_phone: Mapped[str | None] = mapped_column(String(32))

    user: Mapped[User] = relationship(back_populates="citizen_profile")

    @property
    def registered_mobile(self) -> str | None:
        return self.user.phone if self.user else None

    @property
    def age(self) -> int | None:
        if self.date_of_birth is None:
            return None
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )