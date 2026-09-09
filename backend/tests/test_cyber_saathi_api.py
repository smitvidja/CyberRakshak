from datetime import date, timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.errors import APIError
from app.schemas.cyber_saathi import (
    AttachmentAnalysis,
    ConversationCreate,
    ConversationMessageRequest,
    CrimeDomain,
    GroundingStatus,
    IncidentStatus,
    LanguageCode,
    LLMGenerationResult,
    LLMProvider,
    LLMStructuredResponse,
    KnowledgeSearchResponse,
    ReportingMode,
)
from app.services import cyber_saathi_service as service_module
from app.services.cyber_saathi_service import CyberSaathiService
from app.services.cyber_saathi_knowledge import KnowledgeService
from app.services.cyber_saathi_understanding import UnderstandingEngine


def prepare_report_draft(state):
    return CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Prepare report draft",
            state=state,
            prepare_report_draft=True,
        ),
    ).state


@pytest.mark.parametrize(
    ("message", "language", "target", "route", "implementation_status"),
    [
        ("How can I become a cyber warrior volunteer?", LanguageCode.EN, "cyber_warrior", "/cyber-warrior", "available"),
        ("ऑनलाइन कैसे सुरक्षित रहें?", LanguageCode.HI, "learning_resources", "/resources", "available"),
        ("Mujhe check UPI ID fraudster@ybl karna hai.", LanguageCode.HINGLISH, "search_suspect_reports", "/suspects/search", "planned"),
        ("Show cyber risk in my city on Secure India", LanguageCode.EN, "secure_india", "/secure-india", "preview"),
        ("Meri complaint ka status kya hai?", LanguageCode.HINGLISH, "track_complaint", "/complaints/track", "available"),
    ],
)
def test_non_report_workflows_return_typed_handoffs(
    message: str,
    language: LanguageCode,
    target: str,
    route: str,
    implementation_status: str,
) -> None:
    state = CyberSaathiService.start(ConversationCreate(language=language)).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message=message, state=state),
    )

    assert response.state.handoff is not None
    assert response.state.handoff.target.value == target
    assert response.state.handoff.route == route
    assert response.state.handoff.implementation_status.value == implementation_status
    assert response.state.turns[-1].kind.value == "handoff"
    if target == "search_suspect_reports":
        answer = response.state.turns[-1].content.casefold()
        assert "live lookup" in answer
        assert "criminal" in answer
    if target == "track_complaint":
        assert "live access" in response.state.turns[-1].content.casefold()


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
    assert completed_state["incident"]["status"] == "awaiting_user_input"
    assert completed_state["handoff"] is None


def test_prepare_report_draft_is_redacted_server_persistent() -> None:
    client = TestClient(app)
    started = client.post(
        "/api/v1/cyber-saathi/conversations", json={"language": "HINGLISH"}
    )
    assert started.status_code == 201
    state = started.json()["data"]["state"]
    incident = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={
            "message": "Mere bank account se Rs 5000 chale gaye",
            "state": state,
        },
    )
    assert incident.status_code == 200
    state = incident.json()["data"]["state"]
    confirmed = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={"message": "haan", "state": state},
    )
    assert confirmed.status_code == 200
    state = confirmed.json()["data"]["state"]
    state["storage_consent"] = True
    prepared = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={
            "message": "Prepare report draft",
            "state": state,
            "prepare_report_draft": True,
        },
    )
    assert prepared.status_code == 200
    prepared_state = prepared.json()["data"]["state"]
    assert prepared_state["storage_consent"] is True
    assert prepared_state["incidents"][0]["report_preparation"]["draft_prepared"] is True
    assert prepared_state["handoff"] is not None

    resumed = client.get(
        f"/api/v1/cyber-saathi/conversations/{state['id']}"
    )
    assert resumed.status_code == 200
    resumed_state = resumed.json()["data"]["state"]
    assert resumed_state["incidents"][0]["report_preparation"]["draft_prepared"] is True
    assert resumed_state["handoff"]["prefill"]["financial_loss_amount"] == "5000"


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
    assert confirmed_state["incident"]["status"] == "awaiting_user_input"
    assert confirmed_state["language"] == "HINGLISH"
    assert confirmed_state["incident"]["entities"][0]["confirmed"] is True
    assert confirmed_state["pending_confirmation_entity_ids"] == []
    assert confirmed_state["handoff"] is None


def test_anonymous_handoff_has_no_reporter_identity_fields() -> None:
    started = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.EN, reporting_mode=ReportingMode.ANONYMOUS)
    ).state
    response = CyberSaathiService.reply(
        started.id,
        ConversationMessageRequest(
            message="A morphed image of my child is being shared on Instagram today and I kept screenshots",
            state=started,
        ),
    )
    state = CyberSaathiService.reply(
        response.state.id,
        ConversationMessageRequest(message="yes", state=response.state),
    ).state
    state = CyberSaathiService.add_attachment(
        state.id,
        state,
        AttachmentAnalysis(
            file_name="proof.png",
            mime_type="image/png",
            file_size=20,
            checksum="a" * 64,
            media_summary="PNG image",
        ),
    ).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="I want to report anonymously",
            state=state,
            reporting_mode=ReportingMode.ANONYMOUS,
        ),
    )
    assert response.state.handoff is None
    prepared = prepare_report_draft(response.state)
    handoff = prepared.handoff
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


