from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.core.errors import APIError
from app.schemas.cyber_saathi import (
    ConversationCreate,
    ConversationMessageRequest,
    CrimeDomain,
    GroundingStatus,
    IncidentStatus,
    LanguageCode,
    KnowledgeSearchResponse,
    ReportingMode,
)
from app.services.cyber_saathi_service import CyberSaathiService
from app.services.cyber_saathi_knowledge import KnowledgeService


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
    assert state["turns"][-1]["grounding_status"] in {
        "grounded",
        "deterministic_playbook",
    }
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


def test_guidance_turn_is_grounded_and_exposes_traceable_source_metadata() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="How can I stay safe from phishing websites and fake links?",
            state=state,
        ),
    )

    turn = response.state.turns[-1]
    assert turn.grounding_status == GroundingStatus.GROUNDED
    assert turn.sources
    assert turn.sources[0].chunk_id
    assert turn.sources[0].source_url.startswith("https://")
    assert turn.retrieval_latency_ms is not None


def test_weak_retrieval_produces_uncertainty_instead_of_invented_guidance(monkeypatch) -> None:
    monkeypatch.setattr(
        KnowledgeService,
        "search",
        lambda _request: KnowledgeSearchResponse(
            query="Please explain phishing safety",
            retrieval_latency_ms=1,
            index_version="test",
            no_result=True,
            matches=[],
            bounded_context="",
        ),
    )
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="Please explain phishing safety", state=state),
    )

    turn = response.state.turns[-1]
    assert turn.grounding_status == GroundingStatus.NO_RESULT
    assert turn.sources == []
    assert "not find sufficiently relevant official guidance" in turn.content


def test_unavailable_index_never_blocks_deterministic_urgent_safety(monkeypatch) -> None:
    def unavailable(_request):
        raise APIError(status_code=503, code="KNOWLEDGE_INDEX_UNAVAILABLE", message="test")

    monkeypatch.setattr(KnowledgeService, "search", unavailable)
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="My bank was debited right now and I lost 5000 rupees",
            state=state,
        ),
    )

    turn = response.state.turns[-1]
    assert turn.kind.value == "safety"
    assert turn.grounding_status == GroundingStatus.DETERMINISTIC_PLAYBOOK
    assert "OTP/PIN/password" in turn.content
