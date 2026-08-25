from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CyberWarriorProfile, ResumeParsingResult, Skill, User
from app.core.security import hash_password
from app.models.enums import UserRole


def warrior_headers(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"warrior-{suffix}@example.com"
    password = "not-a-real-password"
    assert client.post("/api/v1/auth/register", json={"email": email, "phone": f"+9177{suffix[:8]}", "password": password, "role": "CYBER_WARRIOR"}).status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def create_profile(client: TestClient, headers: dict[str, str]) -> dict[str, object]:
    response = client.post("/api/v1/cyber-warriors/profile", headers=headers, json={"display_name": "Synthetic Warrior", "bio": "Synthetic profile for backend verification."})
    assert response.status_code == 201
    return response.json()['data']


def test_resume_data_stays_untrusted_until_explicit_confirmation(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    headers = warrior_headers(client)
    profile = create_profile(client, headers)
    skill = session.scalar(select(Skill).order_by(Skill.name))
    assert skill is not None

    uploaded = client.post("/api/v1/resume/upload", headers=headers, files={"file": ("resume.pdf", b"%PDF-1.4 synthetic", "application/pdf")})
    assert uploaded.status_code == 201
    result = uploaded.json()['data']
    assert result["status"] == "COMPLETED"
    assert result["extracted_data"]["review_required"] is True

    persisted_profile = session.get(CyberWarriorProfile, profile['id'])
    assert persisted_profile is not None
    assert persisted_profile.display_name == "Synthetic Warrior"
    assert persisted_profile.skills == []

    confirmed = client.post(f"/api/v1/resume/parsing-results/{result['id']}/confirm", headers=headers, json={
        "display_name": "Reviewed Warrior",
        "bio": "Reviewed data deliberately supplied by the user.",
        "skills": [{"skill_id": str(skill.id), "proficiency_level": "ADVANCED", "years_of_experience": 3}],
        "education": [{"institution": "Synthetic Institute", "degree": "BSc"}],
        "experience": [],
        "certifications": [],
    })
    assert confirmed.status_code == 200
    assert confirmed.json()['data']["display_name"] == "Reviewed Warrior"
    assert len(confirmed.json()['data']["skills"]) == 1

    parsing_row = session.get(ResumeParsingResult, result['id'])
    assert parsing_row is not None
    assert parsing_row.confirmed_at is not None


def test_resume_parser_failure_is_persisted_without_profile_changes(api_client: tuple[TestClient, Session], monkeypatch) -> None:
    client, session = api_client
    headers = warrior_headers(client)
    profile = create_profile(client, headers)

    class FailingParser:
        async def parse(self, **kwargs):
            raise RuntimeError("synthetic parser failure")

    from app.services import resume_service
    monkeypatch.setattr(resume_service, "get_resume_parser", lambda: FailingParser())
    uploaded = client.post("/api/v1/resume/upload", headers=headers, files={"file": ("resume.pdf", b"%PDF-1.4 synthetic", "application/pdf")})

    assert uploaded.status_code == 201
    assert uploaded.json()['data']["status"] == "FAILED"
    assert uploaded.json()['data']["error_message"] == "Resume processing could not be completed."
    persisted_profile = session.get(CyberWarriorProfile, profile['id'])
    assert persisted_profile is not None
    assert persisted_profile.display_name == "Synthetic Warrior"


def test_application_and_warrior_report_submit_with_owned_evidence(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    headers = warrior_headers(client)
    create_profile(client, headers)

    application = client.post("/api/v1/warrior-applications", headers=headers, json={"statement": "I want to contribute safely."})
    assert application.status_code == 201
    submitted_application = client.post(f"/api/v1/warrior-applications/{application.json()['data']['id']}/submit", headers=headers)
    assert submitted_application.status_code == 200
    assert submitted_application.json()['data']["status"] == "SUBMITTED"

    report = client.post("/api/v1/warrior-reports", headers=headers, json={"title": "Suspicious phishing domain", "description": "A suspicious domain was observed during permitted research.", "report_type": "PHISHING"})
    assert report.status_code == 201
    report_id = report.json()['data']['id']
    evidence = client.post("/api/v1/evidence", headers=headers, data={"warrior_report_id": report_id}, files={"file": ("capture.png", b"synthetic-image", "image/png")})
    assert evidence.status_code == 201
    submitted_report = client.post(f"/api/v1/warrior-reports/{report_id}/submit", headers=headers)
    assert submitted_report.status_code == 200
    assert submitted_report.json()['data']["status"] == "SUBMITTED"


def admin_headers(client: TestClient, session: Session) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"admin-{suffix}@example.com"
    password = "not-a-real-password"
    session.add(User(email=email, password_hash=hash_password(password), role=UserRole.ADMIN))
    session.commit()
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def test_admin_review_is_server_side_role_protected(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    warrior = warrior_headers(client)
    create_profile(client, warrior)
    application = client.post("/api/v1/warrior-applications", headers=warrior, json={})
    application_id = application.json()['data']['id']

    assert client.get("/api/v1/admin/warrior-applications", headers=warrior).status_code == 403

    admin = admin_headers(client, session)
    reviewed = client.patch(f"/api/v1/admin/warrior-applications/{application_id}/status", headers=admin, json={"status": "APPROVED", "review_note": "Synthetic review outcome."})
    assert reviewed.status_code == 200
    assert reviewed.json()['data']["status"] == "APPROVED"
    assert client.get("/api/v1/admin/audit-logs", headers=admin).status_code == 200


def test_warrior_contracts_are_registered_in_openapi(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    paths = client.get("/openapi.json").json()["paths"]
    for path in ("/api/v1/cyber-warriors/profile", "/api/v1/resume/upload", "/api/v1/resume/parsing-results/{result_id}/confirm", "/api/v1/warrior-applications/{application_id}/submit", "/api/v1/warrior-reports/{report_id}/submit", "/api/v1/admin/warrior-applications/{application_id}/status"):
        assert path in paths