def test_weak_retrieval_uses_guarded_llm_without_claiming_a_grounded_source(
    monkeypatch,
) -> None:
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

    class NoKnowledgeGateway:
        def generate(self, **kwargs) -> LLMGenerationResult:
            assert kwargs["knowledge_context"] == ""
            assert kwargs["source_ids"] == []
            assert "Do not reopen the link" in kwargs["deterministic_playbook"]
            return LLMGenerationResult(
                response=LLMStructuredResponse(
                    answer=(
                        "Use the official service from a trusted device and preserve "
                        "the suspicious message."
                    ),
                    confidence=0.7,
                    urgency="medium",
                    suggested_actions=[],
                    clarification_needed=False,
                    workflow_action="none",
                    sources=[],
                    safety_flags=[],
                ),
                provider=LLMProvider.GEMINI,
                model="gemini-test",
                latency_ms=9,
            )

    monkeypatch.setattr(
        service_module, "get_llm_gateway", lambda: NoKnowledgeGateway()
    )
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="Please explain phishing safety", state=state),
    )

    turn = response.state.turns[-1]
    assert turn.grounding_status == GroundingStatus.NO_RESULT
    assert turn.sources == []
    assert turn.llm_provider == LLMProvider.GEMINI
    assert turn.llm_model == "gemini-test"
    assert "trusted device" in turn.content
    assert "llm_without_retrieved_source" in turn.safety_flags


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


def test_amount_correction_advances_without_repeating_the_safety_template() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="OLX buyer payment ke naam par 35 hazar le gaya", state=state
        ),
    ).state

    corrected = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="45 hazar", state=state),
    ).state

    assert corrected.incident.entities[0].normalized_value == "45000"
    assert corrected.turns[-1].kind.value == "confirmation"
    assert "corrected detail" in corrected.turns[-1].content
    assert "OTP/PIN/password" not in corrected.turns[-1].content


def test_reporting_mode_selection_waits_for_explicit_report_draft() -> None:
    state = CyberSaathiService.start(ConversationCreate()).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="My bank account was debited today by Rs 5000", state=state
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="yes", state=state),
    ).state

    selected = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="I want to report with my identity",
            state=state,
            reporting_mode=ReportingMode.IDENTIFIED,
        ),
    ).state

    assert selected.reporting_mode == ReportingMode.IDENTIFIED
    assert selected.handoff is None
    assert "Identified reporting selected" in selected.turns[-1].content
    assert "OTP/PIN/password" not in selected.turns[-1].content
    prepared = prepare_report_draft(selected)
    assert prepared.handoff is not None
    assert prepared.handoff.reporting_mode == ReportingMode.IDENTIFIED
    assert prepared.handoff.target.value == "report_crime"
    assert prepared.storage_consent is True
    assert prepared.incidents[0].report_preparation.draft_prepared is True


def test_reporting_mode_keeps_optional_report_fields_editable() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="Mere 5 hazaar paise chale gaye", state=state),
    ).state
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=state)
    ).state
    assert state.incidents[0].report_preparation.ready_for_review is False

    selected = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="identity se report karna hai",
            state=state,
            reporting_mode=ReportingMode.IDENTIFIED,
        ),
    ).state

    assert selected.handoff is None
    prepared = prepare_report_draft(selected)
    assert prepared.handoff is not None
    assert prepared.handoff.reporting_mode == ReportingMode.IDENTIFIED


def test_kyc_link_uses_phishing_guidance_and_never_a_child_specific_source() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="KYC update nahi kiya toh account block bola. Maine link open kar diya, ab safe hu?",
            state=state,
        ),
    )

    assert response.state.incident.crime_domain == CrimeDomain.PHISHING_SCAM
    turn = response.state.turns[-1]
    assert turn.sources
    assert all("kids" not in source.source_id for source in turn.sources)
    assert all("mahila" not in source.source_id for source in turn.sources)
    assert "?" in turn.content


def test_ecommerce_non_delivery_has_its_own_domain_and_official_consumer_source() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    response = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Maine online t-shirt mangwayi, payment kiya, 10 din baad bhi delivery nahi aur website nahi chal rahi",
            state=state,
        ),
    )

    assert response.state.incident.crime_domain == CrimeDomain.ECOMMERCE_FRAUD
    turn = response.state.turns[-1]
    assert turn.kind.value == "message"
    assert turn.sources[0].source_id == "nch_ecommerce_grievance"
    assert "OTP/PIN/password" not in turn.content
    assert "?" in turn.content


def test_multiple_incidents_are_queued_and_finished_one_at_a_time() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere bank account mein unauthorized transaction hua aaj", state=state
        ),
    ).state
    first_summary = state.incident.summary

    queued = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere papa ko fake officer ne digital arrest bolkar video call par rakha",
            state=state,
        ),
    ).state

    assert len(queued.incidents) == 2
    assert [item.queue_status.value for item in queued.incidents] == ["active", "queued"]
    assert queued.incident.summary == first_summary
    assert "incident #2" in queued.turns[-1].content.casefold()

    ready = CyberSaathiService.reply(
        queued.id,
        ConversationMessageRequest(message="ye sab kar liya ab kya karu?", state=queued),
    ).state
    assert ready.incident.status == IncidentStatus.AWAITING_CONFIRMATION

    activated = CyberSaathiService.reply(
        ready.id,
        ConversationMessageRequest(message="next incident", state=ready),
    ).state
    assert activated.incident.crime_domain == CrimeDomain.FINANCIAL_FRAUD
    assert [item.queue_status.value for item in activated.incidents] == ["active", "queued"]
    assert "ready nahi" in activated.turns[-1].content.casefold()


