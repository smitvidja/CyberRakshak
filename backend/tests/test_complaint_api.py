from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complaint, ComplaintCategory, ComplaintStatusHistory, User


def authenticated_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"citizen-{suffix}@example.com"
    password = "not-a-real-password"
    registration = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "phone": f"+9199{suffix[:8]}",
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


def complaint_payload(category_id: str, *, is_anonymous: bool) -> dict[str, object]:
    return {
        "category_id": category_id,
        "is_anonymous": is_anonymous,
        "title": "Unauthorized transfer through a fake support call",
        "description": "A caller claimed to be support staff and induced a transfer.",
        "incident_at": "2026-08-25T10:30:00Z",
        "financial_loss_amount": "1500.00",
        "priority": "HIGH",
        "location": {
            "city": "Ahmedabad",
            "district": "Ahmedabad",
            "state": "Gujarat",
        },
        "suspects": [
            {
                "alias": "Fake support caller",
                "contact_details": "+919876543210",
                "description": "Used a fraudulent support-call script.",
            }
        ],
    }


def active_category_id(session: Session) -> str:
    category = session.scalar(
        select(ComplaintCategory)
        .where(ComplaintCategory.is_active.is_(True))
        .order_by(ComplaintCategory.name)
    )
    assert category is not None
    return str(category.id)


def test_categories_are_public_and_exclude_inactive_entries(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    inactive = ComplaintCategory(
        code=f"inactive-{uuid4().hex}",
        name=f"Inactive {uuid4().hex}",
        description="Not available for public reporting.",
        is_active=False,
    )
    session.add(inactive)
    session.commit()

    response = client.get("/api/v1/complaint-categories")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data
    assert all(item["id"] != str(inactive.id) for item in data)


def test_anonymous_complaint_submission_tracks_without_identity(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    draft = client.post(
        "/api/v1/complaints/drafts",
        json=complaint_payload(active_category_id(session), is_anonymous=True),
    )

    assert draft.status_code == 201
    draft_data = draft.json()["data"]
    complaint_id = draft_data["id"]
    assert draft_data["is_anonymous"] is True

    complaint = session.get(Complaint, complaint_id)
    assert complaint is not None
    assert complaint.user_id is None
    assert complaint.status.value == "DRAFT"

    submitted = client.post(f"/api/v1/complaints/{complaint_id}/submit")
    assert submitted.status_code == 200
    submitted_data = submitted.json()["data"]
    assert submitted_data["status"] == "SUBMITTED"

    history = list(
        session.scalars(
            select(ComplaintStatusHistory).where(
                ComplaintStatusHistory.complaint_id == complaint_id
            )
        )
    )
    assert len(history) == 1
    assert history[0].status.value == "SUBMITTED"

    tracking = client.get(
        f"/api/v1/complaints/track/{submitted_data['complaint_number']}"
    )
    assert tracking.status_code == 200
    tracking_data = tracking.json()["data"]
    assert tracking_data["status"] == "SUBMITTED"
    assert tracking_data["history"][0]["status"] == "SUBMITTED"
    assert "note" not in tracking_data["history"][0]
    assert "description" not in tracking_data
    assert "user_id" not in tracking_data


def test_identified_complaints_require_authentication_and_enforce_ownership(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    category_id = active_category_id(session)

    unauthenticated = client.post(
        "/api/v1/complaints/drafts",
        json=complaint_payload(category_id, is_anonymous=False),
    )
    assert unauthenticated.status_code == 401

    owner_headers = authenticated_headers(client)
    draft = client.post(
        "/api/v1/complaints/drafts",
        json=complaint_payload(category_id, is_anonymous=False),
        headers=owner_headers,
    )
    assert draft.status_code == 201
    complaint_id = draft.json()["data"]["id"]

    submitted = client.post(
        f"/api/v1/complaints/{complaint_id}/submit",
        headers=owner_headers,
    )
    assert submitted.status_code == 200

    mine = client.get("/api/v1/complaints/my", headers=owner_headers)
    assert mine.status_code == 200
    assert complaint_id in {item["id"] for item in mine.json()["data"]}

    other_headers = authenticated_headers(client)
    for response in (
        client.get(f"/api/v1/complaints/{complaint_id}", headers=other_headers),
        client.get(
            f"/api/v1/complaints/{complaint_id}/status-history",
            headers=other_headers,
        ),
    ):
        assert response.status_code == 403


def test_reported_suspects_are_owned_and_use_nonjudgmental_contracts(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    payload = {
        "identifier_type": "UPI",
        "identifier_value": "fake-seller@upi",
        "description": "Reported in connection with a suspected online scam.",
    }
    unauthenticated = client.post("/api/v1/suspects/reports", json=payload)
    assert unauthenticated.status_code == 401

    owner_headers = authenticated_headers(client)
    created = client.post(
        "/api/v1/suspects/reports",
        headers=owner_headers,
        json=payload,
    )

    assert created.status_code == 201
    report = created.json()["data"]
    assert report["status"] == "SUBMITTED"
    assert "criminal" not in str(report).lower()

    mine = client.get("/api/v1/suspects/reports/my", headers=owner_headers)
    assert mine.status_code == 200
    assert report["id"] in {item["id"] for item in mine.json()["data"]}

    other_headers = authenticated_headers(client)
    forbidden = client.get(
        f"/api/v1/suspects/reports/{report['id']}",
        headers=other_headers,
    )
    assert forbidden.status_code == 403


def test_complaint_contracts_are_registered_in_openapi(
    api_client: tuple[TestClient, Session],
) -> None:
    client, _ = api_client
    paths = client.get("/openapi.json").json()["paths"]

    for path in (
        "/api/v1/complaint-categories",
        "/api/v1/complaints/drafts",
        "/api/v1/complaints/my",
        "/api/v1/complaints/track/{complaint_number}",
        "/api/v1/complaints/{complaint_id}",
        "/api/v1/complaints/{complaint_id}/status-history",
        "/api/v1/suspects/reports",
        "/api/v1/suspects/reports/my",
        "/api/v1/suspects/reports/{report_id}",
    ):
        assert path in paths
