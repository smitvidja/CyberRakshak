import json
from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, field_validator
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
    # "document" runs the real extractor; "mock" is an explicit demo/test fallback and
    # must never be the default, or every upload returns the same invented person.
    resume_parser: str = "document"
    llm_enabled: bool = True
    llm_primary_provider: str = "gemini"
    llm_secondary_provider: str = "grok"
    llm_tertiary_provider: str = "nvidia"
    gemini_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    grok_api_key: SecretStr | None = None
    grok_model: str = "grok-3-mini"
    grok_base_url: str = "https://api.x.ai/v1"
    nvidia_api_key: SecretStr | None = None
    nvidia_model: str = "nvidia/nemotron-3-super-120b-a12b"
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    llm_provider_timeout_seconds: float = Field(default=6.0, ge=0.2, le=10)
    llm_total_timeout_seconds: float = Field(default=8.0, ge=0.5, le=20)
    llm_max_retries: int = Field(default=1, ge=0, le=2)
    llm_max_input_tokens: int = Field(default=3000, ge=500, le=16000)
    llm_max_output_tokens: int = Field(default=600, ge=100, le=2000)
    llm_safety_temperature: float = Field(default=0.1, ge=0, le=1)
    llm_explanation_temperature: float = Field(default=0.25, ge=0, le=1)
    llm_conversation_temperature: float = Field(default=0.4, ge=0, le=1)
    llm_top_p: float = Field(default=0.9, gt=0, le=1)
    # Cyber Saathi knowledge retrieval stays file-backed for the deliberately small,
    # reviewed corpus. Dense embeddings are generated only by explicit ingestion and
    # queried through the configured server-side Gemini credential; no local model is
    # downloaded or loaded at API startup.
    rag_semantic_embeddings_enabled: bool = True
    rag_semantic_embedding_model: str = "gemini-embedding-001"
    rag_semantic_embedding_dimensions: int = Field(default=768, ge=128, le=3072)
    rag_semantic_embedding_timeout_seconds: float = Field(default=1.5, ge=0.2, le=5)
    rag_dense_weight: float = Field(default=0.55, ge=0, le=1)
    rag_sparse_weight: float = Field(default=0.25, ge=0, le=1)
    rag_lexical_weight: float = Field(default=0.20, ge=0, le=1)
    voice_enabled: bool = True
    sarvam_api_key: SecretStr | None = None
    sarvam_base_url: str = "https://api.sarvam.ai"
    sarvam_stt_model: str = "saaras:v4"
    # The realtime endpoint currently accepts the v4 model as "saaras:v4".
    # "saaras:v4-realtime" is rejected by the live service as invalid_model.
    sarvam_realtime_stt_model: str = "saaras:v4"
    sarvam_tts_model: str = "bulbul:v3"
    sarvam_tts_speaker: str = "shubh"
    voice_provider_timeout_seconds: float = Field(default=12.0, ge=1, le=30)
    voice_max_audio_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    voice_max_recording_seconds: int = Field(default=60, ge=1, le=60)

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

    @field_validator(
        "llm_primary_provider", "llm_secondary_provider", "llm_tertiary_provider"
    )
    @classmethod
    def validate_llm_provider(cls, value: str) -> str:
        candidate = value.strip().casefold()
        if candidate not in {"gemini", "grok", "nvidia"}:
            raise ValueError("LLM provider must be gemini, grok, or nvidia")
        return candidate

    @field_validator(
        "gemini_base_url", "grok_base_url", "nvidia_base_url", "sarvam_base_url"
    )
    @classmethod
    def validate_provider_base_url(cls, value: str) -> str:
        candidate = value.rstrip("/")
        if not candidate.startswith("https://"):
            raise ValueError("LLM provider base URLs must use HTTPS")
        return candidate


@lru_cache
def get_settings() -> Settings:
    return Settings()