def test_bank_contact_followup_returns_only_the_next_missing_step() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere bank se aaj unauthorized transaction hua", state=state
        ),
    ).state

    progressed = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Maine bank ko call kar diya, ab kya karu?", state=state
        ),
    ).state

    assert "bank_contacted" in progressed.incidents[0].completed_actions
    assert "reference number" in progressed.turns[-1].content
    assert "OTP/PIN/password" not in progressed.turns[-1].content


def test_what_next_followup_uses_the_active_domain_not_financial_copy() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="KYC update ka link open kar diya, ab safe hu?", state=state
        ),
    ).state

    progressed = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="ab kya karu?", state=state),
    ).state

    assert progressed.incident.crime_domain == CrimeDomain.PHISHING_SCAM
    assert "password" in progressed.turns[-1].content
    assert "OTP" in progressed.turns[-1].content
    assert "bank/provider" not in progressed.turns[-1].content
    assert "1930" not in progressed.turns[-1].content


def test_completed_ecommerce_steps_keep_ecommerce_report_category() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Online order deliver nahi hua aur seller refund nahi de raha",
            state=state,
        ),
    ).state

    completed = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="ye sab kar liya ab kya karu?", state=state),
    ).state

    assert completed.incident.status == IncidentStatus.AWAITING_USER_INPUT
    assert completed.handoff is None
    prepared = prepare_report_draft(completed)
    assert prepared.handoff is not None
    assert prepared.handoff.prefill.crime_domain == CrimeDomain.ECOMMERCE_FRAUD


def test_repeated_queued_incident_is_not_given_a_new_sequence_number() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere bank account se Rs 9000 unauthorized nikal gaye", state=state
        ),
    ).state
    repeated_incident = "Maine online t-shirt mangwayi thi, delivery nahi hui aur website band hai"
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message=repeated_incident, state=state),
    ).state

    repeated = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message=repeated_incident, state=state),
    ).state

    assert len(repeated.incidents) == 2
    assert "incident #2" in repeated.turns[-1].content.casefold()
    assert "incident #3" not in repeated.turns[-1].content.casefold()
    assert repeated.turns[-1].purpose.value == "duplicate_incident"


def test_blocked_followup_offers_alternative_and_repeated_failures_escalate() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere bank account se abhi Rs 5000 unauthorized nikal gaye", state=state
        ),
    ).state
    for _ in range(5):
        state = CyberSaathiService.reply(
            state.id,
            ConversationMessageRequest(
                message="Mera screenshot nahi ho payega, ab kya karu?", state=state
            ),
        ).state

    assert state.incident.urgency.value == "critical"
    assert state.incidents[0].blocked_actions["screenshot"] == 5
    assert "1930" in state.turns[-1].content
    assert "transaction statement" in state.turns[-1].content.casefold()


def test_report_packet_infers_self_and_reaches_the_handoff_contract() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere HDFC bank account se aaj Rs 5000 unauthorized nikal gaye", state=state
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="haan", state=state),
    ).state
    state = CyberSaathiService.add_attachment(
        state.id,
        state,
        AttachmentAnalysis(
            file_name="payment-proof.png",
            mime_type="image/png",
            file_size=20,
            checksum="b" * 64,
            media_summary="PNG image",
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="identity ke saath report karna hai",
            state=state,
            reporting_mode=ReportingMode.IDENTIFIED,
        ),
    ).state

    preparation = state.incidents[0].report_preparation
    assert preparation.reporting_for == "SELF"
    assert preparation.ready_for_review is True
    assert state.handoff is None
    state = prepare_report_draft(state)
    assert state.handoff is not None
    assert state.handoff.prefill.reporting_for == "SELF"


def test_bank_followup_cross_checks_retrieval_and_advances_one_concrete_action() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="My HDFC bank account lost Rs 5000 today through UPI", state=state
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="yes", state=state)
    ).state

    followed_up = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Bank contacted: yes. What do I need to file the report?", state=state
        ),
    ).state

    reply = followed_up.turns[-1]
    assert "1. Your bank contact is recorded." in reply.content
    assert "2. Ask the official bank channel to block outgoing transactions" in reply.content
    assert "3. Did the bank give a reference number" in reply.content
    assert "CERT" not in reply.content
    assert "1930" not in reply.content
    assert reply.llm_provider is None
    assert reply.grounding_status in {
        GroundingStatus.GROUNDED,
        GroundingStatus.DETERMINISTIC_PLAYBOOK,
    }
    assert followed_up.last_turn_purpose.value == "next_step"
    assert "bank_contacted" in followed_up.incidents[0].completed_actions


def test_ready_financial_packet_exposes_editable_report_prefill_without_mode_round_trip() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="My HDFC bank account lost Rs 5000 today through UPI", state=state
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="yes", state=state)
    ).state
    state = CyberSaathiService.add_attachment(
        state.id,
        state,
        AttachmentAnalysis(
            file_name="payment-proof.png",
            mime_type="image/png",
            file_size=20,
            checksum="c" * 64,
            media_summary="PNG image",
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="Prepare report", state=state),
    ).state

    assert state.reporting_mode == ReportingMode.UNDECIDED
    assert state.handoff is None
    assert state.incidents[0].report_preparation.packet_ready is True
    state = prepare_report_draft(state)
    assert state.handoff is not None
    assert state.handoff.prefill.description
    assert state.handoff.prefill.financial_loss_amount == "5000"
    assert state.handoff.prefill.crime_domain == CrimeDomain.FINANCIAL_FRAUD


