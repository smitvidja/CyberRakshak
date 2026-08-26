from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.test_auth_api import register_user


def test_authenticated_citizen_can_create_and_read_profile(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    payload, _ = register_user(client)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": payload["email"], "password": payload["password"]},
    )
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {
        "full_name": "Prototype Citizen",
        "city": "Pune",
        "state": "Maharashtra",
    }

    saved = client.put("/api/v1/users/me/profile", json=profile_payload, headers=headers)

    assert saved.status_code == 200
    assert saved.json()["success"] is True
    assert saved.json()["data"]["full_name"] == "Prototype Citizen"

    fetched = client.get("/api/v1/users/me/profile", headers=headers)

    assert fetched.status_code == 200
    assert fetched.json()["data"]["city"] == "Pune"


def test_profile_requires_authentication(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    response = client.get("/api/v1/users/me/profile")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "UNAUTHORIZED"
