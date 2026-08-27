"""Session 7.2 - end-to-end journey coverage.

The other test modules verify individual endpoints in isolation. These tests
walk the two critical journeys the product actually ships as *continuous*
flows, in the same order the frontend drives them, asserting that state
carries correctly from one step to the next and is really persisted:

  citizen : mock identity -> profile autofill -> complaint draft -> evidence
            -> submit -> track -> my reports -> suspect report
  warrior : mock identity -> warrior profile -> resume upload -> review &
            confirm -> application -> submit -> report -> evidence -> submit
            -> my reports

They exist to catch breakage *between* steps (a field that never persists, a
status that doesn't advance, an id that doesn't carry forward) which
per-endpoint tests pass right over.
"""

from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complaint, ComplaintCategory, CyberWarriorProfile, Skill


def _active_category_id(session: Session) -> str:
    category = session.scalar(
        select(ComplaintCategory)
        .where(ComplaintCategory.is_active.is_(True))
        .order_by(ComplaintCategory.name)
    )
    assert category is not None
    return str(category.id)


def _women_and_child_category_id(session: Session) -> str:
    category = session.scalar(
        select(ComplaintCategory).where(
            ComplaintCategory.code == "WOMEN_AND_CHILD_SAFETY",
            ComplaintCategory.is_active.is_(True),
        )
    )
    assert category is not None
    return str(category.id)


def _citizen_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"journey-citizen-{suffix}@example.com"
    password = "not-a-real-password"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "phone": f"+9166{suffix[:8]}",
            "password": password,
            "role": "CITIZEN",
        },
    )
    assert registered.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def _warrior_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"journey-warrior-{suffix}@example.com"
    password = "not-a-real-password"
    registered = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "phone": f"+9167{suffix[:8]}",
            "password": password,
            "role": "CYBER_WARRIOR",
        },
    )
    assert registered.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def test_mock_identity_entry_point_issues_a_session_and_autofill_for_both_roles(
    api_client: tuple[TestClient, Session],
) -> None:
    """Both journeys start at the same synthetic eKYC entry point."""
    client, _ = api_client

    for role in ("CITIZEN", "CYBER_WARRIOR"):
        requested = client.post(
            "/api/v1/auth/mock-identity/request-otp",
            json={"demo_identity_id": "99000000000001"},
        )
        assert requested.status_code == 200
        # The OTP itself is never returned by the API - only a masked mobile.
        assert "otp" not in requested.json()["data"]
        assert requested.json()["data"]["masked_mobile"].endswith("00001")

        verified = client.post(
            "/api/v1/auth/mock-identity/verify-otp",
            json={"demo_identity_id": "99000000000001", "otp": "123456", "role": role},
        )
        assert verified.status_code == 200, role
        data = verified.json()["data"]
        assert data["access_token"]
        # Autofill data the profile-setup screen pre-populates from.
        assert data["profile"]["full_name"] == "Rahul Kumar"
        assert data["profile"]["state"] == "Delhi"

    # An admin session must never be obtainable through the mock flow.
    client.post(
        "/api/v1/auth/mock-identity/request-otp",
        json={"demo_identity_id": "99000000000001"},
    )
    rejected = client.post(
        "/api/v1/auth/mock-identity/verify-otp",
        json={"demo_identity_id": "99000000000001", "otp": "123456", "role": "ADMIN"},
    )
    assert rejected.status_code == 422


def test_new_warrior_lists_are_empty_not_missing_before_a_profile_exists(
    api_client: tuple[TestClient, Session],
) -> None:
    """The frontend calls these right after identity verification - before the
    profile step - to decide whether this is a returning applicant. Returning 404
    there made a normal first-time signup emit a spurious console error."""
    client, _ = api_client
    headers = _warrior_headers(client)

    for path in ("/api/v1/warrior-applications/my", "/api/v1/warrior-reports/my"):
        response = client.get(path, headers=headers)
        assert response.status_code == 200, f"{path} should be an empty list, not {response.status_code}"
        assert response.json()["data"] == []

    # Authorization must be unchanged: still no anonymous access, and a citizen
    # account is still refused outright.
    citizen = _citizen_headers(client)
    for path in ("/api/v1/warrior-applications/my", "/api/v1/warrior-reports/my"):
        assert client.get(path).status_code == 401
        assert client.get(path, headers=citizen).status_code == 403

    # Endpoints that genuinely need a profile must still say so.
    assert client.get("/api/v1/cyber-warriors/me", headers=headers).status_code == 404


