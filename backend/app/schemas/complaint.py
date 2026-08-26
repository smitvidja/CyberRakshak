from datetime import datetime, timezone
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import ComplaintPriority, ComplaintStatus


def validate_incident_at(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    normalized = value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value
    if normalized > datetime.now(timezone.utc):
        raise ValueError("The incident date and time cannot be in the future.")
    return normalized


class ComplaintLocationInput(BaseModel):
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=128)
    district: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=16)
    latitude: Decimal | None = None
    longitude: Decimal | None = None


class ComplaintSuspectInput(BaseModel):
    name: str | None = Field(default=None, max_length=255)
    alias: str | None = Field(default=None, max_length=255)
    contact_details: str | None = Field(default=None, max_length=500)
    description: str | None = None


class ComplaintDraftCreate(BaseModel):
    category_id: UUID
    is_anonymous: bool
    reporting_for: Literal["SELF", "CHILD", "OTHER"] = "SELF"
    affected_person_name: str | None = Field(default=None, max_length=255)
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(min_length=10)
    incident_at: datetime | None = None
    financial_loss_amount: Decimal | None = Field(default=None, ge=0)
    priority: ComplaintPriority = ComplaintPriority.NORMAL
    location: ComplaintLocationInput | None = None
    suspects: list[ComplaintSuspectInput] = Field(default_factory=list)

    @field_validator("incident_at")
    @classmethod
    def reject_future_incident(cls, value: datetime | None) -> datetime | None:
        return validate_incident_at(value)


class ComplaintDraftUpdate(BaseModel):
    category_id: UUID | None = None
    reporting_for: Literal["SELF", "CHILD", "OTHER"] | None = None
    affected_person_name: str | None = Field(default=None, max_length=255)
    title: str | None = Field(default=None, min_length=3, max_length=255)
    description: str | None = Field(default=None, min_length=10)
    incident_at: datetime | None = None
    financial_loss_amount: Decimal | None = Field(default=None, ge=0)
    priority: ComplaintPriority | None = None
    location: ComplaintLocationInput | None = None
    suspects: list[ComplaintSuspectInput] | None = None

    @field_validator("incident_at")
    @classmethod
    def reject_future_incident(cls, value: datetime | None) -> datetime | None:
        return validate_incident_at(value)


class ComplaintCategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    name: str
    description: str | None


class ComplaintLocationResponse(ComplaintLocationInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class ComplaintSuspectResponse(ComplaintSuspectInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID


class ComplaintSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    complaint_number: str
    is_anonymous: bool
    reporting_for: str
    affected_person_name: str | None
    title: str
    status: ComplaintStatus
    priority: ComplaintPriority
    created_at: datetime
    submitted_at: datetime | None


class ComplaintResponse(ComplaintSummaryResponse):
    model_config = ConfigDict(from_attributes=True)

    category: ComplaintCategoryResponse
    description: str
    incident_at: datetime | None
    financial_loss_amount: Decimal | None
    location: ComplaintLocationResponse | None
    suspects: list[ComplaintSuspectResponse]


class ComplaintStatusHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: ComplaintStatus
    note: str | None
    created_at: datetime


class ComplaintTrackingHistoryItem(BaseModel):
    status: ComplaintStatus
    created_at: datetime


class ComplaintTrackingResponse(BaseModel):
    complaint_number: str
    status: ComplaintStatus
    priority: ComplaintPriority
    created_at: datetime
    submitted_at: datetime | None
    history: list[ComplaintTrackingHistoryItem] = Field(default_factory=list)