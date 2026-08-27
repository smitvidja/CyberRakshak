import pytest
from pydantic import ValidationError

from app.core.config import Settings, get_settings
from app.core.database import SessionLocal, engine
from app.models import Base


def test_database_engine_uses_postgresql() -> None:
    assert engine.url.get_backend_name() == "postgresql"
    assert SessionLocal.kw["autoflush"] is False
    assert SessionLocal.kw["expire_on_commit"] is False


def test_metadata_is_available_for_migrations() -> None:
    assert "users" in Base.metadata.tables


def test_database_url_is_required_without_environment_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)

    get_settings.cache_clear()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ('["https://a.example.com","https://b.example.com"]', ["https://a.example.com", "https://b.example.com"]),
        ("https://a.example.com,https://b.example.com", ["https://a.example.com", "https://b.example.com"]),
        ("https://a.example.com, https://b.example.com", ["https://a.example.com", "https://b.example.com"]),
        ("https://a.example.com", ["https://a.example.com"]),
        ("https://a.example.com,", ["https://a.example.com"]),
    ],
)
def test_cors_origins_accepts_every_format_a_host_might_supply(
    monkeypatch: pytest.MonkeyPatch, raw: str, expected: list[str]
) -> None:
    """Hosting dashboards generally only accept a plain string, while .env.example
    ships a JSON array. Before NoDecode was applied, pydantic-settings json-decoded
    this field before any validator ran, so every non-JSON form raised SettingsError
    and the backend would not boot in a deployed environment."""
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/d")
    monkeypatch.setenv("SECRET_KEY", "a-test-only-secret-key-that-is-long-enough")
    monkeypatch.setenv("CORS_ORIGINS", raw)

    assert Settings(_env_file=None).cors_origins == expected

    get_settings.cache_clear()


def test_cors_origins_rejects_malformed_json_with_a_clear_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/d")
    monkeypatch.setenv("SECRET_KEY", "a-test-only-secret-key-that-is-long-enough")
    monkeypatch.setenv("CORS_ORIGINS", '["https://a.example.com"')

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(_env_file=None)

    get_settings.cache_clear()


def test_wildcard_cors_origin_is_never_the_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """The API sends credentials, so a "*" origin must never be the fallback."""
    monkeypatch.delenv("CORS_ORIGINS", raising=False)
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/d")
    monkeypatch.setenv("SECRET_KEY", "a-test-only-secret-key-that-is-long-enough")

    assert "*" not in Settings(_env_file=None).cors_origins

    get_settings.cache_clear()
