from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    CrimeDomain,
    IncidentStatus,
    LanguageCode,
    ReportingMode,
)
from app.services.cyber_saathi_service import CyberSaathiService


def test_conversation_state_survives_multiple_validated_turns() -> None:
    client = TestClient(app)
    started = client.post(
        "/api/v1/cyber-saathi/conversations", json={"language": "EN"}
    )
    assert started.status_code == 201
    state = started.json()["data"]["state"]
    assert len(state["turns"]) == 1

    first = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={"message": "I received a suspicious message", "state": state},
    )
    assert first.status_code == 200
    state = first.json()["data"]["state"]

    second = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={"message": "I want to report this complaint", "state": state},
    )
    assert second.status_code == 200
    completed_state = second.json()["data"]["state"]
    assert len(completed_state["turns"]) == 5
    assert completed_state["incident"]["status"] == "ready_to_report"
    assert completed_state["handoff"]["target"] == "report_crime"


def test_urgent_financial_route_is_deterministic_and_confirms_amount() -> None:
    client = TestClient(app)
    state = client.post(
        "/api/v1/cyber-saathi/conversations", json={"language": "HINGLISH"}
    ).json()["data"]["state"]

    urgent = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={
            "message": "Mere bank se abhi 10 hazaar cut gaye",
            "state": state,
        },
    )
    assert urgent.status_code == 200
    state = urgent.json()["data"]["state"]
    assert state["language"] == "HINGLISH"
    assert state["incident"]["crime_domain"] == "financial_fraud"
    assert state["incident"]["urgency"] == "high"
    assert state["incident"]["status"] == "awaiting_confirmation"
    assert state["turns"][-1]["kind"] == "safety"
    assert "OTP/PIN/password" in state["turns"][-1]["content"]
    amount = state["incident"]["entities"][0]
    assert amount["normalized_value"] == "10000"
    assert amount["requires_confirmation"] is True
    assert amount["confirmed"] is False

    confirmed = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={"message": "haan", "state": state},
    )
    assert confirmed.status_code == 200
    confirmed_state = confirmed.json()["data"]["state"]
    assert confirmed_state["incident"]["status"] == "ready_to_report"
    assert confirmed_state["incident"]["entities"][0]["confirmed"] is True
    assert confirmed_state["pending_confirmation_entity_ids"] == []


def test_anonymous_handoff_has_no_reporter_identity_fields() -> None:
    started = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.EN, reporting_mode=ReportingMode.ANONYMOUS)
    ).state
    started.incident.crime_domain = CrimeDomain.CHILD_SAFETY
    response = CyberSaathiService.reply(
        started.id,
        ConversationMessageRequest(
            message="I want to report a complaint anonymously",
            state=started,
            reporting_mode=ReportingMode.ANONYMOUS,
        ),
    )
    handoff = response.state.handoff
    assert handoff is not None
    payload = handoff.model_dump(mode="json")
    assert payload["reporting_mode"] == "anonymous"
    serialized = str(payload).casefold()
    for forbidden in ("full_name", "aadhaar", "user_id", "mobile", "email"):
        assert forbidden not in serialized


def test_anonymous_financial_handoff_is_rejected() -> None:
    state = CyberSaathiService.start(ConversationCreate()).state
    financial = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="My bank account was debited today", state=state),
    ).state
    try:
        CyberSaathiService.reply(
            financial.id,
            ConversationMessageRequest(
                message="I want to report anonymously",
                state=financial,
                reporting_mode=ReportingMode.ANONYMOUS,
            ),
        )
    except Exception as error:
        assert getattr(error, "code", None) == "ANONYMOUS_REPORTING_NOT_AVAILABLE"
    else:
        raise AssertionError("Anonymous financial reporting must be rejected")


def test_hindi_and_hinglish_paths_preserve_language() -> None:
    hindi = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HI)).state
    hindi_response = CyberSaathiService.reply(
        hindi.id,
        ConversationMessageRequest(message="मेरे बैंक से अभी 5000 रुपये कट गए", state=hindi),
    )
    assert hindi_response.state.language == LanguageCode.HI
    assert hindi_response.state.incident.status == IncidentStatus.AWAITING_CONFIRMATION

    hinglish = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    hinglish_response = CyberSaathiService.reply(
        hinglish.id,
        ConversationMessageRequest(message="Mujhe suspicious link aaya hai", state=hinglish),
    )
    assert hinglish_response.state.language == LanguageCode.HINGLISH


def test_conversation_state_is_serializable_and_mismatch_is_rejected() -> None:
    client = TestClient(app)
    response = CyberSaathiService.start(ConversationCreate())
    serialized = response.state.model_dump_json()
    assert '"status":"active"' in serialized
    assert '"status":"unknown"' in serialized

    mismatch = client.post(
        f"/api/v1/cyber-saathi/conversations/{uuid4()}/messages",
        json={"message": "hello", "state": response.state.model_dump(mode="json")},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["error"]["code"] == "CONVERSATION_STATE_MISMATCH"
