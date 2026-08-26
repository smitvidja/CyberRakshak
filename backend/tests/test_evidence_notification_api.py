from pathlib import Path
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, Complaint, ComplaintCategory, Evidence, Notification
from app.services import evidence_service
from app.services.storage_service import LocalStorageAdapter, StorageError, get_storage_adapter


def authenticated_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"evidence-user-{suffix}@example.com"
    password = "not-a-real-password"
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "phone": f"+9198{suffix[:8]}",
            "password": password,
            "role": "CITIZEN",
        },
    )
    assert registration.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def create_complaint(
    client: TestClient,
    session: Session,
    *,
    is_anonymous: bool,
    headers: dict[str, str] | None = None,
) -> str:
    category_query = select(ComplaintCategory).where(
        ComplaintCategory.is_active.is_(True)
    )
    if is_anonymous:
        category_query = category_query.where(
            ComplaintCategory.code == "WOMEN_AND_CHILD_SAFETY"
        )
    category = session.scalar(category_query.order_by(ComplaintCategory.name))
    assert category is not None
    response = client.post(
        "/api/v1/complaints/drafts",
        headers=headers,
        json={
            "category_id": str(category.id),
            "is_anonymous": is_anonymous,
            "title": "Evidence attachment test complaint",
            "description": "This complaint is used to verify evidence handling.",
        },
    )
    assert response.status_code == 201
    return response.json()["data"]["id"]


def evidence_upload(
    client: TestClient,
    complaint_id: str,
    *,
    headers: dict[str, str] | None = None,
    filename: str = "receipt.pdf",
    mime_type: str = "application/pdf",
    content: bytes = b"%PDF-1.4 synthetic evidence",
):
    return client.post(
        "/api/v1/evidence",
        headers=headers,
        data={"complaint_id": complaint_id, "description": "Synthetic receipt."},
        files={"file": (filename, content, mime_type)},
    )


def test_identified_evidence_persists_metadata_audits_and_can_be_deleted(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    headers = authenticated_headers(client)
    complaint_id = create_complaint(
        client,
        session,
        is_anonymous=False,
        headers=headers,
    )

    uploaded = evidence_upload(client, complaint_id, headers=headers)

    assert uploaded.status_code == 201
    response_data = uploaded.json()["data"]
    assert response_data["complaint_id"] == complaint_id
    assert response_data["checksum"]
    assert response_data["file_size"] > 0
    assert "storage_key" not in response_data
    assert "file_url" not in response_data

    evidence = session.get(Evidence, response_data["id"])
    assert evidence is not None
    assert evidence.complaint_id == UUID(complaint_id)
    stored_path = Path("storage") / evidence.storage_key
    assert stored_path.exists()

    audit_log = session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == str(evidence.id),
            AuditLog.action == "evidence.uploaded",
        )
    )
    assert audit_log is not None
    assert "file_name" not in str(audit_log.details)

    notification = session.scalar(
        select(Notification).where(
            Notification.user_id == evidence.complaint.user_id,
            Notification.notification_type == "EVIDENCE_UPLOADED",
        )
    )
    assert notification is not None

    read_metadata = client.get(f"/api/v1/evidence/{evidence.id}", headers=headers)
    assert read_metadata.status_code == 200

    deleted = client.delete(f"/api/v1/evidence/{evidence.id}", headers=headers)
    assert deleted.status_code == 204
    assert session.get(Evidence, evidence.id) is None
    assert not stored_path.exists()


