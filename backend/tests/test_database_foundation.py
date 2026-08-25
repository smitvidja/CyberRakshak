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
