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


def test_reporting_mode_selection_is_acknowledged_without_rerouting_incident() -> None:
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
    assert selected.handoff is not None
    assert selected.handoff.reporting_mode == ReportingMode.IDENTIFIED
    assert "Identified reporting selected" in selected.turns[-1].content
    assert "OTP/PIN/password" not in selected.turns[-1].content


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
    assert ready.incident.status == IncidentStatus.READY_TO_REPORT

    activated = CyberSaathiService.reply(
        ready.id,
        ConversationMessageRequest(message="next incident", state=ready),
    ).state
    assert activated.incident.crime_domain == CrimeDomain.IMPERSONATION
    assert [item.queue_status.value for item in activated.incidents] == [
        "completed",
        "active",
    ]


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
    assert "password/OTP" in progressed.turns[-1].content
    assert "bank/provider" not in progressed.turns[-1].content
    assert "1930" not in progressed.turns[-1].content


def test_completed_ecommerce_steps_offer_nch_not_cybercrime_handoff() -> None:
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

    assert completed.incident.status == IncidentStatus.READY_TO_REPORT
    assert completed.handoff is None
    assert "National Consumer Helpline" in completed.turns[-1].content
    assert "NCH" in completed.turns[-1].content


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
            message="Mere bank account se Rs 5000 unauthorized nikal gaye", state=state
        ),
    ).state
    state = CyberSaathiService.reply(
        state.id,
        ConversationMessageRequest(message="haan", state=state),
    ).state

    preparation = state.incidents[0].report_preparation
    assert preparation.reporting_for == "SELF"
    assert preparation.ready_for_review is True
    assert state.handoff is not None
    assert state.handoff.prefill.reporting_for == "SELF"


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