def test_multiple_amounts_require_one_corrected_total_before_confirmation() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere HDFC bank account se aaj Rs 10000 aur Rs 30000 unauthorized gaye",
            state=state,
        ),
    ).state
    assert len([entity for entity in state.incident.entities if entity.type.value == "amount"]) == 2

    ambiguous = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=state)
    ).state
    assert "corrected total" in ambiguous.turns[-1].content
    assert ambiguous.pending_question is not None
    assert ambiguous.pending_question.key == "final_loss_amount"
    assert ambiguous.pending_question.attempts == 1
    assert ambiguous.handoff is None

    repeated = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=ambiguous)
    ).state
    assert repeated.turns[-1].content != ambiguous.turns[-1].content
    assert "numeric form" in repeated.turns[-1].content
    assert repeated.pending_question is not None
    assert repeated.pending_question.attempts == 2

    corrected = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="total Rs 40000 tha", state=repeated)
    ).state
    confirmed = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=corrected)
    ).state
    amounts = [entity for entity in confirmed.incident.entities if entity.type.value == "amount"]
    assert [entity.normalized_value for entity in amounts] == ["40000"]
    assert all(entity.confirmed for entity in confirmed.incident.entities if entity.requires_confirmation)
    assert confirmed.handoff is None


def test_composite_indian_amount_is_one_confirmable_loss() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere account se 2 lakh 30 hazar chale gaye",
            state=state,
        ),
    ).state

    amounts = [entity for entity in state.incident.entities if entity.type.value == "amount"]
    assert [entity.normalized_value for entity in amounts] == ["230000"]
    assert state.pending_question is not None
    assert state.pending_question.key == "confirm_entities"
    assert "ek se zyada amount" not in state.turns[-1].content
    assert "₹2,30,000" in state.turns[-1].content


def test_contextual_ha_bol_diya_advances_stored_bank_question_without_llm() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere bank account se aaj Rs 5000 unauthorized chale gaye",
            state=state,
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=state)
    ).state
    assert state.pending_question is not None
    assert state.pending_question.key == "bank_contact_and_protect"

    progressed = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="ha bol diya", state=state)
    ).state

    assert "bank_contacted" in progressed.incidents[0].completed_actions
    assert "bank_protection_requested" not in progressed.incidents[0].completed_actions
    assert progressed.pending_question is not None
    assert progressed.pending_question.key == "bank_protection"
    assert "protection action" in progressed.turns[-1].content
    assert progressed.turns[-1].llm_provider is None
    assert "1930" not in progressed.turns[-1].content
    assert "CERT" not in progressed.turns[-1].content


@pytest.mark.parametrize(
    "completion",
    [
        "karva diya block",
        "kardiya block age batao",
        "account block karwa diya hai, ab next step batao",
    ],
)
def test_natural_bank_protection_completion_advances_stored_question_once(
    completion: str,
) -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere account se Rs 18000 nikal gaye", state=state
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=state)
    ).state

    progressed = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message=completion, state=state)
    ).state

    assert progressed.pending_question is not None
    assert progressed.pending_question.key == "transaction_reference_or_evidence"
    assert "bank_protection_requested" in progressed.incidents[0].completed_actions
    assert "transaction/UTR/reference number" in progressed.turns[-1].content
    assert "Protection action complete" not in progressed.turns[-1].content


def test_opening_bank_complaint_is_not_asked_again_after_amount_confirmation() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message=(
                "Mere business account se multiple transactions mein Rs 18 lakh "
                "nikal gaye. Bank mein complaint kar di hai, ab kya karu?"
            ),
            state=state,
        ),
    ).state

    assert "bank_contacted" in state.incidents[0].completed_actions
    confirmed = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=state)
    ).state

    assert confirmed.pending_question is not None
    assert confirmed.pending_question.key == "bank_protection"
    assert "Bank se contact karna record ho gaya hai" in confirmed.turns[-1].content


@pytest.mark.parametrize(
    ("message", "expected_domain", "required_text"),
    [
        (
            "Meri 15 saal ki cousin ko ek online friend ne private photos bhejne "
            "ke liye convince kiya tha. Ab woh person photos leak karne ki dhamki "
            "de raha hai aur paise maang raha hai. Woh bahut darr gayi hai, please "
            "batao abhi kya karein.",
            CrimeDomain.CHILD_SAFETY,
            "trusted adult",
        ),
        (
            "Mere ex ne meri kuch private photos apne paas rakhi hain aur ab mujhe "
            "threaten kar raha hai ki agar maine usse baat nahi ki toh woh photos "
            "online upload kar dega. Main bahut scared hu aur samajh nahi aa raha "
            "kisko report karu.",
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
            "intimate",
        ),
    ],
)
def test_private_image_threats_receive_grounded_safety_before_report_handoff(
    message: str, expected_domain: CrimeDomain, required_text: str
) -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    updated = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message=message, state=state)
    ).state

    reply = updated.turns[-1]
    assert updated.incident.crime_domain == expected_domain
    assert CrimeDomain.ONLINE_HARASSMENT in updated.incident.related_domains
    assert updated.pending_question is not None
    assert updated.pending_question.key == "immediate_danger"
    assert reply.grounding_status == GroundingStatus.GROUNDED
    assert reply.sources
    assert required_text in reply.content
    assert "1." in reply.content and "2." in reply.content and "3." in reply.content
    assert "physical danger" in reply.content
    assert "Bank/payment provider" not in reply.content
    assert "reporting flow open" not in reply.content