def test_identified_citizen_journey_persists_through_submit_track_and_my_reports(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    headers = _citizen_headers(client)

    # 1. Profile - what the Aadhaar-autofilled setup screen saves.
    saved_profile = client.put(
        "/api/v1/users/me/profile",
        headers=headers,
        json={
            "full_name": "Journey Citizen",
            "date_of_birth": "1995-08-15",
            "gender": "Male",
            "address": "42 Demo Park",
            "city": "New Delhi",
            "state": "Delhi",
            "postal_code": "110024",
        },
    )
    assert saved_profile.status_code == 200
    assert saved_profile.json()["data"]["city"] == "New Delhi"

    # 2. Draft an identified complaint.
    draft = client.post(
        "/api/v1/complaints/drafts",
        headers=headers,
        json={
            "category_id": _active_category_id(session),
            "is_anonymous": False,
            "title": "Unauthorized UPI debit after a support call",
            "description": "A caller posing as bank support induced a UPI transfer.",
            "incident_at": "2026-08-20T10:30:00Z",
            "financial_loss_amount": "2500.00",
            "priority": "HIGH",
            "location": {"city": "New Delhi", "district": "New Delhi", "state": "Delhi"},
        },
    )
    assert draft.status_code == 201
    complaint_id = draft.json()["data"]["id"]
    assert draft.json()["data"]["status"] == "DRAFT"

    # 3. Attach evidence to the draft.
    evidence = client.post(
        "/api/v1/evidence",
        headers=headers,
        data={"complaint_id": complaint_id, "description": "Transaction screenshot."},
        files={"file": ("receipt.png", b"synthetic-png-bytes", "image/png")},
    )
    assert evidence.status_code == 201
    evidence_id = evidence.json()["data"]["id"]

    # 4. Submit - this is the step that mints the trackable complaint number.
    submitted = client.post(f"/api/v1/complaints/{complaint_id}/submit", headers=headers)
    assert submitted.status_code == 200
    complaint_number = submitted.json()["data"]["complaint_number"]
    assert submitted.json()["data"]["status"] == "SUBMITTED"

    # 5. Public tracking by that number shows status history and leaks no identity.
    tracked = client.get(f"/api/v1/complaints/track/{complaint_number}")
    assert tracked.status_code == 200
    tracking = tracked.json()["data"]
    assert tracking["status"] == "SUBMITTED"
    assert tracking["history"][0]["status"] == "SUBMITTED"
    assert "user_id" not in tracking
    assert "description" not in tracking

    # 6. It appears in My Reports, and the evidence is still attached.
    mine = client.get("/api/v1/complaints/my", headers=headers)
    assert mine.status_code == 200
    assert complaint_id in {item["id"] for item in mine.json()["data"]}

    detail = client.get(f"/api/v1/complaints/{complaint_id}", headers=headers)
    assert detail.status_code == 200

    stored_evidence = client.get(f"/api/v1/evidence/{evidence_id}", headers=headers)
    assert stored_evidence.status_code == 200

    # 7. A different citizen must not reach any of it.
    other = _citizen_headers(client)
    assert client.get(f"/api/v1/complaints/{complaint_id}", headers=other).status_code == 403
    assert client.get(f"/api/v1/evidence/{evidence_id}", headers=other).status_code == 403

    # 8. The same citizen can also file a standalone suspect report.
    suspect = client.post(
        "/api/v1/suspects/reports",
        headers=headers,
        json={
            "identifier_type": "UPI",
            "identifier_value": f"journey-suspect-{uuid4().hex[:8]}@upi",
            "description": "Reported in connection with the incident above.",
        },
    )
    assert suspect.status_code == 201
    assert suspect.json()["data"]["status"] == "SUBMITTED"
    suspect_id = suspect.json()["data"]["id"]
    listed = client.get("/api/v1/suspects/reports/my", headers=headers)
    assert suspect_id in {item["id"] for item in listed.json()["data"]}

    persisted = session.get(Complaint, complaint_id)
    assert persisted is not None
    assert persisted.user_id is not None
    assert persisted.complaint_number == complaint_number


def test_anonymous_citizen_journey_completes_without_any_identity(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client

    draft = client.post(
        "/api/v1/complaints/drafts",
        json={
            "category_id": _women_and_child_category_id(session),
            "is_anonymous": True,
            "reporting_for": "SELF",
            "title": "Repeated threatening messages on a social platform",
            "description": "An account has been sending threatening messages daily.",
            "incident_at": "2026-08-18T19:00:00Z",
            "priority": "HIGH",
            "location": {"city": "Pune", "district": "Pune", "state": "Maharashtra"},
        },
    )
    assert draft.status_code == 201
    complaint_id = draft.json()["data"]["id"]

    # Evidence attaches to an anonymous draft with no session at all.
    evidence = client.post(
        "/api/v1/evidence",
        data={"complaint_id": complaint_id},
        files={"file": ("chat.txt", b"synthetic chat export", "text/plain")},
    )
    assert evidence.status_code == 201

    submitted = client.post(f"/api/v1/complaints/{complaint_id}/submit")
    assert submitted.status_code == 200
    complaint_number = submitted.json()["data"]["complaint_number"]

    tracked = client.get(f"/api/v1/complaints/track/{complaint_number}")
    assert tracked.status_code == 200
    assert tracked.json()["data"]["status"] == "SUBMITTED"

    # The whole point of the anonymous path: no user is ever attached.
    persisted = session.get(Complaint, complaint_id)
    assert persisted is not None
    assert persisted.user_id is None
    assert persisted.is_anonymous is True


def test_cyber_warrior_journey_from_resume_review_to_a_tracked_report(
    api_client: tuple[TestClient, Session],
) -> None:
    client, session = api_client
    headers = _warrior_headers(client)

    # 1. Warrior profile.
    profile = client.post(
        "/api/v1/cyber-warriors/profile",
        headers=headers,
        json={"display_name": "Journey Warrior", "location": "Pune, Maharashtra"},
    )
    assert profile.status_code == 201
    profile_id = profile.json()["data"]["id"]

    # 2. Resume upload - parsed data must arrive flagged as needing review, and
    #    must NOT have written anything to the profile yet.
    uploaded = client.post(
        "/api/v1/resume/upload",
        headers=headers,
        files={"file": ("journey-resume.pdf", b"%PDF-1.4 synthetic resume", "application/pdf")},
    )
    assert uploaded.status_code == 201
    parsed = uploaded.json()["data"]
    assert parsed["status"] == "COMPLETED"
    assert parsed["extracted_data"]["review_required"] is True

    before_confirm = session.get(CyberWarriorProfile, profile_id)
    assert before_confirm is not None
    session.refresh(before_confirm)
    assert before_confirm.skills == []

    # 3. The user reviews and explicitly confirms - only now does it persist.
    skill = session.scalar(select(Skill).order_by(Skill.name))
    assert skill is not None
    confirmed = client.post(
        f"/api/v1/resume/parsing-results/{parsed['id']}/confirm",
        headers=headers,
        json={
            "display_name": "Journey Warrior",
            "bio": "Reviewed and confirmed by the applicant.",
            "location": "Pune, Maharashtra",
            "linkedin_url": None,
            "github_url": None,
            "skills": [
                {
                    "skill_id": str(skill.id),
                    "proficiency_level": "INTERMEDIATE",
                    "years_of_experience": 3,
                }
            ],
            "education": [{"institution": "Synthetic Institute", "degree": "B.E."}],
            "experience": [
                {
                    "organization": "Synthetic Labs",
                    "title": "Security Analyst",
                    "is_current": True,
                }
            ],
            "certifications": [{"name": "Synthetic Cert", "issuing_organization": "Synthetic Body"}],
        },
    )
    assert confirmed.status_code == 200
    assert len(confirmed.json()["data"]["skills"]) == 1

    # 4. Application - created, then submitted for review.
    application = client.post(
        "/api/v1/warrior-applications",
        headers=headers,
        json={"statement": "I would like to volunteer as a Cyber Warrior."},
    )
    assert application.status_code == 201
    application_id = application.json()["data"]["id"]
    assert application.json()["data"]["status"] == "DRAFT"

    submitted_application = client.post(
        f"/api/v1/warrior-applications/{application_id}/submit", headers=headers
    )
    assert submitted_application.status_code == 200
    assert submitted_application.json()["data"]["status"] == "UNDER_REVIEW"
    assert submitted_application.json()["data"]["submitted_at"] is not None

    # A second active application must be refused - this is what makes the
    # frontend treat the identity as a returning user on next login.
    duplicate = client.post("/api/v1/warrior-applications", headers=headers, json={})
    assert duplicate.status_code == 409

    listed_applications = client.get("/api/v1/warrior-applications/my", headers=headers)
    assert listed_applications.status_code == 200
    assert application_id in {item["id"] for item in listed_applications.json()["data"]}

    # 5. Report a cybercrime: draft -> evidence -> submit.
    report = client.post(
        "/api/v1/warrior-reports",
        headers=headers,
        json={
            "title": "Fake bank login page harvesting credentials",
            "description": "A lookalike domain is serving a cloned bank login form.",
            "report_type": "PHISHING",
        },
    )
    assert report.status_code == 201
    report_id = report.json()["data"]["id"]
    assert report.json()["data"]["status"] == "DRAFT"

    report_evidence = client.post(
        "/api/v1/evidence",
        headers=headers,
        data={"warrior_report_id": report_id, "description": "Screenshot of the cloned page."},
        files={"file": ("phishing.png", b"synthetic-screenshot-bytes", "image/png")},
    )
    assert report_evidence.status_code == 201
    report_evidence_id = report_evidence.json()["data"]["id"]

    submitted_report = client.post(f"/api/v1/warrior-reports/{report_id}/submit", headers=headers)
    assert submitted_report.status_code == 200
    assert submitted_report.json()["data"]["status"] == "SUBMITTED"
    assert submitted_report.json()["data"]["submitted_at"] is not None

    # 6. It shows up in My Reports / tracking with its evidence intact.
    my_reports = client.get("/api/v1/warrior-reports/my", headers=headers)
    assert my_reports.status_code == 200
    assert report_id in {item["id"] for item in my_reports.json()["data"]}

    attached = client.get(f"/api/v1/evidence/by-warrior-report/{report_id}", headers=headers)
    assert attached.status_code == 200
    assert report_evidence_id in {item["id"] for item in attached.json()["data"]}

    downloadable = client.get(f"/api/v1/evidence/{report_evidence_id}/file", headers=headers)
    assert downloadable.status_code == 200
    assert downloadable.content == b"synthetic-screenshot-bytes"

    # 7. A submitted report is no longer editable or deletable.
    assert client.delete(f"/api/v1/warrior-reports/{report_id}", headers=headers).status_code == 409
    assert (
        client.patch(
            f"/api/v1/warrior-reports/{report_id}",
            headers=headers,
            json={"title": "Changed after submission"},
        ).status_code
        == 409
    )

    # 8. Another warrior must not reach this warrior's report or evidence.
    other = _warrior_headers(client)
    client.post(
        "/api/v1/cyber-warriors/profile",
        headers=other,
        json={"display_name": "Other Warrior"},
    )
    assert client.get(f"/api/v1/warrior-reports/{report_id}", headers=other).status_code == 403
    assert (
        client.get(f"/api/v1/evidence/{report_evidence_id}/file", headers=other).status_code == 403
    )
    assert (
        client.get(f"/api/v1/evidence/by-warrior-report/{report_id}", headers=other).status_code
        == 403
    )

    # 9. Submitting/creating any of this without a session must fail outright.
    assert client.get("/api/v1/warrior-reports/my").status_code == 401
    assert client.post("/api/v1/warrior-applications", json={}).status_code == 401
