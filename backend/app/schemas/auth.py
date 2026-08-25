from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import UserRole


class RegistrationRequest(BaseModel):
    email: EmailStr
    phone: str | None = Field(default=None, min_length=7, max_length=32)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.CITIZEN

    @field_validator("phone")
    @classmethod
    def normalize_phone(cls, value: str | None) -> str | None:
        return value.strip() if value else None

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must not be blank.")
        return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    phone: str | None
    role: UserRole
    is_active: bool


class AccessToken(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