NON_FINANCIAL_DOMAIN_CASES = [
    ("I paid for an online t-shirt but the order was not delivered", CrimeDomain.ECOMMERCE_FRAUD, "seller_contacted"),
    ("My Instagram account is compromised and I cannot log in", CrimeDomain.ACCOUNT_COMPROMISE, "password_changed_trusted_device"),
    ("A fake police officer put my father under digital arrest", CrimeDomain.IMPERSONATION, "impersonator_identifiers"),
    ("Someone stole my identity", CrimeDomain.IDENTITY_THEFT, "identity_items_exposed"),
    ("Someone keeps sending abusive threats on Instagram", CrimeDomain.ONLINE_HARASSMENT, "immediate_danger"),
    ("A woman's morphed image is being used for blackmail", CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY, "immediate_danger"),
    ("Someone is tracking my location and cyberstalking me", CrimeDomain.CYBERSTALKING, "immediate_danger"),
    ("A fake KYC link asked for my password and I opened it", CrimeDomain.PHISHING_SCAM, "credentials_or_otp_entered"),
    ("I installed an unknown APK and gave remote access", CrimeDomain.MALWARE, "money_or_account_affected"),
    ("This viral post contains dangerous fake news", CrimeDomain.MISINFORMATION, "immediate_harm_risk"),
    ("An adult is grooming a child online", CrimeDomain.CHILD_SAFETY, "immediate_danger"),
    ("I received a cyber terrorism threat against a hospital", CrimeDomain.CYBER_TERRORISM, "immediate_physical_threat"),
]


@pytest.mark.parametrize(("message", "domain", "first_key"), NON_FINANCIAL_DOMAIN_CASES)
def test_each_non_financial_domain_stores_and_advances_specialised_question(
    message: str,
    domain: CrimeDomain,
    first_key: str,
) -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    first = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message=message, state=state)
    ).state

    assert first.incident.crime_domain == domain
    assert first.pending_question is not None
    assert first.pending_question.key == first_key
    assert first.turns[-1].llm_provider is None
    first_question = first.turns[-1].content
    assert "1." in first_question
    assert "?" in first_question
    assert "1930" not in first_question

    second = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="yes", state=first)
    ).state

    assert second.incident.crime_domain == domain
    assert second.pending_question is not None
    assert second.pending_question.key != first_key
    assert second.turns[-1].content != first_question
    assert second.turns[-1].llm_provider is None
    assert f"answered:{first_key}" in second.incidents[0].completed_actions


@pytest.mark.parametrize(("message", "domain", "first_key"), NON_FINANCIAL_DOMAIN_CASES)
def test_each_domain_accepts_yes_no_and_uncertain_for_expected_yes_no_questions(
    message: str,
    domain: CrimeDomain,
    first_key: str,
) -> None:
    for answer, answer_class in (("yes", "yes"), ("no", "no"), ("pata nahi", "uncertain")):
        state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
        state = CyberSaathiService.reply(
            state.id, ConversationMessageRequest(message=message, state=state)
        ).state
        for _ in range(4):
            if state.pending_question is None or state.pending_question.answer_type.value == "yes_no":
                break
            state = CyberSaathiService.reply(
                state.id,
                ConversationMessageRequest(message="details unavailable", state=state),
            ).state
        assert state.pending_question is not None
        assert state.pending_question.answer_type.value == "yes_no"
        question_key = state.pending_question.key

        answered = CyberSaathiService.reply(
            state.id, ConversationMessageRequest(message=answer, state=state)
        ).state

        assert answered.incident.crime_domain == domain
        assert f"answer:{question_key}:{answer_class}" in answered.incidents[0].completed_actions
        assert answered.pending_question is None or answered.pending_question.key != question_key


@pytest.mark.parametrize(("message", "domain", "first_key"), NON_FINANCIAL_DOMAIN_CASES)
def test_each_domain_reaches_packet_then_explicit_draft_handoff(
    message: str,
    domain: CrimeDomain,
    first_key: str,
) -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message=message, state=state)
    ).state
    for _ in range(6):
        if state.pending_question is None:
            break
        answer = "no" if state.pending_question.answer_type.value == "yes_no" else "not provided"
        state = CyberSaathiService.reply(
            state.id, ConversationMessageRequest(message=answer, state=state)
        ).state

    preparation = state.incidents[0].report_preparation
    assert preparation.packet_ready is True
    assert preparation.draft_prepared is False
    assert state.handoff is None

    prepared = prepare_report_draft(state)
    assert prepared.incident.crime_domain == domain
    assert prepared.incidents[0].report_preparation.draft_prepared is True
    assert prepared.handoff is not None
    assert prepared.handoff.prefill.crime_domain == domain


def test_uncertain_high_impact_amount_is_not_silently_confirmed() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="Mere bank se Rs 5000 chale gaye", state=state),
    ).state
    pending_ids = list(state.pending_confirmation_entity_ids)

    uncertain = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="pata nahi", state=state)
    ).state

    assert uncertain.pending_confirmation_entity_ids == pending_ids
    assert uncertain.pending_question is not None
    assert uncertain.pending_question.answer_type.value == "confirm_entities"
    assert uncertain.incident.entities[0].confirmed is False
    assert uncertain.handoff is None


