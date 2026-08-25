from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import WarriorApplicationStatus, WarriorReportStatus, WarriorReportType


class WarriorApplicationCreate(BaseModel):
    statement: str | None = Field(default=None, max_length=5000)


class WarriorApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    application_number: str
    status: WarriorApplicationStatus
    statement: str | None
    submitted_at: datetime | None
    reviewed_at: datetime | None
    review_note: str | None
    created_at: datetime
    updated_at: datetime


class WarriorReportCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10, max_length=10000)
    report_type: WarriorReportType


class WarriorReportUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10, max_length=10000)
    report_type: WarriorReportType | None = None


class WarriorReportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    report_type: WarriorReportType
    status: WarriorReportStatus
    submitted_at: datetime | None
    created_at: datetime
    updated_at: datetime
