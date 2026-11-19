from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import WarriorVerificationStatus

# "Availability & Preferences" (Step 14 profile reference). Fixed codes rather than
# free text: the UI translates them (EN/HI) and they cannot carry personal data.
Availability = Literal["UNDER_5", "5_TO_10", "10_TO_15", "15_TO_20", "OVER_20"]
PreferredTask = Literal[
    "REPORT_REVIEW", "EVIDENCE_ANALYSIS", "AWARENESS", "OSINT_RESEARCH", "VICTIM_SUPPORT", "TRANSLATION"
]
PreferredCommunication = Literal["EMAIL", "PORTAL", "SMS"]


def _no_duplicates(value: list[str] | None) -> list[str] | None:
    if value is not None and len(set(value)) != len(value):
        raise ValueError("Each option may be selected only once.")
    return value


class ProfileCreate(BaseModel):
    display_name: str = Field(min_length=2, max_length=255)
    bio: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=255)
    github_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)


class ProfileUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=255)
    bio: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=255)
    github_url: str | None = Field(default=None, max_length=500)
    linkedin_url: str | None = Field(default=None, max_length=500)
    availability: Availability | None = None
    preferred_tasks: list[PreferredTask] | None = Field(default=None, max_length=6)
    preferred_communication: list[PreferredCommunication] | None = Field(default=None, max_length=3)
    willing_to_volunteer: bool | None = None

    _unique_tasks = field_validator("preferred_tasks")(_no_duplicates)
    _unique_channels = field_validator("preferred_communication")(_no_duplicates)


class SkillInput(BaseModel):
    skill_id: UUID
    proficiency_level: str | None = Field(default=None, max_length=64)
    years_of_experience: int | None = Field(default=None, ge=0, le=80)


class EducationInput(BaseModel):
    institution: str = Field(min_length=2, max_length=255)
    degree: str = Field(min_length=2, max_length=255)
    field_of_study: str | None = Field(default=None, max_length=255)
    started_on: date | None = None
    completed_on: date | None = None


class ExperienceInput(BaseModel):
    organization: str = Field(min_length=2, max_length=255)
    title: str = Field(min_length=2, max_length=255)
    description: str | None = Field(default=None, max_length=5000)
    started_on: date | None = None
    ended_on: date | None = None
    is_current: bool = False


class CertificationInput(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    issuing_organization: str | None = Field(default=None, max_length=255)
    credential_id: str | None = Field(default=None, max_length=255)
    credential_url: str | None = Field(default=None, max_length=500)
    issued_on: date | None = None
    expires_on: date | None = None


class ResumeConfirmationRequest(ProfileCreate):
    skills: list[SkillInput] = Field(default_factory=list)
    education: list[EducationInput] = Field(default_factory=list)
    experience: list[ExperienceInput] = Field(default_factory=list)
    certifications: list[CertificationInput] = Field(default_factory=list)

    @field_validator("skills")
    @classmethod
    def unique_skill_ids(cls, value: list[SkillInput]) -> list[SkillInput]:
        if len({item.skill_id for item in value}) != len(value):
            raise ValueError("Each skill may be selected only once.")
        return value


class SkillResponse(SkillInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class SkillCatalogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    category: str | None
    description: str | None


class EducationResponse(EducationInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class ExperienceResponse(ExperienceInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class CertificationResponse(CertificationInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class CyberWarriorProfileResponse(ProfileCreate):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    warrior_code: str
    verification_status: WarriorVerificationStatus
    availability: str | None = None
    preferred_tasks: list[str] | None = None
    preferred_communication: list[str] | None = None
    willing_to_volunteer: bool | None = None
    created_at: datetime
    updated_at: datetime
    skills: list[SkillResponse] = Field(default_factory=list)
    education: list[EducationResponse] = Field(default_factory=list)
    experience: list[ExperienceResponse] = Field(default_factory=list)
    certifications: list[CertificationResponse] = Field(default_factory=list)
