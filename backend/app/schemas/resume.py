from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.enums import ResumeParsingStatus


class ResumeParsingResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    resume_file_name: str
    status: ResumeParsingStatus
    extracted_data: dict[str, Any] | None
    error_message: str | None
    processed_at: datetime | None
    confirmed_at: datetime | None
    created_at: datetime
