from datetime import date, datetime
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


class MockIdentityOtpRequest(BaseModel):
    demo_identity_id: str = Field(min_length=14, max_length=14, pattern=r"^\d{14}$")

    @field_validator("demo_identity_id", mode="before")
    @classmethod
    def normalize_demo_identity_id(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class MockIdentityOtpRequestResponse(BaseModel):
    masked_mobile: str
    expires_at: datetime


class MockIdentityOtpVerificationRequest(MockIdentityOtpRequest):
    otp: str = Field(min_length=6, max_length=6, pattern=r"^\d{6}$")


class MockIdentityProfileResponse(BaseModel):
    full_name: str
    date_of_birth: date
    age: int
    gender: str
    address: str
    city: str
    state: str
    postal_code: str
    registered_mobile: str


class MockIdentityVerificationResponse(AccessToken):
    profile: MockIdentityProfileResponse