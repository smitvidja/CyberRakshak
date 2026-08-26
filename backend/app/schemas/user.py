from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CitizenProfileInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    date_of_birth: date | None = None
    gender: str | None = Field(default=None, max_length=32)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=16)
    alternate_phone: str | None = Field(default=None, min_length=7, max_length=32)

    @field_validator("alternate_phone")
    @classmethod
    def normalize_alternate_phone(cls, value: str | None) -> str | None:
        return value.strip() if value else None


class CitizenProfileResponse(CitizenProfileInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    registered_mobile: str | None
    age: int | None