@pytest.mark.parametrize(
    ("message", "expected_domain"),
    (
        ("Something unusual happened online", CrimeDomain.UNKNOWN),
        ("ऑनलाइन कुछ अजीब हुआ", CrimeDomain.UNKNOWN),
        ("Somthing odd hapend onlne", CrimeDomain.UNKNOWN),
        ("I need help with another cyber issue", CrimeDomain.OTHER),
        ("मुझे अन्य साइबर समस्या में मदद चाहिए", CrimeDomain.OTHER),
        ("I need help with an othr cyber isue", CrimeDomain.OTHER),
    ),
)
def test_unknown_or_other_domain_asks_one_safe_clarification_without_false_handoff(
    message: str, expected_domain: CrimeDomain
) -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message=message, state=state)
    ).state

    assert state.incident.crime_domain == expected_domain
    assert state.handoff is None
    assert state.turns[-1].content.count("?") == 1
    assert "1930" not in state.turns[-1].content
    assert "CERT" not in state.turns[-1].content


def test_fake_cyber_police_first_asks_for_caller_profile_or_channel() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Nakli cyber police banke case ka dar dikha rahe hain.",
            state=state,
        ),
    ).state

    assert state.incident.crime_domain == CrimeDomain.IMPERSONATION
    assert state.pending_question is not None
    assert state.pending_question.key == "impersonator_identifiers"
    assert "Phone number, account, profile" in state.turns[-1].content
    assert "1930" not in state.turns[-1].content


def test_apk_remote_access_does_not_repeat_stated_facts() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Maine loan APK install kiya aur remote access de diya.",
            state=state,
        ),
    ).state

    assert state.incident.crime_domain == CrimeDomain.MALWARE
    assert state.pending_question is not None
    assert state.pending_question.key == "money_or_account_affected"
    assert "paise gaye" in state.turns[-1].content
    assert "remote access ya app install allow" not in state.turns[-1].content


def test_ecommerce_no_seller_reply_advances_to_order_reference() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Maine online order payment kiya, delivery nahi hui aur seller reply nahi kar raha.",
            state=state,
        ),
    ).state

    assert state.incident.crime_domain == CrimeDomain.ECOMMERCE_FRAUD
    assert state.pending_question is not None
    assert state.pending_question.key == "order_reference"
    assert "order number" in state.turns[-1].content
    assert "1930" not in state.turns[-1].content


def test_phishing_initial_message_remembers_click_and_password() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mujhe KYC update ka fake link aaya, maine click karke password enter kar diya. Ab login nahi ho raha.",
            state=state,
        ),
    ).state

    assert state.incident.crime_domain == CrimeDomain.PHISHING_SCAM
    assert CrimeDomain.ACCOUNT_COMPROMISE in state.incident.related_domains
    assert state.pending_question is not None
    assert state.pending_question.key == "additional_sensitive_data_shared"
    assert "password" in state.turns[-1].content
    assert "Suspicious link open" not in state.turns[-1].content


def test_phishing_money_loss_denial_does_not_promote_to_financial() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mujhe KYC fake link aaya, maine click karke password enter kar diya",
            state=state,
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="nahi, sirf password enter kiya tha", state=state),
    ).state
    denied = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="nahi, koi paisa debit ya transfer nahi hua",
            state=state,
        ),
    ).state

    assert denied.incident.crime_domain == CrimeDomain.PHISHING_SCAM
    assert denied.pending_question is not None
    assert denied.pending_question.key == "app_or_remote_access"
    assert "1930" not in denied.turns[-1].content


def test_phishing_recovery_attempt_answers_stored_question_before_blocker_route() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    messages = (
        "Mujhe KYC fake link aaya, maine click karke password enter kar diya",
        "nahi, sirf password enter kiya tha",
        "nahi, koi paisa debit ya transfer nahi hua",
        "nahi, koi app install ya remote access nahi diya",
        "official website se password reset try kiya, abhi login nahi ho raha",
    )
    for message in messages:
        state = CyberSaathiService.reply(
            state.id, ConversationMessageRequest(message=message, state=state)
        ).state

    assert state.incident.crime_domain == CrimeDomain.PHISHING_SCAM
    assert state.pending_question is not None
    assert state.pending_question.key == "phishing_source_and_time"
    assert "Sender, phone number" in state.turns[-1].content
    assert state.turns[-1].llm_provider is None


def test_exact_financial_journey_reaches_packet_without_repeating_or_escalation_dump() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mujhe Pune mein fake government call aaya. Unhone 2 lakh 30 hazar transfer karwa liye. Ab kya karu?",
            state=state,
        ),
    ).state
    amounts = [entity for entity in state.incident.entities if entity.type.value == "amount"]
    assert state.language == LanguageCode.HINGLISH
    assert len(amounts) == 1
    assert amounts[0].normalized_value == "230000"
    assert "1." in state.turns[-1].content
    assert "1930" not in state.turns[-1].content
    assert "CERT" not in state.turns[-1].content

    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=state)
    ).state
    assert state.pending_question is not None
    assert state.pending_question.key == "bank_contact_and_protect"

    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="haan, bank ko official number se call kar diya", state=state),
    ).state
    assert state.pending_question is not None
    assert state.pending_question.key == "bank_protection"

    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="account froe karwa diya bank se", state=state),
    ).state
    assert state.pending_question is not None
    assert state.pending_question.key == "transaction_reference_or_evidence"

    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="UTR ABC123456 kal 4:30 pm ka hai", state=state),
    ).state
    preparation = state.incidents[0].report_preparation
    assert preparation.packet_ready is True
    assert preparation.draft_prepared is False
    assert state.handoff is None
    assert "1930" not in state.turns[-1].content
    assert "CERT" not in state.turns[-1].content

    # The newly extracted UTR/date/time are critical report identifiers, so
    # they must be confirmed once before the saved draft can use them.
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=state)
    ).state
    assert state.pending_question is not None
    assert state.pending_question.key == "optional_suspect_details"
    assert state.pending_confirmation_entity_ids == []
    assert "amount" not in state.turns[-1].content.casefold()
    assert "optional" in state.turns[-1].content.casefold()
    assert "koi baat nahi" in state.turns[-1].content.casefold()

    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="pata nahi", state=state)
    ).state
    assert state.pending_question is None
    assert "answered:optional_suspect_details" in state.incidents[0].completed_actions

    state = prepare_report_draft(state)
    assert state.handoff is not None
    assert state.handoff.prefill.financial_loss_amount == "230000"
    assert state.handoff.prefill.incident_at == f"{(date.today() - timedelta(days=1)).isoformat()}T16:30:00"
    assert state.handoff.prefill.city == "Pune"
    assert state.handoff.prefill.state == "Maharashtra"
    assert "ABC123456" not in state.handoff.prefill.suspect_identifiers
    assert state.incidents[0].report_preparation.draft_prepared is True


