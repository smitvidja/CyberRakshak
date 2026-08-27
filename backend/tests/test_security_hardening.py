"""Session 7.3 - security and privacy regression checks.

These lock in the boundaries that must not quietly regress later:

  * secrets and storage internals never appear in an API response
  * every protected endpoint rejects an absent/invalid/garbage token
  * the anonymous complaint path never attaches or exposes an identity
  * upload validation cannot be bypassed by lying about the content type

They are deliberately assertion-heavy and cheap to run, so a future change
that loosens one of these fails here rather than in production.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ComplaintCategory

# Anything that must never be serialized out to a client.
FORBIDDEN_RESPONSE_FIELDS = (
    "password",
    "password_hash",
    "storage_key",
    "otp",
    "otp_code_hash",
    "secret_key",
)


def _citizen_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"sec-citizen-{suffix}@example.com"
    password = "not-a-real-password"
    assert (
        client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "phone": f"+9165{suffix[:8]}",
                "password": password,
                "role": "CITIZEN",
            },
        ).status_code
        == 201
    )
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def _assert_no_secrets(payload: object, context: str) -> None:
    blob = str(payload).lower()
    for field in FORBIDDEN_RESPONSE_FIELDS:
        assert field not in blob, f"{context} leaked {field!r}"


def _active_category_id(session: Session) -> str:
    category = session.scalar(
        select(ComplaintCategory).where(ComplaintCategory.is_active.is_(True))
    )
    assert category is not None
    return str(category.id)


def test_registration_login_and_profile_never_return_credential_material(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    suffix = uuid4().hex
    email = f"sec-secrets-{suffix}@example.com"
    password = "not-a-real-password"

    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "phone": f"+9164{suffix[:8]}",
            "password": password,
            "role": "CITIZEN",
        },
    )
    assert registered.status_code == 201
    _assert_no_secrets(registered.json(), "register response")
    assert password not in str(registered.json())

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    assert password not in str(login.json())
    headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    _assert_no_secrets(me.json(), "auth/me response")


def test_mock_identity_never_returns_the_otp_or_full_mobile(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    requested = client.post(
        "/api/v1/auth/mock-identity/request-otp",
        json={"demo_identity_id": "99000000000001"},
    )
    assert requested.status_code == 200
    body = requested.json()["data"]
    # Only a masked mobile may come back - never the OTP, never the full number.
    assert "123456" not in str(requested.json())
    assert body["masked_mobile"].startswith("+91 *****")
    assert "9000000001" not in body["masked_mobile"]

    verified = client.post(
        "/api/v1/auth/mock-identity/verify-otp",
        json={"demo_identity_id": "99000000000001", "otp": "123456", "role": "CITIZEN"},
    )
    assert verified.status_code == 200
    _assert_no_secrets(verified.json(), "verify-otp response")


def test_evidence_responses_never_expose_the_storage_location(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    headers = _citizen_headers(client)

    draft = client.post(
        "/api/v1/complaints/drafts",
        headers=headers,
        json={
            "category_id": _active_category_id(session),
            "is_anonymous": False,
            "title": "Storage key exposure check",
            "description": "Synthetic complaint used to inspect the evidence contract.",
            "incident_at": "2026-08-20T10:30:00Z",
            "priority": "NORMAL",
            "location": {"city": "Pune", "district": "Pune", "state": "Maharashtra"},
        },
    )
    assert draft.status_code == 201

    uploaded = client.post(
        "/api/v1/evidence",
        headers=headers,
        data={"complaint_id": draft.json()["data"]["id"]},
        files={"file": ("proof.png", b"synthetic-bytes", "image/png")},
    )
    assert uploaded.status_code == 201
    payload = uploaded.json()["data"]
    _assert_no_secrets(payload, "evidence response")
    # The client gets metadata only - never a path it could use to reach the file store.
    assert set(payload).isdisjoint({"storage_key", "path", "file_path", "url"})


def test_every_protected_endpoint_rejects_missing_and_invalid_tokens(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    protected_gets = (
        "/api/v1/auth/me",
        "/api/v1/users/me/profile",
        "/api/v1/complaints/my",
        "/api/v1/suspects/reports/my",
        "/api/v1/cyber-warriors/me",
        "/api/v1/warrior-applications/my",
        "/api/v1/warrior-reports/my",
        "/api/v1/notifications",
        "/api/v1/admin/complaints",
        "/api/v1/admin/warrior-applications",
        "/api/v1/admin/audit-logs",
    )

    for path in protected_gets:
        assert client.get(path).status_code == 401, f"{path} allowed an unauthenticated read"

    for bad_token in ("not-a-jwt", "Bearer", "a.b.c", ""):
        headers = {"Authorization": f"Bearer {bad_token}"}
        for path in protected_gets:
            assert client.get(path, headers=headers).status_code == 401, (
                f"{path} accepted a malformed token {bad_token!r}"
            )


def test_a_citizen_token_cannot_reach_admin_review_endpoints(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    headers = _citizen_headers(client)

    for path in (
        "/api/v1/admin/complaints",
        "/api/v1/admin/suspect-reports",
        "/api/v1/admin/warrior-applications",
        "/api/v1/admin/audit-logs",
    ):
        response = client.get(path, headers=headers)
        assert response.status_code == 403, f"{path} was reachable by a CITIZEN"
        # A refusal must not disclose why, beyond the documented error envelope.
        assert response.json()["success"] is False
        assert "error" in response.json()


def test_anonymous_tracking_exposes_no_identity_or_internal_detail(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    category = session.scalar(
        select(ComplaintCategory).where(
            ComplaintCategory.code == "WOMEN_AND_CHILD_SAFETY",
            ComplaintCategory.is_active.is_(True),
        )
    )
    assert category is not None

    draft = client.post(
        "/api/v1/complaints/drafts",
        json={
            "category_id": str(category.id),
            "is_anonymous": True,
            "reporting_for": "SELF",
            "title": "Anonymous privacy check",
            "description": "Sensitive narrative that must never appear in public tracking.",
            "incident_at": "2026-08-18T19:00:00Z",
            "priority": "HIGH",
            "location": {"city": "Pune", "district": "Pune", "state": "Maharashtra"},
        },
    )
    assert draft.status_code == 201
    complaint_id = draft.json()["data"]["id"]
    submitted = client.post(f"/api/v1/complaints/{complaint_id}/submit")
    assert submitted.status_code == 200

    tracked = client.get(f"/api/v1/complaints/track/{submitted.json()['data']['complaint_number']}")
    assert tracked.status_code == 200
    body = tracked.json()["data"]
    for leaked in ("user_id", "description", "location", "user"):
        assert leaked not in body, f"public tracking exposed {leaked}"
    assert "sensitive narrative" not in str(tracked.json()).lower()


def test_upload_validation_cannot_be_bypassed_by_a_spoofed_content_type(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    headers = _citizen_headers(client)

    draft = client.post(
        "/api/v1/complaints/drafts",
        headers=headers,
        json={
            "category_id": _active_category_id(session),
            "is_anonymous": False,
            "title": "Upload validation check",
            "description": "Synthetic complaint used to probe upload validation.",
            "incident_at": "2026-08-20T10:30:00Z",
            "priority": "NORMAL",
            "location": {"city": "Pune", "district": "Pune", "state": "Maharashtra"},
        },
    )
    complaint_id = draft.json()["data"]["id"]

    # An executable renamed and relabelled as an image must still be refused.
    spoofed = client.post(
        "/api/v1/evidence",
        headers=headers,
        data={"complaint_id": complaint_id},
        files={"file": ("payload.exe", b"MZ\x90\x00 synthetic", "image/png")},
    )
    assert spoofed.status_code == 422, "an .exe passed upload validation"
    assert spoofed.json()["success"] is False

    # The resume endpoint enforces its own narrower allow-list.
    warrior_suffix = uuid4().hex
    warrior_email = f"sec-warrior-{warrior_suffix}@example.com"
    client.post(
        "/api/v1/auth/register",
        json={
            "email": warrior_email,
            "phone": f"+9163{warrior_suffix[:8]}",
            "password": "not-a-real-password",
            "role": "CYBER_WARRIOR",
        },
    )
    login = client.post(
        "/api/v1/auth/login",
        json={"email": warrior_email, "password": "not-a-real-password"},
    )
    warrior_headers = {"Authorization": f"Bearer {login.json()['data']['access_token']}"}
    client.post(
        "/api/v1/cyber-warriors/profile",
        headers=warrior_headers,
        json={"display_name": "Upload Probe"},
    )

    rejected_resume = client.post(
        "/api/v1/resume/upload",
        headers=warrior_headers,
        files={"file": ("resume.png", b"synthetic-bytes", "application/pdf")},
    )
    assert rejected_resume.status_code == 422, "a .png passed resume validation"


def test_error_responses_follow_the_documented_envelope(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client

    # 404, 401 and 422 must all use {success:false, error:{code,message,details}}.
    for response in (
        client.get(f"/api/v1/complaints/{uuid4()}"),
        client.get("/api/v1/auth/me"),
        client.post("/api/v1/auth/login", json={"email": "not-an-email", "password": ""}),
    ):
        body = response.json()
        assert body["success"] is False
        assert set(body["error"]) >= {"code", "message"}
        assert isinstance(body["error"]["code"], str)
        assert isinstance(body["error"]["message"], str)
