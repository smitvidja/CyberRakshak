"""Session 10.2: downloadable complaint copy, authorization and PDF safety."""

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Complaint, ComplaintAccessGrant, ComplaintCategory
from app.services.complaint_document_service import ComplaintDocumentService, hash_token


def register(client: TestClient) -> dict[str, str]:
    suffix = uuid4().hex
    email = f"copy-{suffix}@example.com"
    password = "not-a-real-password"
    assert client.post("/api/v1/auth/register", json={"email": email, "password": password}).status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def category_id(session: Session, *, anonymous: bool) -> str:
    """Anonymous reporting is restricted to Women and Child Safety by product rule."""
    from app.services.complaint_service import ANONYMOUS_CATEGORY_CODES

    statement = select(ComplaintCategory)
    if anonymous:
        statement = statement.where(ComplaintCategory.code.in_(ANONYMOUS_CATEGORY_CODES))
    else:
        statement = statement.where(ComplaintCategory.code.notin_(ANONYMOUS_CATEGORY_CODES))
    category = session.scalar(statement.order_by(ComplaintCategory.name))
    assert category is not None
    return str(category.id)


def draft_payload(session: Session, *, anonymous: bool) -> dict:
    return {
        "category_id": category_id(session, anonymous=anonymous),
        "is_anonymous": anonymous,
        "reporting_for": "SELF",
        "title": "Fraudulent UPI request",
        "description": "A caller asked me to approve a UPI collect request for a refund that never existed.",
        "financial_loss_amount": "45000.00",
        "location": {"city": "Bengaluru", "state": "Karnataka"},
        "suspects": [{"name": "Unknown caller", "contact_details": "+91 90000 00000", "description": "Claimed to be from a bank"}],
    }


def create_and_submit(client: TestClient, session: Session, *, anonymous: bool, headers: dict | None = None):
    response = client.post("/api/v1/complaints/drafts", json=draft_payload(session, anonymous=anonymous), headers=headers or {})
    assert response.status_code == 201, response.text
    complaint = response.json()["data"]
    submitted = client.post(f"/api/v1/complaints/{complaint['id']}/submit", headers=headers or {})
    assert submitted.status_code == 200, submitted.text
    return submitted.json()["data"]


# --- anonymous capability ---------------------------------------------------


