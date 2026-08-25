from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import WarriorVerificationStatus


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
    verification_status: WarriorVerificationStatus
    created_at: datetime
    updated_at: datetime
    skills: list[SkillResponse] = Field(default_factory=list)
    education: list[EducationResponse] = Field(default_factory=list)
    experience: list[ExperienceResponse] = Field(default_factory=list)
    certifications: list[CertificationResponse] = Field(default_factory=list)
