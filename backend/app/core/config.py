import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "CyberRakshak API"
    app_environment: str = "development"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    database_url: str = Field(..., min_length=1)
    secret_key: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    # 30 days by default: there is no refresh-token flow in this MVP, so the access token IS
    # the whole session. A short (60 min) expiry was silently killing "stay logged in until you
    # explicitly log out" - the token would go stale while localStorage still held it, so API
    # calls started failing with no login screen and no visible cause. Overridable via env for
    # a stricter deployment.
    access_token_expire_minutes: int = Field(default=43200, ge=5, le=129600)
    # NoDecode is required, not cosmetic: without it pydantic-settings runs json.loads()
    # on this value before any validator sees it, so a plain
    # "https://app.example.com,https://www.example.com" - the format hosting platforms
    # (Railway/Render/Fly/Heroku) actually use - raised SettingsError and the backend
    # refused to start. Even a single bare URL failed; only JSON array syntax worked.
    # NoDecode hands the raw string to parse_cors_origins below, which accepts both.
    cors_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ]
    )
    local_storage_path: str = "storage"
    evidence_max_file_size: int = Field(default=10 * 1024 * 1024, ge=1)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        """Accept a JSON array, a comma-separated list, or a single origin.

        All three are used in practice: .env.example ships the JSON form, while
        hosting dashboards generally only let you paste a plain string.
        """
        if not isinstance(value, str):
            return value
        candidate = value.strip()
        if candidate.startswith("["):
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    "CORS_ORIGINS looks like a JSON array but is not valid JSON. "
                    'Use ["https://a.com","https://b.com"] or a comma-separated list.'
                ) from exc
            if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
                raise ValueError("CORS_ORIGINS JSON must be an array of strings.")
            return [origin.strip() for origin in parsed if origin.strip()]
        return [origin.strip() for origin in candidate.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
