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

from app.core.database import SessionLocal, engine, get_db_session
from app.main import app


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
