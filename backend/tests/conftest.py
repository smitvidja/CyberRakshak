import os
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

os.environ.setdefault(
    "DATABASE_URL",
    "postgresql+psycopg://cyberrakshak:cyberrakshak_local_only@localhost:5432/cyberrakshak",
)
os.environ.setdefault(
    "SECRET_KEY",
    "test-only-secret-key-that-is-long-enough-for-session-three",
)
# Test runs must never call paid/live LLM providers even when a developer has
# configured real keys in backend/.env. Provider behavior is covered with mocks.
os.environ.setdefault("LLM_ENABLED", "false")
os.environ.setdefault("VOICE_ENABLED", "false")

from app.core.database import SessionLocal, engine, get_db_session
from app.core.public_rate_limit import (
    suspect_correction_rate_limiter,
    suspect_search_rate_limiter,
)
from app.main import app


@pytest.fixture(autouse=True)
def _reset_public_rate_limiters() -> None:
    """Public limiters are process-global and the TestClient has no real address.

    Without this every test in the run shares one bucket, so adding a test that
    happens to be the 31st public call makes an unrelated test fail with a 429.
    """
    suspect_search_rate_limiter.reset()
    suspect_correction_rate_limiter.reset()


@pytest.fixture
def api_client() -> Iterator[tuple[TestClient, Session]]:
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    def override_db_session() -> Iterator[Session]:
        yield session

    app.dependency_overrides[get_db_session] = override_db_session
    try:
        with TestClient(app) as client:
            yield client, session
    finally:
        app.dependency_overrides.clear()
        session.close()
        transaction.rollback()
        connection.close()
