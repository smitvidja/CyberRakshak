from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


def request_demo_otp(client: TestClient, demo_identity_id: str = "99000000000001") -> None:
    response = client.post(
        "/api/v1/auth/mock-identity/request-otp",
        json={"demo_identity_id": demo_identity_id},
    )
    assert response.status_code == 200
    payload = response.json()["data"]
    assert payload["masked_mobile"].startswith("+91 *****")
    assert "otp" not in payload
    assert "expires_at" in payload


def test_mock_identity_verification_autofills_a_profile_and_uses_otp_once(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    request_demo_otp(client)

    verified = client.post(
        "/api/v1/auth/mock-identity/verify-otp",
        json={"demo_identity_id": "99000000000001", "otp": "123456"},
    )

    assert verified.status_code == 200
    data = verified.json()["data"]
    assert data["access_token"]
    assert data["profile"]["full_name"] == "Rahul Kumar"
    assert data["profile"]["registered_mobile"] == "+91 90000 00001"
    assert data["profile"]["date_of_birth"] == "1995-08-15"
    expected_age = date.today().year - 1995 - (
        (date.today().month, date.today().day) < (8, 15)
    )
    assert data["profile"]["age"] == expected_age

    reused = client.post(
        "/api/v1/auth/mock-identity/verify-otp",
        json={"demo_identity_id": "99000000000001", "otp": "123456"},
    )
    assert reused.status_code == 409
    assert reused.json()["error"]["code"] == "OTP_ALREADY_USED"

    headers = {"Authorization": f"Bearer {data['access_token']}"}
    profile = client.get("/api/v1/users/me/profile", headers=headers)
    assert profile.status_code == 200
    assert profile.json()["data"]["full_name"] == "Rahul Kumar"
    assert profile.json()["data"]["registered_mobile"] == "+91 90000 00001"


def test_verified_profile_allows_supporting_edits_but_locks_verified_name(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    request_demo_otp(client, "99000000000002")
    verified = client.post(
        "/api/v1/auth/mock-identity/verify-otp",
        json={"demo_identity_id": "99000000000002", "otp": "654321"},
    )
    token = verified.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    profile_payload = {
        "full_name": "Ananya Shah",
        "date_of_birth": "1999-03-09",
        "gender": "Female",
        "address": "18 Sample Avenue, Vastrapur",
        "city": "Ahmedabad",
        "state": "Gujarat",
        "postal_code": "380015",
        "alternate_phone": "+91 90000 00009",
    }
    saved = client.put("/api/v1/users/me/profile", json=profile_payload, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["data"]["alternate_phone"] == "+91 90000 00009"
    assert saved.json()["data"]["date_of_birth"] == "1999-03-09"

    profile_payload["full_name"] = "Different Name"
    rejected = client.put("/api/v1/users/me/profile", json=profile_payload, headers=headers)
    assert rejected.status_code == 400
    assert rejected.json()["error"]["code"] == "PROFILE_IDENTITY_LOCKED"


def test_mock_identity_rejects_unknown_identity_and_wrong_otp(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    for invalid_id in ("123456789012", "DEMO-ID-NOT14"):
        invalid = client.post(
            "/api/v1/auth/mock-identity/request-otp",
            json={"demo_identity_id": invalid_id},
        )
        assert invalid.status_code == 422

    missing = client.post(
        "/api/v1/auth/mock-identity/request-otp",
        json={"demo_identity_id": "99999999999999"},
    )
    assert missing.status_code == 404

    request_demo_otp(client)
    wrong_otp = client.post(
        "/api/v1/auth/mock-identity/verify-otp",
        json={"demo_identity_id": "99000000000001", "otp": "000000"},
    )
    assert wrong_otp.status_code == 422
    assert wrong_otp.json()["error"]["code"] == "INVALID_OTP"
