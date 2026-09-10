from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ReportedSuspectIdentifierType, ReportedSuspectStatus, SuspectCorrectionStatus


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


class SuspectSearchRequest(BaseModel):
    identifier_type: ReportedSuspectIdentifierType
    identifier_value: str = Field(min_length=2, max_length=500)


class SuspectSearchResponse(BaseModel):
    identifier_type: ReportedSuspectIdentifierType
    masked_identifier: str
    match_state: str
    eligible_report_count: int = Field(ge=0, le=5)
    count_capped: bool
    disclosure_code: str


class SuspectCorrectionCreate(BaseModel):
    identifier_type: ReportedSuspectIdentifierType
    identifier_value: str = Field(min_length=2, max_length=500)
    reason: str = Field(min_length=10, max_length=1000)


class SuspectCorrectionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    identifier_type: ReportedSuspectIdentifierType
    masked_identifier: str
    status: SuspectCorrectionStatus
    created_at: datetime