def test_optional_suspect_answer_is_preserved_for_editable_report_prefill() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Maine seller ko payment kiya par order deliver nahi hua",
            state=state,
        ),
    ).state

    for _ in range(6):
        assert state.pending_question is not None
        if state.pending_question.key == "optional_suspect_details":
            break
        answer = "nahi" if state.pending_question.answer_type.value == "yes_no" else "pata nahi"
        state = CyberSaathiService.reply(
            state.id, ConversationMessageRequest(message=answer, state=state)
        ).state

    assert state.pending_question is not None
    assert state.pending_question.key == "optional_suspect_details"
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Seller ka naam Rakesh tha aur profile alias mobiledeal tha",
            state=state,
        ),
    ).state
    state = prepare_report_draft(state)

    assert state.handoff is not None
    assert state.handoff.prefill.suspect_details == (
        "Seller ka naam Rakesh tha aur profile alias mobiledeal tha"
    )
    assert state.handoff.prefill.suspect_name == "Rakesh"
    assert state.handoff.prefill.suspect_alias == "mobiledeal"
    suspect_item = next(
        item
        for item in state.incidents[0].report_preparation.checklist
        if item.key == "suspect_details"
    )
    assert suspect_item.status.value == "collected"
    assert suspect_item.value_preview == state.handoff.prefill.suspect_details


def test_long_incident_summary_is_safely_bounded_in_report_preview() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="My bank account had an unauthorized transaction", state=state),
    ).state
    for index in range(6):
        state = CyberSaathiService.reply(
            state.id,
            ConversationMessageRequest(
                message=f"This is the same incident detail {index}: " + ("additional evidence context " * 30),
                state=state,
            ),
        ).state
    description = next(
        item for item in state.incidents[0].report_preparation.checklist if item.key == "incident_description"
    )
    assert description.value_preview is not None
    assert len(description.value_preview) <= 300


def test_consented_conversation_resumes_from_redacted_server_state(api_client) -> None:
    client, _ = api_client
    started = client.post(
        "/api/v1/cyber-saathi/conversations",
        json={"language": "EN", "storage_consent": True},
    )
    state = started.json()["data"]["state"]
    updated = client.post(
        f"/api/v1/cyber-saathi/conversations/{state['id']}/messages",
        json={
            "message": "My phone is 9876543210 and email is victim@example.com; my bank was debited today",
            "state": state,
        },
    )
    assert updated.status_code == 200
    resumed = client.get(f"/api/v1/cyber-saathi/conversations/{state['id']}")
    assert resumed.status_code == 200
    serialized = resumed.text
    assert "9876543210" not in serialized
    assert "victim@example.com" not in serialized
    assert "REDACTED_PHONE" in serialized
    assert "REDACTED_EMAIL" in serialized


def test_unrelated_resume_is_rejected_as_incident_evidence() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="My bank had an unauthorized payment", state=state),
    ).state
    analysis = AttachmentAnalysis(
        file_name="resume.pdf",
        mime_type="application/pdf",
        file_size=200,
        checksum="c" * 64,
        media_summary="PDF document",
        extraction_method="pdf_text",
        extraction_status="completed",
        extracted_text_preview="Resume curriculum vitae education professional experience software skills",
    )
    try:
        CyberSaathiService.add_attachment(state.id, state, analysis)
    except APIError as error:
        assert error.code == "EVIDENCE_NOT_RELEVANT"
    else:
        raise AssertionError("An unrelated resume must not be accepted as incident evidence")


def test_attachment_is_inspected_transiently_and_added_to_report_packet() -> None:
    client = TestClient(app)
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere saath phishing hua aur maine message ka screenshot rakha hai",
            state=state,
        ),
    ).state
    png = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\x0dIHDR" + (320).to_bytes(4, "big") + (240).to_bytes(4, "big")

    response = client.post(
        f"/api/v1/cyber-saathi/conversations/{state.id}/attachments",
        data={"state_json": state.model_dump_json()},
        files={"file": ("proof.png", png, "image/png")},
    )

    assert response.status_code == 200
    updated = response.json()["data"]["state"]
    attachment = updated["incidents"][0]["report_preparation"]["attachments"][0]
    assert attachment["file_name"] == "proof.png"
    assert attachment["media_summary"] == "PNG image · 320 × 240 pixels"
    assert attachment["needs_user_review"] is True


