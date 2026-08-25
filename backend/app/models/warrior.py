from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.enums import (
    ResumeParsingStatus,
    WarriorApplicationStatus,
    WarriorReportStatus,
    WarriorReportType,
    WarriorVerificationStatus,
)
from app.models.mixins import TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.evidence import Evidence
    from app.models.user import User


class CyberWarriorProfile(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "cyber_warrior_profiles"

    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    bio: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(255))
    github_url: Mapped[str | None] = mapped_column(String(500))
    linkedin_url: Mapped[str | None] = mapped_column(String(500))
    verification_status: Mapped[WarriorVerificationStatus] = mapped_column(
        Enum(WarriorVerificationStatus, name="warrior_verification_status"),
        nullable=False,
        default=WarriorVerificationStatus.PENDING,
    )

    user: Mapped[User] = relationship(back_populates="cyber_warrior_profile")
    skills: Mapped[list[WarriorSkill]] = relationship(
        back_populates="warrior",
        cascade="all, delete-orphan",
    )
    education: Mapped[list[WarriorEducation]] = relationship(
        back_populates="warrior",
        cascade="all, delete-orphan",
    )
    experience: Mapped[list[WarriorExperience]] = relationship(
        back_populates="warrior",
        cascade="all, delete-orphan",
    )
    certifications: Mapped[list[WarriorCertification]] = relationship(
        back_populates="warrior",
        cascade="all, delete-orphan",
    )
    applications: Mapped[list[WarriorApplication]] = relationship(back_populates="warrior")
    resume_parsing_results: Mapped[list[ResumeParsingResult]] = relationship(
        back_populates="warrior"
    )
    reports: Mapped[list[WarriorReport]] = relationship(back_populates="warrior")


class Skill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    category: Mapped[str | None] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)

    warrior_skills: Mapped[list[WarriorSkill]] = relationship(back_populates="skill")


class WarriorSkill(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warrior_skills"
    __table_args__ = (UniqueConstraint("warrior_id", "skill_id", name="uq_warrior_skills_pair"),)

    warrior_id: Mapped[UUID] = mapped_column(
        ForeignKey("cyber_warrior_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    skill_id: Mapped[UUID] = mapped_column(ForeignKey("skills.id"), nullable=False)
    proficiency_level: Mapped[str | None] = mapped_column(String(64))
    years_of_experience: Mapped[int | None] = mapped_column(Integer)

    warrior: Mapped[CyberWarriorProfile] = relationship(back_populates="skills")
    skill: Mapped[Skill] = relationship(back_populates="warrior_skills")


class WarriorEducation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warrior_education"

    warrior_id: Mapped[UUID] = mapped_column(
        ForeignKey("cyber_warrior_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    degree: Mapped[str] = mapped_column(String(255), nullable=False)
    field_of_study: Mapped[str | None] = mapped_column(String(255))
    started_on: Mapped[date | None] = mapped_column(Date)
    completed_on: Mapped[date | None] = mapped_column(Date)

    warrior: Mapped[CyberWarriorProfile] = relationship(back_populates="education")


class WarriorExperience(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warrior_experience"

    warrior_id: Mapped[UUID] = mapped_column(
        ForeignKey("cyber_warrior_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    organization: Mapped[str] = mapped_column(String(255), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    started_on: Mapped[date | None] = mapped_column(Date)
    ended_on: Mapped[date | None] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    warrior: Mapped[CyberWarriorProfile] = relationship(back_populates="experience")


class WarriorCertification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warrior_certifications"

    warrior_id: Mapped[UUID] = mapped_column(
        ForeignKey("cyber_warrior_profiles.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    issuing_organization: Mapped[str | None] = mapped_column(String(255))
    credential_id: Mapped[str | None] = mapped_column(String(255))
    credential_url: Mapped[str | None] = mapped_column(String(500))
    issued_on: Mapped[date | None] = mapped_column(Date)
    expires_on: Mapped[date | None] = mapped_column(Date)

    warrior: Mapped[CyberWarriorProfile] = relationship(back_populates="certifications")


class WarriorApplication(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warrior_applications"

    warrior_id: Mapped[UUID] = mapped_column(
        ForeignKey("cyber_warrior_profiles.id"),
        nullable=False,
    )
    application_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[WarriorApplicationStatus] = mapped_column(
        Enum(WarriorApplicationStatus, name="warrior_application_status"),
        nullable=False,
        default=WarriorApplicationStatus.DRAFT,
    )
    statement: Mapped[str | None] = mapped_column(Text)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)

    warrior: Mapped[CyberWarriorProfile] = relationship(back_populates="applications")


class ResumeParsingResult(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "resume_parsing_results"

    warrior_id: Mapped[UUID] = mapped_column(
        ForeignKey("cyber_warrior_profiles.id"),
        nullable=False,
    )
    resume_file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    resume_storage_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[ResumeParsingStatus] = mapped_column(
        Enum(ResumeParsingStatus, name="resume_parsing_status"),
        nullable=False,
        default=ResumeParsingStatus.PENDING,
    )
    extracted_data: Mapped[dict[str, object] | None] = mapped_column(JSONB)
    error_message: Mapped[str | None] = mapped_column(Text)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    warrior: Mapped[CyberWarriorProfile] = relationship(
        back_populates="resume_parsing_results"
    )


class WarriorReport(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "warrior_reports"

    warrior_id: Mapped[UUID] = mapped_column(
        ForeignKey("cyber_warrior_profiles.id"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    report_type: Mapped[WarriorReportType] = mapped_column(
        Enum(WarriorReportType, name="warrior_report_type"),
        nullable=False,
    )
    status: Mapped[WarriorReportStatus] = mapped_column(
        Enum(WarriorReportStatus, name="warrior_report_status"),
        nullable=False,
        default=WarriorReportStatus.DRAFT,
    )
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    warrior: Mapped[CyberWarriorProfile] = relationship(back_populates="reports")
    evidence_items: Mapped[list[Evidence]] = relationship(back_populates="warrior_report")
