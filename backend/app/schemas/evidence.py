from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class EvidenceUploadTarget(BaseModel):
    complaint_id: UUID | None = None
    suspect_report_id: UUID | None = None
    warrior_report_id: UUID | None = None
    description: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def require_exactly_one_parent(self) -> "EvidenceUploadTarget":
        parent_count = sum(
            value is not None
            for value in (
                self.complaint_id,
                self.suspect_report_id,
                self.warrior_report_id,
            )
        )
        if parent_count != 1:
            raise ValueError("Evidence must be attached to exactly one supported parent.")
        return self


class EvidenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    complaint_id: UUID | None
    suspect_report_id: UUID | None
    warrior_report_id: UUID | None
    file_name: str
    mime_type: str
    file_size: int
    checksum: str | None
    description: str | None
    created_at: datetime