def test_attachment_rejects_content_that_does_not_match_extension() -> None:
    client = TestClient(app)
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="My account was compromised", state=state),
    ).state

    response = client.post(
        f"/api/v1/cyber-saathi/conversations/{state.id}/attachments",
        data={"state_json": state.model_dump_json()},
        files={"file": ("fake.png", b"not an image", "image/png")},
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "ATTACHMENT_SIGNATURE_MISMATCH"


def test_same_incident_followup_merges_details_without_losing_original_facts() -> None:
    state = CyberSaathiService.start(
        ConversationCreate(language=LanguageCode.HINGLISH)
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Mere bank account se Rs 5000 unauthorized nikal gaye", state=state
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="haan", state=state),
    ).state

    followed_up = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Maine usi link par OTP bhi enter kar diya tha", state=state
        ),
    ).state

    assert len(followed_up.incidents) == 1
    assert followed_up.incident.crime_domain == CrimeDomain.FINANCIAL_FRAUD
    assert "Rs 5000" in (followed_up.incident.summary or "")
    assert "OTP" in (followed_up.incident.summary or "")
    assert any(entity.normalized_value == "5000" for entity in followed_up.incident.entities)


def test_noisy_women_child_message_gets_domain_specific_grounded_guidance() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state

    updated = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="Someone using my morfed img im mminor girl", state=state
        ),
    ).state

    assert updated.incident.crime_domain == CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY
    assert updated.turns[-1].grounding_status == GroundingStatus.GROUNDED
    assert updated.turns[-1].sources


def test_hinglish_financial_follow_up_changes_language_and_advances_after_bank_freeze() -> None:
    """Regression for the real victim journey, not a source-text dump."""
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.EN)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message=(
                "Mere papa ko call karke illegal transaction ka dar dikhaya aur "
                "unse 4 lakh transfer karwa liye. Abhi kya karu?"
            ),
            state=state,
        ),
    ).state

    assert state.language == LanguageCode.HINGLISH
    assert state.incident.crime_domain == CrimeDomain.FINANCIAL_FRAUD
    assert "official channel" in state.turns[-1].content

    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message="haan", state=state)
    ).state
    assert "Amount confirm ho gaya" in state.turns[-1].content
    assert "keep asking only" not in state.turns[-1].content

    progressed = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(
            message="mene account froe krvadiya bank se ab", state=state
        ),
    ).state

    reply = progressed.turns[-1].content
    assert progressed.language == LanguageCode.HINGLISH
    assert "1. Bank wala action record ho gaya hai." in reply
    assert "transaction/UTR/reference number" in reply
    assert "CERT" not in reply
    assert "1930" not in reply
    assert progressed.handoff is None
    assert progressed.pending_question is not None
    assert progressed.pending_question.key == "transaction_reference_or_evidence"


def test_generic_lure_variants_choose_the_correct_victim_workflow() -> None:
    cases = {
        "Arogya department bolkar Ayushman limit badhane ke naam par OTP liya aur mere bank se sare paise chale gaye": CrimeDomain.FINANCIAL_FRAUD,
        "Nakli cyber police banke case ka dar dikha rahe hain": CrimeDomain.IMPERSONATION,
        "Maine loan APK install kiya aur remote access de diya": CrimeDomain.MALWARE,
    }

    for message, expected_domain in cases.items():
        normalized = UnderstandingEngine.normalize_query(message)
        assert UnderstandingEngine.classify_domain(normalized) == expected_domain


@pytest.mark.parametrize(
    ("message", "primary", "related"),
    [
        ("Fake Ayushman government call par OTP liya aur bank se paise chale gaye", CrimeDomain.FINANCIAL_FRAUD, CrimeDomain.IMPERSONATION),
        ("Fake cyber police ne case ka dar dikhaya", CrimeDomain.IMPERSONATION, None),
        ("Fake cyber police ne mujhse money transfer karwa liya", CrimeDomain.FINANCIAL_FRAUD, CrimeDomain.IMPERSONATION),
        ("Fake KYC link par maine password enter kiya", CrimeDomain.PHISHING_SCAM, CrimeDomain.ACCOUNT_COMPROMISE),
        ("APK install karke remote access diya aur bank se paise chale gaye", CrimeDomain.FINANCIAL_FRAUD, CrimeDomain.MALWARE),
        ("Online order ka payment kiya par delivery nahi hui", CrimeDomain.ECOMMERCE_FRAUD, None),
    ],
)
def test_cross_domain_branches_keep_primary_and_related_incident_context(
    message: str,
    primary: CrimeDomain,
    related: CrimeDomain | None,
) -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id, ConversationMessageRequest(message=message, state=state)
    ).state

    assert state.incident.crime_domain == primary
    if related is not None:
        assert related in state.incident.related_domains
    if primary == CrimeDomain.ECOMMERCE_FRAUD:
        assert CrimeDomain.FINANCIAL_FRAUD not in state.incident.related_domains


def test_phishing_followup_with_money_loss_promotes_primary_financial_route() -> None:
    state = CyberSaathiService.start(ConversationCreate(language=LanguageCode.HINGLISH)).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="Fake KYC link par password enter kiya", state=state),
    ).state
    assert state.incident.crime_domain == CrimeDomain.PHISHING_SCAM

    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="Ab bank se Rs 25000 paise chale gaye", state=state),
    ).state

    assert state.incident.crime_domain == CrimeDomain.FINANCIAL_FRAUD
    assert CrimeDomain.PHISHING_SCAM in state.incident.related_domains
    assert "Rs 25000" in (state.incident.summary or "")
