from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ComplaintStatus, ReportedSuspectStatus, WarriorApplicationStatus


class ComplaintStatusUpdate(BaseModel):
    status: ComplaintStatus
    note: str | None = Field(default=None, max_length=2000)


class ReportedSuspectStatusUpdate(BaseModel):
    status: ReportedSuspectStatus


class WarriorApplicationStatusUpdate(BaseModel):
    status: WarriorApplicationStatus
    review_note: str | None = Field(default=None, max_length=2000)


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID | None
    action: str
    entity_type: str
    entity_id: str
    details: dict[str, Any] | None
    created_at: datetime