def test_anonymous_draft_evidence_keeps_user_identity_out_of_metadata_and_audit(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    complaint_id = create_complaint(client, session, is_anonymous=True)
    uploaded = evidence_upload(client, complaint_id)

    assert uploaded.status_code == 201
    evidence = session.get(Evidence, uploaded.json()["data"]["id"])
    assert evidence is not None
    complaint = session.get(Complaint, complaint_id)
    assert complaint is not None
    assert complaint.user_id is None

    audit_log = session.scalar(
        select(AuditLog).where(
            AuditLog.entity_id == str(evidence.id),
            AuditLog.action == "evidence.uploaded",
        )
    )
    assert audit_log is not None
    assert audit_log.user_id is None

    get_storage_adapter().delete(evidence.storage_key)


def test_evidence_rejects_unsupported_files_before_metadata_is_persisted(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    headers = authenticated_headers(client)
    complaint_id = create_complaint(
        client,
        session,
        is_anonymous=False,
        headers=headers,
    )

    rejected = evidence_upload(
        client,
        complaint_id,
        headers=headers,
        filename="payload.exe",
        mime_type="application/octet-stream",
        content=b"not executable content",
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"
    assert session.scalar(select(Evidence).where(Evidence.complaint_id == complaint_id)) is None


def test_evidence_upload_rejects_a_different_users_complaint(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    owner_headers = authenticated_headers(client)
    complaint_id = create_complaint(
        client,
        session,
        is_anonymous=False,
        headers=owner_headers,
    )

    forbidden = evidence_upload(
        client,
        complaint_id,
        headers=authenticated_headers(client),
    )

    assert forbidden.status_code == 403
    assert session.scalar(select(Evidence).where(Evidence.complaint_id == complaint_id)) is None


def test_notifications_are_current_user_only_and_can_be_marked_read(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    owner_headers = authenticated_headers(client)
    complaint_id = create_complaint(
        client,
        session,
        is_anonymous=False,
        headers=owner_headers,
    )
    submitted = client.post(
        f"/api/v1/complaints/{complaint_id}/submit",
        headers=owner_headers,
    )
    assert submitted.status_code == 200

    listed = client.get("/api/v1/notifications", headers=owner_headers)
    assert listed.status_code == 200
    notification = next(
        item
        for item in listed.json()["data"]
        if item["notification_type"] == "COMPLAINT_SUBMITTED"
    )
    assert notification["is_read"] is False

    other_headers = authenticated_headers(client)
    forbidden = client.patch(
        f"/api/v1/notifications/{notification['id']}/read",
        headers=other_headers,
    )
    assert forbidden.status_code == 403

    marked_read = client.patch(
        f"/api/v1/notifications/{notification['id']}/read",
        headers=owner_headers,
    )
    assert marked_read.status_code == 200
    assert marked_read.json()["data"]["is_read"] is True
    assert marked_read.json()["data"]["read_at"] is not None


def test_evidence_and_notification_contracts_are_registered_in_openapi(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    paths = client.get("/openapi.json").json()["paths"]

    for path in (
        "/api/v1/evidence",
        "/api/v1/evidence/{evidence_id}",
        "/api/v1/notifications",
        "/api/v1/notifications/{notification_id}/read",
    ):
        assert path in paths

class FailingStorageAdapter:
    async def store(self, *args, **kwargs):
        raise StorageError("Synthetic storage outage.")

    def delete(self, storage_key: str) -> None:
        return None


def test_evidence_rejects_oversized_files_before_metadata_is_persisted(
    api_client: tuple[TestClient, Session],
    monkeypatch,
) -> None:
    client, session = api_client
    headers = authenticated_headers(client)
    complaint_id = create_complaint(
        client,
        session,
        is_anonymous=False,
        headers=headers,
    )
    monkeypatch.setattr(
        evidence_service,
        "get_storage_adapter",
        lambda: LocalStorageAdapter("storage", max_file_size=8),
    )

    rejected = evidence_upload(
        client,
        complaint_id,
        headers=headers,
        content=b"more-than-eight-bytes",
    )

    assert rejected.status_code == 422
    assert rejected.json()["error"]["code"] == "FILE_TOO_LARGE"
    assert session.scalar(select(Evidence).where(Evidence.complaint_id == complaint_id)) is None


def test_storage_failure_does_not_create_evidence_metadata(
    api_client: tuple[TestClient, Session],
    monkeypatch,
) -> None:
    client, session = api_client
    headers = authenticated_headers(client)
    complaint_id = create_complaint(
        client,
        session,
        is_anonymous=False,
        headers=headers,
    )
    monkeypatch.setattr(
        evidence_service,
        "get_storage_adapter",
        lambda: FailingStorageAdapter(),
    )

    unavailable = evidence_upload(client, complaint_id, headers=headers)

    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    assert session.scalar(select(Evidence).where(Evidence.complaint_id == complaint_id)) is None


def test_evidence_attaches_to_an_owned_reported_suspect(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    headers = authenticated_headers(client)
    reported = client.post(
        "/api/v1/suspects/reports",
        headers=headers,
        json={
            "identifier_type": "UPI",
            "identifier_value": "synthetic-seller@upi",
            "description": "Reported after a suspected marketplace scam.",
        },
    )
    assert reported.status_code == 201

    uploaded = client.post(
        "/api/v1/evidence",
        headers=headers,
        data={
            "suspect_report_id": reported.json()["data"]["id"],
            "description": "Synthetic screenshot metadata.",
        },
        files={"file": ("reported-identifier.png", b"synthetic-image", "image/png")},
    )

    assert uploaded.status_code == 201
    evidence_data = uploaded.json()["data"]
    assert evidence_data["suspect_report_id"] == reported.json()["data"]["id"]
    assert evidence_data["complaint_id"] is None
    assert "storage_key" not in evidence_data
    evidence = session.get(Evidence, evidence_data["id"])
    assert evidence is not None
    get_storage_adapter().delete(evidence.storage_key)
