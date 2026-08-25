from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportedSuspectIdentifierType, ReportedSuspectStatus


class ReportedSuspectCreate(BaseModel):
    identifier_type: ReportedSuspectIdentifierType
    identifier_value: str = Field(min_length=2, max_length=500)
    description: str | None = None


class ReportedSuspectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_type: ReportedSuspectIdentifierType
    identifier_value: str
    description: str | None
    status: ReportedSuspectStatus
    created_at: datetime
