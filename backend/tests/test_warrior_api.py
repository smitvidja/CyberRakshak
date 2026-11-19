from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CyberWarriorProfile, ResumeParsingResult, Skill, User
from app.core.security import hash_password
from app.models.enums import UserRole


def synthetic_resume_pdf() -> bytes:
    """A real, minimal PDF so uploads exercise the actual extraction pipeline."""
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=11)
    for line in (
        "Summary",
        "Cyber safety volunteer supporting community awareness work",
        "Bengaluru, Karnataka",
        "Skills",
        "Network Security, Threat Analysis",
        "Education",
        "Bachelor of Technology in Computer Science, Anna University College of Engineering, 2015 - 2019",
        "Experience",
        "Security Analyst, Aegis Cyber Solutions Pvt Ltd, 2021 - Present",
        "Reviewed phishing reports and documented findings.",
        "Certifications",
        "Certified Incident Handler - EC-Council",
    ):
        pdf.cell(0, 6, line, new_x="LMARGIN", new_y="NEXT")
    return bytes(pdf.output())


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


def upload_resume(client: TestClient, headers: dict[str, str]) -> str:
    """Upload a real resume through the parsing pipeline; returns the parsing result id."""
    uploaded = client.post("/api/v1/resume/upload", headers=headers, files={"file": ("resume.pdf", synthetic_resume_pdf(), "application/pdf")})
    assert uploaded.status_code == 201
    assert uploaded.json()["data"]["status"] == "COMPLETED"
    return uploaded.json()["data"]["id"]


def confirm_resume(client: TestClient, headers: dict[str, str]) -> None:
    """Upload a resume and confirm the reviewed details - what the application flow requires."""
    result_id = upload_resume(client, headers)
    confirmed = client.post(
        f"/api/v1/resume/parsing-results/{result_id}/confirm",
        headers=headers,
        json={
            "display_name": "Synthetic Warrior",
            "education": [{"institution": "Synthetic Institute", "degree": "B.E."}],
            "experience": [{"organization": "Synthetic Labs", "title": "Security Analyst", "is_current": True}],
        },
    )
    assert confirmed.status_code == 200