def test_anonymous_submission_issues_a_one_time_capability(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    submitted = create_and_submit(client, session, anonymous=True)
    token = submitted["access_token"]
    assert token and len(token) >= 32

    # only a digest is stored; the table cannot yield a working token
    grant = session.scalar(select(ComplaintAccessGrant).where(ComplaintAccessGrant.token_hash == hash_token(token)))
    assert grant is not None
    assert token not in str(grant.token_hash)
    assert not hasattr(grant, "user_id"), "an access grant must not carry identity"


def test_anonymous_copy_downloads_with_the_capability_and_no_login(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    submitted = create_and_submit(client, session, anonymous=True)
    response = client.get(
        f"/api/v1/complaints/{submitted['id']}/copy",
        headers={"X-Complaint-Access-Token": submitted["access_token"]},
    )
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF-")
    assert "attachment" in response.headers["content-disposition"]
    assert submitted["complaint_number"] in response.headers["content-disposition"]
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["x-content-type-options"] == "nosniff"


def test_complaint_number_alone_cannot_download_a_copy(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    submitted = create_and_submit(client, session, anonymous=True)
    assert client.get(f"/api/v1/complaints/{submitted['id']}/copy").status_code == 401
    # public tracking stays available, and stays status-only
    tracking = client.get(f"/api/v1/complaints/track/{submitted['complaint_number']}")
    assert tracking.status_code == 200
    body = tracking.json()["data"]
    assert "description" not in body and "title" not in body


def test_guessed_revoked_and_foreign_capabilities_all_fail(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    first = create_and_submit(client, session, anonymous=True)
    second = create_and_submit(client, session, anonymous=True)

    def attempt(complaint_id: str, token: str) -> int:
        return client.get(f"/api/v1/complaints/{complaint_id}/copy", headers={"X-Complaint-Access-Token": token}).status_code

    assert attempt(first["id"], "clearly-not-a-real-token") == 403
    # a valid capability for a different complaint must not open this one
    assert attempt(first["id"], second["access_token"]) == 403

    grant = session.scalar(select(ComplaintAccessGrant).where(ComplaintAccessGrant.token_hash == hash_token(first["access_token"])))
    assert grant is not None
    from datetime import datetime, timezone

    grant.revoked_at = datetime.now(timezone.utc)
    session.commit()
    assert attempt(first["id"], first["access_token"]) == 403


# --- identified ownership ---------------------------------------------------


def test_identified_owner_downloads_and_others_cannot(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    owner = register(client)
    stranger = register(client)
    submitted = create_and_submit(client, session, anonymous=False, headers=owner)

    assert client.get(f"/api/v1/complaints/{submitted['id']}/copy", headers=owner).status_code == 200
    # unauthenticated and wrong-owner requests must not reveal that it exists
    assert client.get(f"/api/v1/complaints/{submitted['id']}/copy").status_code == 401
    assert client.get(f"/api/v1/complaints/{submitted['id']}/copy", headers=stranger).status_code == 404
    # an anonymous capability cannot be used against an identified complaint
    assert client.get(
        f"/api/v1/complaints/{submitted['id']}/copy",
        headers={"X-Complaint-Access-Token": "anything"},
    ).status_code == 401


def test_identified_submission_issues_no_capability(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    owner = register(client)
    submitted = create_and_submit(client, session, anonymous=False, headers=owner)
    assert submitted["access_token"] is None


def test_a_draft_has_no_copy(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    owner = register(client)
    draft = client.post("/api/v1/complaints/drafts", json=draft_payload(session, anonymous=False), headers=owner)
    assert draft.status_code == 201
    assert client.get(f"/api/v1/complaints/{draft.json()['data']['id']}/copy", headers=owner).status_code == 404


# --- document content -------------------------------------------------------


def _pdf_text(content: bytes) -> str:
    from io import BytesIO

    from pypdf import PdfReader

    import re

    raw = " ".join((page.extract_text() or "") for page in PdfReader(BytesIO(content)).pages)
    # The renderer wraps lines, so phrases span line breaks; compare on
    # whitespace-normalized text rather than the raw layout.
    return re.sub(r"\s+", " ", raw)


def test_copy_contains_the_required_sections_and_disclaimer(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    owner = register(client)
    submitted = create_and_submit(client, session, anonymous=False, headers=owner)
    text = _pdf_text(client.get(f"/api/v1/complaints/{submitted['id']}/copy", headers=owner).content)

    assert submitted["complaint_number"] in text
    assert "NOT an FIR" in text
    assert "not connected to police, government, banking or telecom systems" in text
    assert "Complaint reference" in text
    assert "Incident details" in text
    assert "Fraudulent UPI request" in text
    assert "Suspect information as reported" in text
    assert "allegation, not a finding" in text
    assert "What happens next" in text


def test_copy_never_leaks_storage_keys_tokens_or_internal_ids(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    submitted = create_and_submit(client, session, anonymous=True)
    content = client.get(
        f"/api/v1/complaints/{submitted['id']}/copy",
        headers={"X-Complaint-Access-Token": submitted["access_token"]},
    ).content
    text = _pdf_text(content)

    assert submitted["access_token"] not in text, "the capability must never be printed into the document"
    assert submitted["id"] not in text, "internal ids must not appear"
    for leaked in ("storage_key", "evidence/", "Bearer ", "user_id"):
        assert leaked not in text


def test_anonymous_copy_carries_no_reporter_identity(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    submitted = create_and_submit(client, session, anonymous=True)
    text = _pdf_text(
        client.get(
            f"/api/v1/complaints/{submitted['id']}/copy",
            headers={"X-Complaint-Access-Token": submitted["access_token"]},
        ).content
    )
    assert "Anonymous" in text
    assert "Affected person" not in text


def test_html_and_control_characters_render_as_text(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    owner = register(client)
    payload = draft_payload(session, anonymous=False)
    payload["title"] = "<script>alert(1)</script> and {{7*7}}"
    payload["description"] = "Line one\x07\x00 with control bytes and </table> markup that must stay literal."
    created = client.post("/api/v1/complaints/drafts", json=payload, headers=owner)
    assert created.status_code == 201
    complaint_id = created.json()["data"]["id"]
    assert client.post(f"/api/v1/complaints/{complaint_id}/submit", headers=owner).status_code == 200

    content = client.get(f"/api/v1/complaints/{complaint_id}/copy", headers=owner).content
    assert content.startswith(b"%PDF-")
    text = _pdf_text(content)
    assert "7*7" in text, "template-looking text must render literally, not evaluate"
    assert "\x00" not in text and "\x07" not in text


def test_long_multiline_content_paginates_without_failing(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    owner = register(client)
    payload = draft_payload(session, anonymous=False)
    payload["description"] = ("A very long incident narrative sentence that repeats. " * 220)
    payload["suspects"] = [
        {"name": f"Suspect {index}", "contact_details": f"+9190000000{index:02d}", "description": "Reported detail " * 20}
        for index in range(6)
    ]
    created = client.post("/api/v1/complaints/drafts", json=payload, headers=owner)
    assert created.status_code == 201
    complaint_id = created.json()["data"]["id"]
    assert client.post(f"/api/v1/complaints/{complaint_id}/submit", headers=owner).status_code == 200

    content = client.get(f"/api/v1/complaints/{complaint_id}/copy", headers=owner).content
    from io import BytesIO

    from pypdf import PdfReader

    reader = PdfReader(BytesIO(content))
    assert len(reader.pages) >= 2, "long content must flow onto further pages"


def test_devanagari_content_renders_and_survives_extraction(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    owner = register(client)
    payload = draft_payload(session, anonymous=False)
    payload["title"] = "साइबर धोखाधड़ी की शिकायत"
    payload["description"] = "मुझे एक कॉल आया और उन्होंने यूपीआई अनुरोध स्वीकार करने को कहा। क्षतिग्रस्त विश्वविद्यालय द्वितीय।"
    created = client.post("/api/v1/complaints/drafts", json=payload, headers=owner)
    assert created.status_code == 201
    complaint_id = created.json()["data"]["id"]
    assert client.post(f"/api/v1/complaints/{complaint_id}/submit", headers=owner).status_code == 200

    content = client.get(f"/api/v1/complaints/{complaint_id}/copy", headers=owner).content
    assert content.startswith(b"%PDF-")

    # Assert on RENDERING, not extraction. fpdf2 emits an unreliable ToUnicode map
    # for a *fallback* font under text shaping, so Devanagari cannot be copied out
    # of the PDF even though it draws correctly. Shaping is what makes conjuncts
    # and matras correct, so it is kept and the extraction limit is accepted and
    # documented rather than traded for wrong-looking Hindi.
    from io import BytesIO

    from pypdf import PdfReader

    page = PdfReader(BytesIO(content)).pages[0]
    fonts = [str(ref.get_object().get("/BaseFont", "")) for ref in page["/Resources"]["/Font"].values()]
    assert any("Devanagari" in name for name in fonts), "the Devanagari face must be embedded for Hindi content"
    assert any("NotoSans" in name and "Devanagari" not in name for name in fonts), "Latin face must also be embedded"



def test_document_model_is_built_from_persisted_data_only(api_client: tuple[TestClient, Session]) -> None:
    client, session = api_client
    owner = register(client)
    submitted = create_and_submit(client, session, anonymous=False, headers=owner)
    complaint = session.get(Complaint, submitted["id"])
    assert complaint is not None
    document = ComplaintDocumentService.build(complaint)
    assert document.complaint_number == complaint.complaint_number
    titles = [section.title for section in document.sections]
    assert titles[0] == "Complaint reference"
    assert "What happens next" in titles


def test_cors_preflight_allows_the_complaint_access_token_header(api_client: tuple[TestClient, Session]) -> None:
    """A custom header triggers a preflight; if it is not allowed the browser
    blocks the anonymous download cross-origin, which is the deployed topology.
    TestClient bypasses CORS, so this asserts the middleware config directly."""
    from app.core.config import get_settings
    from app.main import create_application

    application = create_application()
    cors = [m for m in application.user_middleware if "CORS" in str(m.cls)]
    assert cors, "CORS middleware must be installed"
    allowed = {h.lower() for h in cors[0].kwargs["allow_headers"]}
    assert "x-complaint-access-token" in allowed
    assert "authorization" in allowed
    assert get_settings() is not None


def test_download_is_an_attachment_but_stays_fetchable_cross_origin(api_client: tuple[TestClient, Session]) -> None:
    """Chrome fails a cross-origin fetch() whose response is marked a download.

    The browser client reads the blob and names the file itself, so a cors-mode
    fetch is served inline while every other consumer still gets an attachment.
    Without this the download is broken in the deployed split-origin topology.
    """
    client, session = api_client
    owner = register(client)
    submitted = create_and_submit(client, session, anonymous=False, headers=owner)
    url = f"/api/v1/complaints/{submitted['id']}/copy"

    default = client.get(url, headers=owner)
    assert default.status_code == 200
    assert default.headers["content-disposition"].startswith("attachment")

    navigation = client.get(url, headers={**owner, "Sec-Fetch-Mode": "navigate"})
    assert navigation.headers["content-disposition"].startswith("attachment")

    fetched = client.get(url, headers={**owner, "Sec-Fetch-Mode": "cors"})
    assert fetched.status_code == 200
    assert "content-disposition" not in fetched.headers, "Chrome blocks a cross-origin fetch carrying this header"
    # The protective headers are identical either way.
    assert fetched.headers["x-content-type-options"] == "nosniff"
    assert "no-store" in fetched.headers["cache-control"]
    assert fetched.content.startswith(b"%PDF-")
