from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class CitizenProfileInput(BaseModel):
    full_name: str = Field(min_length=2, max_length=255)
    address: str | None = Field(default=None, max_length=500)
    city: str | None = Field(default=None, max_length=128)
    state: str | None = Field(default=None, max_length=128)
    postal_code: str | None = Field(default=None, max_length=16)


class CitizenProfileResponse(CitizenProfileInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
