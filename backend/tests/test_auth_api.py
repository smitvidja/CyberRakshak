import asyncio
from collections.abc import Iterator
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.database import SessionLocal, engine, get_db_session
from app.core.errors import APIError
from app.core.security import (
    ensure_resource_owner,
    hash_password,
    require_roles,
    verify_password,
)
from app.main import app
from app.models import User
from app.models.enums import UserRole


@pytest.fixture
def auth_client() -> Iterator[tuple[TestClient, Session]]:
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


def registration_payload(**overrides: object) -> dict[str, object]:
    suffix = uuid4().hex
    payload: dict[str, object] = {
        "email": f"user-{suffix}@example.com",
        "phone": f"+9199{suffix[:8]}",
        "password": "not-a-real-password",
        "role": "CITIZEN",
    }
    payload.update(overrides)
    return payload


def register_user(
    client: TestClient,
    **overrides: object,
) -> tuple[dict[str, object], dict[str, object]]:
    payload = registration_payload(**overrides)
    response = client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 201
    return payload, response.json()


def test_register_hashes_password_and_uses_success_envelope(
    auth_client: tuple[TestClient, Session],
) -> None:
    client, session = auth_client
    payload, body = register_user(client)

    assert body["success"] is True
    assert body["message"] == "Account created successfully."
    assert body["data"]["email"] == payload["email"]
    assert "password" not in body["data"]

    user = session.scalar(select(User).where(User.email == payload["email"]))
    assert user is not None
    assert user.password_hash != payload["password"]
    assert verify_password(str(payload["password"]), user.password_hash)


def test_duplicate_email_and_phone_return_safe_conflicts(
    auth_client: tuple[TestClient, Session],
) -> None:
    client, _ = auth_client
    payload, _ = register_user(client)

    duplicate_email = client.post(
        "/api/v1/auth/register",
        json=registration_payload(email=payload["email"]),
    )
    duplicate_phone = client.post(
        "/api/v1/auth/register",
        json=registration_payload(phone=payload["phone"]),
    )

    for response in (duplicate_email, duplicate_phone):
        body = response.json()
        assert response.status_code == 409
        assert body["success"] is False
        assert body["error"]["code"] == "CONFLICT"
        assert "email" not in body["error"]["message"].lower()
        assert "phone" not in body["error"]["message"].lower()


def test_login_and_current_user_require_a_valid_bearer_token(
    auth_client: tuple[TestClient, Session],
) -> None:
    client, _ = auth_client
    payload, _ = register_user(client)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )

    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    assert login.json()["data"]["token_type"] == "bearer"

    current_user = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert current_user.status_code == 200
    assert current_user.json()["data"]["email"] == payload["email"]

    for headers in ({}, {"Authorization": "Bearer invalid-token"}):
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "UNAUTHORIZED"


def test_invalid_or_inactive_credentials_return_the_same_safe_error(
    auth_client: tuple[TestClient, Session],
) -> None:
    client, session = auth_client
    payload, _ = register_user(client)
    inactive_email = f"inactive-{uuid4().hex}@example.com"
    session.add(
        User(
            email=inactive_email,
            password_hash=hash_password("not-a-real-password"),
            role=UserRole.CITIZEN,
            is_active=False,
        )
    )
    session.commit()

    invalid_password = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": "wrong-password"},
    )
    unknown_email = client.post(
        "/api/v1/auth/login",
        json={"email": f"missing-{uuid4().hex}@example.com", "password": "wrong-password"},
    )
    inactive_user = client.post(
        "/api/v1/auth/login",
        json={"email": inactive_email, "password": "not-a-real-password"},
    )

    for response in (invalid_password, unknown_email, inactive_user):
        assert response.status_code == 401
        assert response.json()["error"] == {
            "code": "INVALID_CREDENTIALS",
            "message": "Invalid email or password.",
            "details": {},
        }


def test_role_and_ownership_helpers_enforce_server_side_rules() -> None:
    citizen = User(
        email="citizen@example.com",
        password_hash="not-a-real-password",
        role=UserRole.CITIZEN,
    )
    citizen.id = uuid4()
    other_user_id = uuid4()
    admin = User(
        email="admin@example.com",
        password_hash="not-a-real-password",
        role=UserRole.ADMIN,
    )
    admin.id = uuid4()

    with pytest.raises(APIError) as role_error:
        asyncio.run(require_roles(UserRole.ADMIN)(citizen))
    assert role_error.value.status_code == 403

    ensure_resource_owner(citizen.id, citizen)
    ensure_resource_owner(other_user_id, admin)
    with pytest.raises(APIError) as ownership_error:
        ensure_resource_owner(other_user_id, citizen)
    assert ownership_error.value.status_code == 403


def test_validation_errors_use_the_api_error_envelope(
    auth_client: tuple[TestClient, Session],
) -> None:
    client, _ = auth_client

    response = client.post(
        "/api/v1/auth/register",
        json={"email": "invalid", "password": "sensitive-password-that-must-not-leak"},
    )

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "sensitive-password-that-must-not-leak" not in str(body["error"]["details"])


def test_openapi_exposes_the_versioned_auth_contract(
    auth_client: tuple[TestClient, Session],
) -> None:
    client, _ = auth_client
    paths = client.get("/openapi.json").json()["paths"]

    assert "/api/v1/auth/register" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