def test_resume_data_stays_untrusted_until_explicit_confirmation(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    headers = warrior_headers(client)
    profile = create_profile(client, headers)
    skill = session.scalar(select(Skill).order_by(Skill.name))
    assert skill is not None

    uploaded = client.post("/api/v1/resume/upload", headers=headers, files={"file": ("resume.pdf", synthetic_resume_pdf(), "application/pdf")})
    assert uploaded.status_code == 201
    result = uploaded.json()['data']
    assert result["status"] == "COMPLETED"
    assert result["extracted_data"]["review_required"] is True
    assert result["extracted_data"]["education"]
    assert result["extracted_data"]["experience"]
    assert result["extracted_data"]["skills"]
    assert result["extracted_data"]["certifications"]

    catalog = client.get("/api/v1/cyber-warriors/skills", headers=headers)
    assert catalog.status_code == 200
    assert any(item["id"] == str(skill.id) for item in catalog.json()["data"])

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
    replacement_upload = client.post("/api/v1/resume/upload", headers=headers, files={"file": ("updated-resume.pdf", synthetic_resume_pdf(), "application/pdf")})
    assert replacement_upload.status_code == 201
    replacement = client.post(f"/api/v1/resume/parsing-results/{replacement_upload.json()['data']['id']}/confirm", headers=headers, json={
        "display_name": "Reviewed Warrior",
        "bio": "A second reviewed resume replaces the prior profile details.",
        "skills": [{"skill_id": str(skill.id), "proficiency_level": "EXPERT", "years_of_experience": 4}],
        "education": [{"institution": "Replacement Institute", "degree": "MSc"}],
        "experience": [],
        "certifications": [],
    })
    assert replacement.status_code == 200
    assert len(replacement.json()['data']["skills"]) == 1
    assert replacement.json()['data']["skills"][0]["proficiency_level"] == "EXPERT"


def test_resume_parser_failure_is_persisted_without_profile_changes(api_client: tuple[TestClient, Session], monkeypatch) -> None:
    client, session = api_client
    headers = warrior_headers(client)
    profile = create_profile(client, headers)

    class FailingParser:
        async def parse(self, **kwargs):
            raise RuntimeError("synthetic parser failure")

    from app.services.resume import service as resume_service
    monkeypatch.setattr(resume_service, "get_resume_parser", lambda: FailingParser())
    uploaded = client.post("/api/v1/resume/upload", headers=headers, files={"file": ("resume.pdf", synthetic_resume_pdf(), "application/pdf")})

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
    confirm_resume(client, headers)

    application = client.post("/api/v1/warrior-applications", headers=headers, json={"statement": "I want to contribute safely."})
    assert application.status_code == 201
    submitted_application = client.post(f"/api/v1/warrior-applications/{application.json()['data']['id']}/submit", headers=headers)
    assert submitted_application.status_code == 200
    assert submitted_application.json()['data']["status"] == "UNDER_REVIEW"
    duplicate = client.post("/api/v1/warrior-applications", headers=headers, json={"statement": "Duplicate application."})
    assert duplicate.status_code == 409

    report = client.post("/api/v1/warrior-reports", headers=headers, json={"title": "Suspicious phishing domain", "description": "A suspicious domain was observed during permitted research.", "report_type": "PHISHING"})
    assert report.status_code == 201
    report_id = report.json()['data']['id']
    evidence = client.post("/api/v1/evidence", headers=headers, data={"warrior_report_id": report_id}, files={"file": ("capture.png", b"synthetic-image", "image/png")})
    assert evidence.status_code == 201
    submitted_report = client.post(f"/api/v1/warrior-reports/{report_id}/submit", headers=headers)
    assert submitted_report.status_code == 200
    assert submitted_report.json()['data']["status"] == "SUBMITTED"

    listed_evidence = client.get(f"/api/v1/evidence/by-warrior-report/{report_id}", headers=headers)
    assert listed_evidence.status_code == 200
    assert [item["id"] for item in listed_evidence.json()["data"]] == [evidence.json()["data"]["id"]]

    other_headers = warrior_headers(client)
    create_profile(client, other_headers)
    forbidden = client.get(f"/api/v1/evidence/by-warrior-report/{report_id}", headers=other_headers)
    assert forbidden.status_code == 403


def test_warrior_report_evidence_file_can_be_read_and_draft_can_be_deleted(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    headers = warrior_headers(client)
    create_profile(client, headers)

    report = client.post("/api/v1/warrior-reports", headers=headers, json={"title": "Suspicious link", "description": "A suspicious link was shared in a group chat.", "report_type": "PHISHING"})
    assert report.status_code == 201
    report_id = report.json()["data"]["id"]

    file_bytes = b"synthetic-evidence-bytes"
    evidence = client.post("/api/v1/evidence", headers=headers, data={"warrior_report_id": report_id}, files={"file": ("note.txt", file_bytes, "text/plain")})
    assert evidence.status_code == 201
    evidence_id = evidence.json()["data"]["id"]

    file_response = client.get(f"/api/v1/evidence/{evidence_id}/file", headers=headers)
    assert file_response.status_code == 200
    assert file_response.content == file_bytes
    assert file_response.headers["content-type"].startswith("text/plain")

    other_headers = warrior_headers(client)
    create_profile(client, other_headers)
    forbidden_file = client.get(f"/api/v1/evidence/{evidence_id}/file", headers=other_headers)
    assert forbidden_file.status_code == 403

    # A draft report (with evidence attached) can be deleted by its owner - evidence rows and
    # the underlying stored file must be cleaned up too, not just the report row.
    forbidden_delete = client.delete(f"/api/v1/warrior-reports/{report_id}", headers=other_headers)
    assert forbidden_delete.status_code == 403

    deleted = client.delete(f"/api/v1/warrior-reports/{report_id}", headers=headers)
    assert deleted.status_code == 204

    missing_after_delete = client.get(f"/api/v1/warrior-reports/{report_id}", headers=headers)
    assert missing_after_delete.status_code == 404
    evidence_gone = client.get(f"/api/v1/evidence/{evidence_id}/file", headers=headers)
    assert evidence_gone.status_code == 404

    # Deleting a submitted (non-draft) report is rejected.
    second_report = client.post("/api/v1/warrior-reports", headers=headers, json={"title": "Second report", "description": "Another synthetic report for delete-guard testing.", "report_type": "OTHER"})
    second_report_id = second_report.json()["data"]["id"]
    client.post(f"/api/v1/warrior-reports/{second_report_id}/submit", headers=headers)
    delete_submitted = client.delete(f"/api/v1/warrior-reports/{second_report_id}", headers=headers)
    assert delete_submitted.status_code == 409


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
    confirm_resume(client, warrior)
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
    for path in ("/api/v1/cyber-warriors/profile", "/api/v1/cyber-warriors/skills", "/api/v1/resume/upload", "/api/v1/resume/parsing-results/{result_id}/confirm", "/api/v1/warrior-applications/{application_id}/submit", "/api/v1/warrior-reports/{report_id}/submit", "/api/v1/admin/warrior-applications/{application_id}/status"):
        assert path in paths


def test_confirmation_accepts_multiple_reviewed_entries(api_client: tuple[TestClient, Session]) -> None:
    """The review screen offers every parsed entry, so confirmation must persist them all.

    Guards the replace-all transaction against the case that previously could not
    arise, because the UI only ever sent the first row of each section.
    """
    client, session = api_client
    headers = warrior_headers(client)
    profile = create_profile(client, headers)
    skills = session.scalars(select(Skill).order_by(Skill.name).limit(2)).all()
    assert len(skills) == 2

    uploaded = client.post("/api/v1/resume/upload", headers=headers, files={"file": ("resume.pdf", synthetic_resume_pdf(), "application/pdf")})
    assert uploaded.status_code == 201
    result_id = uploaded.json()["data"]["id"]

    confirmed = client.post(f"/api/v1/resume/parsing-results/{result_id}/confirm", headers=headers, json={
        "display_name": "Reviewed Warrior",
        "bio": "Reviewed across several roles and qualifications.",
        "skills": [
            {"skill_id": str(skills[0].id), "proficiency_level": "ADVANCED", "years_of_experience": 3},
            {"skill_id": str(skills[1].id), "proficiency_level": "BEGINNER", "years_of_experience": 1},
        ],
        "education": [
            {"institution": "First Institute", "degree": "BSc", "field_of_study": "Computer Science"},
            {"institution": "Second University", "degree": "MSc", "field_of_study": "Cyber Forensics"},
        ],
        "experience": [
            {"organization": "Alpha Security Pvt Ltd", "title": "Analyst", "description": "Older role.", "is_current": False},
            {"organization": "Beta Cyber Labs", "title": "Senior Analyst", "description": "Current role.", "is_current": True},
        ],
        "certifications": [
            {"name": "Incident Handling", "issuing_organization": "EC-Council"},
            {"name": "Network Defence", "issuing_organization": "Cisco Academy"},
        ],
    })
    assert confirmed.status_code == 200, confirmed.text
    data = confirmed.json()["data"]
    assert len(data["education"]) == 2
    assert len(data["experience"]) == 2
    assert len(data["certifications"]) == 2
    assert len(data["skills"]) == 2
    assert {item["institution"] for item in data["education"]} == {"First Institute", "Second University"}
    assert {item["is_current"] for item in data["experience"]} == {True, False}

    persisted = session.get(CyberWarriorProfile, profile["id"])
    assert persisted is not None
    session.refresh(persisted)
    assert len(persisted.education) == 2
    assert len(persisted.experience) == 2


# --- resume must be reviewed before applying ---------------------------------
#
# AGENTS.md: resume parser output is untrusted until the user reviews and confirms
# it. Only the frontend used to enforce that before an application was created, so a
# direct API call could apply with nothing reviewed.


def test_an_application_needs_a_confirmed_resume(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    headers = warrior_headers(client)
    create_profile(client, headers)

    no_resume = client.post("/api/v1/warrior-applications", headers=headers, json={})
    assert no_resume.status_code == 409
    assert no_resume.json()["error"]["code"] == "RESUME_NOT_CONFIRMED"

    # Uploaded and parsed, but not yet reviewed: still refused.
    upload_resume(client, headers)
    unreviewed = client.post("/api/v1/warrior-applications", headers=headers, json={})
    assert unreviewed.status_code == 409
    assert unreviewed.json()["error"]["code"] == "RESUME_NOT_CONFIRMED"

    confirm_resume(client, headers)
    accepted = client.post("/api/v1/warrior-applications", headers=headers, json={})
    assert accepted.status_code == 201


def test_another_warriors_confirmed_resume_does_not_count(api_client: tuple[TestClient, Session]) -> None:
    client, _ = api_client
    someone_else = warrior_headers(client)
    create_profile(client, someone_else)
    confirm_resume(client, someone_else)

    applicant = warrior_headers(client)
    create_profile(client, applicant)
    refused = client.post("/api/v1/warrior-applications", headers=applicant, json={})
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "RESUME_NOT_CONFIRMED"


def test_an_old_draft_cannot_be_submitted_without_a_confirmed_resume(api_client: tuple[TestClient, Session]) -> None:
    """A draft created before the rule existed must not slip through at submit."""
    from app.models import WarriorApplication

    client, session = api_client
    headers = warrior_headers(client)
    profile = create_profile(client, headers)
    from uuid import UUID

    # A real UUID, not the JSON string: the session keeps this object, and the
    # ownership check compares it with the profile's UUID.
    legacy = WarriorApplication(warrior_id=UUID(str(profile["id"])), application_number=f"CW-APP-LEGACY-{uuid4().hex[:8]}")
    session.add(legacy)
    session.commit()

    refused = client.post(f"/api/v1/warrior-applications/{legacy.id}/submit", headers=headers)
    assert refused.status_code == 409
    assert refused.json()["error"]["code"] == "RESUME_NOT_CONFIRMED"

    confirm_resume(client, headers)
    submitted = client.post(f"/api/v1/warrior-applications/{legacy.id}/submit", headers=headers)
    assert submitted.status_code == 200
    assert submitted.json()["data"]["status"] == "UNDER_REVIEW"
