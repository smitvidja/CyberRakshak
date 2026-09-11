from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
import re
from uuid import UUID

from app.core.errors import APIError
from app.schemas.cyber_saathi import (
    AttachmentAnalysis,
    ComplaintPrefill,
    ConversationCreate,
    ConversationIncident,
    ConversationMessageRequest,
    ConversationResponse,
    ConversationSource,
    ConversationState,
    ConversationStatus,
    ConversationTurn,
    CrimeDomain,
    Entity,
    EntityType,
    ExpectedAnswerType,
    GroundingStatus,
    HandoffImplementationStatus,
    HandoffTarget,
    IncidentState,
    IncidentQueueStatus,
    IncidentStatus,
    Intent,
    KnowledgeDomain,
    KnowledgeMatch,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    LanguageCode,
    LLMProvider,
    PendingQuestion,
    ReportingMode,
    Sentiment,
    TurnKind,
    TurnPurpose,
    Urgency,
    UnderstandingResult,
    WorkflowHandoff,
)
from app.services.cyber_saathi_conversation import (
    blocked_action,
    build_report_preparation,
    classify_turn_purpose,
    find_matching_incident,
    message_fingerprint,
    normalized_text,
)
from app.services.cyber_saathi_knowledge import KnowledgeService
from app.services.cyber_saathi_llm import get_llm_gateway
from app.services.cyber_saathi_understanding import UnderstandingEngine


YES_MARKERS = {"yes", "correct", "confirm", "haan", "ha", "हाँ", "सही"}
NO_MARKERS = {"no", "nope", "nahi", "nahin", "nhi", "नहीं"}
UNCERTAIN_MARKERS = {
    "not sure", "don't know", "dont know", "pata nahi", "malum nahi",
    "yaad nahi", "पता नहीं", "मालूम नहीं", "शायद",
}
CONTEXTUAL_YES_MARKERS = YES_MARKERS | {
    "haan bol diya", "ha bol diya", "bol diya", "kar diya", "kr diya",
    "ho gaya", "done", "yes done", "haan kar diya", "हाँ कर दिया",
}
NEXT_INCIDENT_MARKERS = {
    "next incident", "next case", "switch incident", "switch case",
    "agla incident", "agla case", "dusra incident", "doosra incident",
    "अगली घटना", "दूसरी घटना",
}
NEW_SUBJECT_MARKERS = {
    "my father", "my mother", "my wife", "my husband", "my brother", "my sister",
    "mere papa", "meri mummy", "meri maa", "mere bhai", "meri behen",
    "another incident", "another scam", "another fraud", "alag fraud",
}
SAME_INCIDENT_MARKERS = {
    "same incident", "same case", "isi incident", "ye same incident",
    "yahi incident", "इसी घटना", "यही घटना",
}
LANGUAGE_SWITCHES = {
    LanguageCode.EN: ("reply in english", "answer in english", "english please"),
    LanguageCode.HI: ("reply in hindi", "answer in hindi", "hindi please", "हिंदी में"),
    LanguageCode.HINGLISH: ("reply in hinglish", "answer in hinglish", "hinglish please"),
}
BANK_CONTACT_MARKERS = (
    "called the bank", "contacted the bank", "bank complaint", "bank ko call",
    "bank ko official number se call", "bank ke official number se call",
    "bank me call", "bank mein call", "bank se baat", "bank contact",
    "bank ko inform", "bank ko bata", "bank ko report", "bank mein complaint",
    "bank me complaint", "bank se complaint",
)
BANK_PROTECTION_MARKERS = (
    "account freeze", "account frozen", "account froe", "account block",
    "bank se freeze", "bank se froe", "freeze karwa", "froe karwa",
    "bank se karwa diya", "bank ne block", "outgoing transaction band",
    "block karwa", "block karva", "block krwa", "karwa diya block",
    "karva diya block", "krwa diya block", "krva diya block",
    "kar diya block", "kardiya block", "kr diya block", "krdiya block",
)
ALL_DONE_MARKERS = (
    "all done", "did all", "done everything", "sab kar liya", "sab kr liya",
    "ye sab kar liya", "ye sab kr liya", "everything complete", "details complete",
    "details are complete", "i have provided all details", "ready to file",
    "ready to report", "file the report", "file report", "submit report",
    "sab kuch ho gaya", "सब कर लिया", "सब कुछ हो गया",
)
GENERAL_GUIDANCE_MARKERS = (
    "how can i stay safe", "how to stay safe", "explain phishing safety",
    "safety tips", "awareness tips", "bachne ke tips", "safe kaise",
)
MONEY_LOSS_DENIAL_MARKERS = (
    "no money was lost", "no money lost", "did not lose money", "didn't lose money",
    "no debit", "not debited", "no transfer", "money was not debited",
    "paise nahi gaye", "paisa nahi gaya", "paisa debit nahi", "paise debit nahi",
    "koi paisa debit ya transfer nahi", "transfer nahi hua", "debit nahi hua",
    "पैसे नहीं गए", "पैसा नहीं कटा", "ट्रांसफर नहीं हुआ",
)

SUSPECT_IDENTIFIER_TYPES = {
    EntityType.PHONE_NUMBER,
    EntityType.UPI_ID,
    EntityType.URL,
    EntityType.EMAIL,
    EntityType.USERNAME,
    EntityType.ACCOUNT_ID,
}

CITY_STATE_BY_CITY = {
    "delhi": "Delhi",
    "mumbai": "Maharashtra",
    "ahmedabad": "Gujarat",
    "bengaluru": "Karnataka",
    "bangalore": "Karnataka",
    "kolkata": "West Bengal",
    "chennai": "Tamil Nadu",
    "pune": "Maharashtra",
    "jaipur": "Rajasthan",
}

DOMAIN_QUESTION_FLOWS: dict[CrimeDomain, tuple[tuple[str, ExpectedAnswerType], ...]] = {
    CrimeDomain.ECOMMERCE_FRAUD: (
        ("seller_contacted", ExpectedAnswerType.YES_NO),
        ("order_reference", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
        ("payment_proof", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
        ("delivery_or_refund_promise", ExpectedAnswerType.FREE_TEXT),
    ),
    CrimeDomain.ACCOUNT_COMPROMISE: (
        ("account_access_available", ExpectedAnswerType.YES_NO),
        ("password_changed_trusted_device", ExpectedAnswerType.YES_NO),
        ("sessions_and_mfa_secured", ExpectedAnswerType.YES_NO),
        ("unknown_activity_evidence", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
    ),
    CrimeDomain.IMPERSONATION: (
        ("impersonator_identifiers", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
        ("impersonator_still_connected", ExpectedAnswerType.YES_NO),
        ("money_or_sensitive_data_shared", ExpectedAnswerType.YES_NO),
        ("remote_access_granted", ExpectedAnswerType.YES_NO),
    ),
    CrimeDomain.IDENTITY_THEFT: (
        ("identity_items_exposed", ExpectedAnswerType.FREE_TEXT),
        ("identity_misuse_observed", ExpectedAnswerType.YES_NO),
        ("affected_accounts_secured", ExpectedAnswerType.YES_NO),
        ("misuse_evidence", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
    ),
    CrimeDomain.ONLINE_HARASSMENT: (
        ("immediate_danger", ExpectedAnswerType.YES_NO),
        ("platform_and_profile", ExpectedAnswerType.FREE_TEXT),
        ("harassment_evidence_preserved", ExpectedAnswerType.YES_NO),
        ("platform_block_report", ExpectedAnswerType.YES_NO),
    ),
    CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY: (
        ("immediate_danger", ExpectedAnswerType.YES_NO),
        ("affected_person_and_age", ExpectedAnswerType.FREE_TEXT),
        ("platform_and_profile", ExpectedAnswerType.FREE_TEXT),
        ("safe_evidence_preserved", ExpectedAnswerType.YES_NO),
    ),
    CrimeDomain.CYBERSTALKING: (
        ("immediate_danger", ExpectedAnswerType.YES_NO),
        ("stalker_knows_location", ExpectedAnswerType.YES_NO),
        ("platform_and_profile", ExpectedAnswerType.FREE_TEXT),
        ("stalking_evidence_preserved", ExpectedAnswerType.YES_NO),
    ),
    CrimeDomain.PHISHING_SCAM: (
        ("link_opened", ExpectedAnswerType.YES_NO),
        ("credentials_or_otp_entered", ExpectedAnswerType.YES_NO),
        ("additional_sensitive_data_shared", ExpectedAnswerType.YES_NO),
        ("money_lost_after_phishing", ExpectedAnswerType.YES_NO),
        ("app_or_remote_access", ExpectedAnswerType.YES_NO),
        ("affected_account_secured", ExpectedAnswerType.YES_NO),
        ("phishing_source_and_time", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
    ),
    CrimeDomain.MALWARE: (
        ("app_or_apk_installed", ExpectedAnswerType.YES_NO),
        ("remote_access_granted", ExpectedAnswerType.YES_NO),
        ("money_or_account_affected", ExpectedAnswerType.YES_NO),
        ("device_disconnected", ExpectedAnswerType.YES_NO),
        ("unknown_activity_evidence", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
    ),
    CrimeDomain.MISINFORMATION: (
        ("claim_and_source", ExpectedAnswerType.FREE_TEXT),
        ("immediate_harm_risk", ExpectedAnswerType.YES_NO),
        ("source_link_or_capture", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
        ("platform_reported", ExpectedAnswerType.YES_NO),
    ),
    CrimeDomain.CHILD_SAFETY: (
        ("immediate_danger", ExpectedAnswerType.YES_NO),
        ("affected_person_and_age", ExpectedAnswerType.FREE_TEXT),
        ("platform_and_profile", ExpectedAnswerType.FREE_TEXT),
        ("trusted_adult_and_evidence", ExpectedAnswerType.YES_NO),
    ),
    CrimeDomain.CYBER_TERRORISM: (
        ("immediate_physical_threat", ExpectedAnswerType.YES_NO),
        ("threat_is_ongoing", ExpectedAnswerType.YES_NO),
        ("source_account_or_url", ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE),
        ("threat_evidence_preserved", ExpectedAnswerType.YES_NO),
    ),
}

logger = logging.getLogger(__name__)


def _compact_incident_summary(current: str, detail: str, limit: int = 2000) -> str:
    combined = f"{current.strip()} | Follow-up: {detail.strip()}".strip(" |")
    if len(combined) <= limit:
        return combined
    head_length = limit // 2
    tail_length = limit - head_length - 3
    return f"{combined[:head_length]} … {combined[-tail_length:]}"


def _domains_may_share_incident(left: CrimeDomain, right: CrimeDomain) -> bool:
    related_groups = (
        {
            CrimeDomain.FINANCIAL_FRAUD,
            CrimeDomain.PHISHING_SCAM,
            CrimeDomain.ACCOUNT_COMPROMISE,
            CrimeDomain.IMPERSONATION,
            CrimeDomain.IDENTITY_THEFT,
            CrimeDomain.MALWARE,
        },
        {
            CrimeDomain.ONLINE_HARASSMENT,
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
            CrimeDomain.CHILD_SAFETY,
            CrimeDomain.CYBERSTALKING,
            CrimeDomain.IMPERSONATION,
        },
    )
    return any(left in group and right in group for group in related_groups)


@dataclass
class RoutedReply:
    content: str
    kind: TurnKind
    grounding_status: GroundingStatus = GroundingStatus.NOT_USED
    sources: list[ConversationSource] = field(default_factory=list)
    retrieval_latency_ms: float | None = None
    llm_provider: LLMProvider | None = None
    llm_model: str | None = None
    llm_fallback_used: bool = False
    llm_latency_ms: float | None = None
    safety_flags: list[str] = field(default_factory=list)


class CyberSaathiService:
    @staticmethod
    def _resolve_response_language(
        current: LanguageCode,
        message: str,
        detected: LanguageCode,
    ) -> LanguageCode:
        lowered = normalized_text(message)
        # Asking in words ("reply in hindi") is an explicit instruction and still
        # switches the conversation, exactly like using the selector.
        for language, markers in LANGUAGE_SWITCHES.items():
            if any(marker in lowered for marker in markers):
                return language
        # Otherwise the chosen language is kept. The conversation no longer
        # re-guesses from each message: a citizen on English who types one
        # Devanagari line is not asking to be answered in Hinglish, and switching
        # on them produced chats mixing all three languages at once.
        if current in {LanguageCode.EN, LanguageCode.HI, LanguageCode.HINGLISH}:
            return current
        return detected

    @staticmethod
    def start(payload: ConversationCreate) -> ConversationResponse:
        welcome = CyberSaathiService._copy(payload.language, "welcome")
        state = ConversationState(
            language=payload.language,
            storage_consent=payload.storage_consent,
            reporting_mode=payload.reporting_mode,
            turns=[ConversationTurn(role="assistant", content=welcome, language=payload.language)],
        )
        return ConversationResponse(state=state)

    @staticmethod
    def reply(
        conversation_id: UUID, payload: ConversationMessageRequest
    ) -> ConversationResponse:
        state = payload.state.model_copy(deep=True)
        if state.id != conversation_id:
            raise APIError(
                status_code=409,
                code="CONVERSATION_STATE_MISMATCH",
                message="Conversation state does not match this conversation.",
            )
        if len(state.turns) >= 48:
            raise APIError(
                status_code=422,
                code="CONVERSATION_LIMIT_REACHED",
                message="Start a new conversation to continue.",
            )

        understanding = UnderstandingEngine.analyze(payload.message, state.language)
        language = CyberSaathiService._resolve_response_language(
            state.language, payload.message, understanding.response_language
        )
        if payload.reporting_mode is not None:
            state.reporting_mode = payload.reporting_mode
        effective_domain = (
            understanding.crime_domain
            if understanding.crime_domain != CrimeDomain.UNKNOWN
            else state.incident.crime_domain
        )
        if (
            state.reporting_mode == ReportingMode.ANONYMOUS
            and effective_domain
            not in {
                CrimeDomain.CHILD_SAFETY,
                CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
            }
        ):
            raise APIError(
                status_code=403,
                code="ANONYMOUS_REPORTING_NOT_AVAILABLE",
                message="Anonymous reporting is available only for Women and Child Safety incidents.",
            )
        state.language = language
        purpose = (
            TurnPurpose.REPORTING_MODE
            if payload.reporting_mode is not None
            else TurnPurpose.REPORT_PREPARATION
            if payload.prepare_report_draft
            else TurnPurpose.SWITCH_INCIDENT
            if CyberSaathiService._is_next_incident_command(payload.message)
            else TurnPurpose.CONFIRMATION
            if state.pending_confirmation_entity_ids and CyberSaathiService._is_confirmation(payload.message)
            else classify_turn_purpose(payload.message)
        )
        state.turns.append(
            ConversationTurn(
                role="user",
                content=payload.message.strip(),
                language=language,
                purpose=purpose,
            )
        )
        state.last_turn_purpose = purpose

        if payload.reporting_mode is not None:
            routed = CyberSaathiService._handle_reporting_mode_selection(state)
        elif CyberSaathiService._is_next_incident_command(payload.message):
            routed = CyberSaathiService._activate_next_incident(state)
        elif state.pending_confirmation_entity_ids and CyberSaathiService._is_confirmation(payload.message):
            if CyberSaathiService._has_ambiguous_pending_amounts(state):
                if state.pending_question is None:
                    CyberSaathiService._set_pending_question(
                        state,
                        "final_loss_amount",
                        ExpectedAnswerType.FINAL_LOSS_AMOUNT,
                    )
                state.pending_question.attempts += 1
                state.pending_question.last_answer = payload.message.strip()[:500]
                routed = CyberSaathiService._ambiguous_amount_reply(
                    language,
                    repeated=state.pending_question.attempts > 1,
                )
            else:
                CyberSaathiService._confirm_pending_entities(state)
                routed = CyberSaathiService._next_question_after_confirmation(state)
        elif (
            state.pending_confirmation_entity_ids
            and CyberSaathiService._looks_like_new_incident(
                state, payload.message, understanding
            )
        ):
            matching = find_matching_incident(state, payload.message, understanding)
            if matching is not None:
                purpose = TurnPurpose.DUPLICATE_INCIDENT
                routed = CyberSaathiService._route_duplicate_incident(state, matching)
            else:
                purpose = TurnPurpose.NEW_INCIDENT
                routed = CyberSaathiService._queue_new_incident(
                    state, payload.message, understanding
                )
        elif state.pending_confirmation_entity_ids and understanding.entities:
            purpose = TurnPurpose.CORRECTION
            routed = CyberSaathiService._revise_pending_entities(state, understanding.entities)
        elif (
            purpose == TurnPurpose.ACTION_BLOCKED
            and state.pending_question is not None
            and state.pending_question.answer_type
            not in {
                ExpectedAnswerType.CONFIRM_ENTITIES,
                ExpectedAnswerType.FINAL_LOSS_AMOUNT,
            }
        ):
            # A natural answer such as "password reset try kiya, login nahi"
            # can also look like a blocked-action request. The stored question
            # owns this turn; resolve it before any generic blocker guidance so
            # the conversation cannot lose its deterministic place.
            purpose = TurnPurpose.SAME_INCIDENT_DETAIL
            routed = CyberSaathiService._route_expected_answer(
                state, payload.message, understanding
            )
        elif purpose == TurnPurpose.ACTION_BLOCKED and state.incident.summary:
            routed = CyberSaathiService._route_blocked_action(
                state, payload.message, understanding
            )
        elif purpose == TurnPurpose.REPORT_PREPARATION:
            routed = CyberSaathiService._prepare_report(
                state,
                prepare_draft=payload.prepare_report_draft,
            )
        elif CyberSaathiService._looks_like_new_incident(state, payload.message, understanding):
            matching = find_matching_incident(state, payload.message, understanding)
            if matching is not None:
                purpose = TurnPurpose.DUPLICATE_INCIDENT
                routed = CyberSaathiService._route_duplicate_incident(state, matching)
            else:
                purpose = TurnPurpose.NEW_INCIDENT
                routed = CyberSaathiService._queue_new_incident(state, payload.message, understanding)
        elif CyberSaathiService._is_progress_followup(state, payload.message):
            purpose = TurnPurpose.NEXT_STEP
            routed = CyberSaathiService._route_progress_followup(
                state, payload.message, understanding
            )
        elif state.pending_question is not None:
            purpose = TurnPurpose.SAME_INCIDENT_DETAIL
            routed = CyberSaathiService._route_expected_answer(
                state, payload.message, understanding
            )
        else:
            routed = CyberSaathiService._route_mock_message(
                state, payload.message, understanding
            )

        CyberSaathiService._sync_active_incident(state)
        CyberSaathiService._refresh_report_preparation(state)
        CyberSaathiService._apply_report_readiness(state)
        if state.handoff is not None and state.handoff.target == HandoffTarget.REPORT_CRIME:
            state.handoff = CyberSaathiService._report_handoff(state)
        if state.pending_question is not None:
            state.pending_question_incident_id = state.pending_question.incident_id
        else:
            state.pending_question_incident_id = (
                state.active_incident_id if "?" in routed.content else None
            )
        state.last_turn_purpose = purpose

        state.turns.append(
            ConversationTurn(
                role="assistant",
                content=routed.content,
                language=language,
                kind=routed.kind,
                grounding_status=routed.grounding_status,
                sources=routed.sources,
                retrieval_latency_ms=routed.retrieval_latency_ms,
                llm_provider=routed.llm_provider,
                llm_model=routed.llm_model,
                llm_fallback_used=routed.llm_fallback_used,
                llm_latency_ms=routed.llm_latency_ms,
                safety_flags=routed.safety_flags,
                purpose=purpose,
            )
        )
        state.updated_at = datetime.now(timezone.utc)
        logger.info(
            "cyber_saathi_reply conversation_id=%s turns=%s domain=%s status=%s grounding=%s llm_fallback=%s",
            state.id,
            len(state.turns),
            state.incident.crime_domain.value,
            state.incident.status.value,
            routed.grounding_status.value,
            routed.llm_fallback_used,
        )
        return ConversationResponse(state=state, mock_provider=routed.llm_provider is None)

    @staticmethod
    def _handle_reporting_mode_selection(state: ConversationState) -> RoutedReply:
        CyberSaathiService._refresh_report_preparation(state)
        record = CyberSaathiService._active_record(state)
        if record is None:
            state.incident.status = IncidentStatus.AWAITING_USER_INPUT
            state.handoff = None
            copy = {
                LanguageCode.EN: "Please describe the incident before choosing a reporting mode.",
                LanguageCode.HI: "रिपोर्टिंग मोड चुनने से पहले घटना का विवरण दें।",
                LanguageCode.HINGLISH: "Reporting mode choose karne se pehle incident describe karein.",
            }
            return RoutedReply(copy.get(state.language, copy[LanguageCode.EN]), TurnKind.MESSAGE)
        if any(
            entity.requires_confirmation and not entity.confirmed
            for entity in state.incident.entities
        ):
            state.incident.status = IncidentStatus.AWAITING_CONFIRMATION
            state.handoff = None
            copy = {
                LanguageCode.EN: "Please confirm the highlighted critical detail before continuing to the report.",
                LanguageCode.HI: "रिपोर्ट पर आगे बढ़ने से पहले दिखाई गई महत्वपूर्ण जानकारी की पुष्टि करें।",
                LanguageCode.HINGLISH: "Report continue karne se pehle highlighted critical detail confirm karein.",
            }
            return RoutedReply(copy.get(state.language, copy[LanguageCode.EN]), TurnKind.MESSAGE)
        # The report form is where optional/Uknown details are edited.  A
        # reporting-mode click must not refuse the handoff merely because a
        # UTR, provider, date, or attachment was not supplied in the chat.
        state.incident.status = IncidentStatus.READY_TO_REPORT
        state.handoff = CyberSaathiService._report_handoff(state)
        if state.incident.crime_domain == CrimeDomain.ECOMMERCE_FRAUD:
            return RoutedReply(
                CyberSaathiService._copy(state.language, "ecommerce_all_done_next"),
                TurnKind.MESSAGE,
            )
        copy = {
            ReportingMode.IDENTIFIED: {
                LanguageCode.EN: "Identified reporting selected. Your incident details are ready for your review; use Continue to report when you are ready.",
                LanguageCode.HI: "पहचान सहित रिपोर्टिंग चुनी गई है। घटना विवरण आपकी समीक्षा के लिए तैयार हैं; तैयार होने पर रिपोर्ट जारी रखें।",
                LanguageCode.HINGLISH: "Identity ke saath reporting select ho gayi. Incident details review ke liye ready hain; ready hon to Continue to report use karein.",
            },
            ReportingMode.ANONYMOUS: {
                LanguageCode.EN: "Anonymous reporting selected. No reporter identity will be prefilled; review the incident details before continuing.",
                LanguageCode.HI: "गुमनाम रिपोर्टिंग चुनी गई है। रिपोर्टर की पहचान पहले से नहीं भरी जाएगी; आगे बढ़ने से पहले घटना विवरण देखें।",
                LanguageCode.HINGLISH: "Anonymous reporting select ho gayi. Reporter identity prefill nahi hogi; continue karne se pehle incident details review karein.",
            },
        }
        localized = copy.get(state.reporting_mode, copy[ReportingMode.IDENTIFIED])
        return RoutedReply(
            localized.get(state.language, localized[LanguageCode.EN]), TurnKind.HANDOFF
        )

    @staticmethod
    def _is_next_incident_command(message: str) -> bool:
        lowered = message.strip().casefold()
        return any(marker in lowered for marker in NEXT_INCIDENT_MARKERS)

    @staticmethod
    def _ensure_active_incident(state: ConversationState) -> None:
        if state.active_incident_id is not None:
            return
        active = next(
            (
                record
                for record in state.incidents
                if record.queue_status == IncidentQueueStatus.ACTIVE
            ),
            None,
        )
        if active is not None:
            state.active_incident_id = active.id
            return
        if state.incident.summary or state.incident.crime_domain != CrimeDomain.UNKNOWN:
            fingerprints = (
                [message_fingerprint(state.incident.summary)]
                if state.incident.summary
                else []
            )
            record = ConversationIncident(
                sequence=len(state.incidents) + 1,
                queue_status=IncidentQueueStatus.ACTIVE,
                incident=state.incident.model_copy(deep=True),
                message_fingerprints=fingerprints,
            )
            state.incidents.append(record)
            state.active_incident_id = record.id

    @staticmethod
    def _sync_active_incident(state: ConversationState) -> None:
        CyberSaathiService._ensure_active_incident(state)
        if state.active_incident_id is None and state.incident.summary:
            CyberSaathiService._ensure_active_incident(state)
        for record in state.incidents:
            if record.id == state.active_incident_id:
                record.queue_status = IncidentQueueStatus.ACTIVE
                record.incident = state.incident.model_copy(deep=True)
                return

    @staticmethod
    def _active_record(state: ConversationState) -> ConversationIncident | None:
        CyberSaathiService._ensure_active_incident(state)
        return next(
            (record for record in state.incidents if record.id == state.active_incident_id),
            None,
        )

    @staticmethod
    def _looks_like_new_incident(
        state: ConversationState, message: str, understanding: UnderstandingResult
    ) -> bool:
        if not state.incident.summary:
            return False
        lowered = normalized_text(message)
        if any(marker in lowered for marker in SAME_INCIDENT_MARKERS):
            return False
        # While a structured question is pending, repeated short answers such
        # as "no", "not provided", or "pata nahi" answer that question. Their
        # repeated fingerprint must not be mistaken for a duplicate incident.
        if (
            state.pending_question is not None
            and state.pending_question.incident_id == state.active_incident_id
            and not any(marker in lowered for marker in NEW_SUBJECT_MARKERS)
            and (
                understanding.crime_domain in {CrimeDomain.UNKNOWN, CrimeDomain.OTHER}
                or understanding.crime_domain == state.incident.crime_domain
                or _domains_may_share_incident(
                    understanding.crime_domain, state.incident.crime_domain
                )
            )
        ):
            return False
        if find_matching_incident(state, message, understanding) is not None:
            return True
        if CyberSaathiService._is_progress_followup(state, message):
            return False
        if any(marker in lowered for marker in NEW_SUBJECT_MARKERS):
            return True
        return (
            understanding.crime_domain not in {CrimeDomain.UNKNOWN, CrimeDomain.OTHER}
            and understanding.crime_domain != state.incident.crime_domain
            and not _domains_may_share_incident(
                understanding.crime_domain, state.incident.crime_domain
            )
            and len(message.split()) >= 6
        )

    @staticmethod
    def _incident_from_understanding(
        message: str, understanding: UnderstandingResult
    ) -> IncidentState:
        pending = any(entity.requires_confirmation for entity in understanding.entities)
        return IncidentState(
            status=IncidentStatus.AWAITING_CONFIRMATION if pending else IncidentStatus.IDENTIFIED,
            intent=(
                understanding.intent
                if understanding.intent != Intent.UNKNOWN
                else Intent.SEEK_GUIDANCE
            ),
            crime_domain=understanding.crime_domain,
            related_domains=CyberSaathiService._related_domains(
                message,
                understanding.crime_domain,
            ),
            urgency=understanding.urgency,
            sentiment=understanding.sentiment,
            language=understanding.language,
            response_language=understanding.response_language,
            confidence=understanding.confidence,
            entities=understanding.entities,
            summary=message.strip(),
            occurred_recently=understanding.urgency in {Urgency.HIGH, Urgency.CRITICAL},
            needs_clarification=understanding.needs_clarification,
        )

    @staticmethod
    def _merge_incident_detail(
        state: ConversationState,
        message: str,
        understanding: UnderstandingResult,
    ) -> None:
        """Merge a follow-up without erasing the active incident's established facts."""
        record = CyberSaathiService._active_record(state)
        prior_domain = state.incident.crime_domain
        normalized_message = normalized_text(message)
        denies_money_loss = any(
            marker in normalized_message for marker in MONEY_LOSS_DENIAL_MARKERS
        )
        if (
            understanding.crime_domain == CrimeDomain.FINANCIAL_FRAUD
            and not denies_money_loss
            and prior_domain
            in {
                CrimeDomain.PHISHING_SCAM,
                CrimeDomain.ACCOUNT_COMPROMISE,
                CrimeDomain.IMPERSONATION,
                CrimeDomain.MALWARE,
            }
        ):
            state.incident.crime_domain = CrimeDomain.FINANCIAL_FRAUD
            if prior_domain not in state.incident.related_domains:
                state.incident.related_domains.append(prior_domain)
        for related in CyberSaathiService._related_domains(
            message,
            state.incident.crime_domain,
        ):
            if related not in state.incident.related_domains:
                state.incident.related_domains.append(related)
        fingerprint = message_fingerprint(message)
        already_seen = bool(record and fingerprint in record.message_fingerprints)
        if record is not None and not already_seen:
            record.message_fingerprints = [
                *record.message_fingerprints[-29:],
                fingerprint,
            ]

        if not already_seen:
            current_summary = state.incident.summary or ""
            detail = message.strip()
            if detail and detail.casefold() not in current_summary.casefold():
                state.incident.summary = _compact_incident_summary(
                    current_summary, detail
                )

        known_entities = {
            (entity.type, entity.normalized_value or entity.value.casefold())
            for entity in state.incident.entities
        }
        for entity in understanding.entities:
            key = (entity.type, entity.normalized_value or entity.value.casefold())
            if key not in known_entities:
                state.incident.entities.append(entity)
                known_entities.add(key)

        urgency_rank = {
            Urgency.LOW: 0,
            Urgency.MEDIUM: 1,
            Urgency.HIGH: 2,
            Urgency.CRITICAL: 3,
        }
        if urgency_rank[understanding.urgency] > urgency_rank[state.incident.urgency]:
            state.incident.urgency = understanding.urgency
        state.incident.sentiment = understanding.sentiment
        state.incident.language = understanding.language
        state.incident.response_language = understanding.response_language
        state.incident.confidence = max(
            state.incident.confidence, understanding.confidence
        )
        state.incident.needs_clarification = False
        if any(
            entity.requires_confirmation and not entity.confirmed
            for entity in state.incident.entities
        ):
            state.incident.status = IncidentStatus.AWAITING_CONFIRMATION

    @staticmethod
    def _related_domains(message: str, primary: CrimeDomain) -> list[CrimeDomain]:
        text = normalized_text(message)
        related: list[CrimeDomain] = []

        def include(domain: CrimeDomain) -> None:
            if domain != primary and domain not in related:
                related.append(domain)

        if any(
            marker in text
            for marker in (
                "fake police", "fake officer", "cyber police", "nakli police",
                "digital arrest", "government call", "govt call", "ayushman",
                "arogya department", "नकली पुलिस", "अधिकारी बनकर",
            )
        ):
            include(CrimeDomain.IMPERSONATION)
        if any(marker in text for marker in ("link", "phishing", "फिशिंग", "लिंक")):
            include(CrimeDomain.PHISHING_SCAM)
            if any(
                marker in text
                for marker in (
                    "password", "otp", "pin", "credential", "cannot log in",
                    "login nahi", "पासवर्ड", "लॉगिन",
                )
            ):
                include(CrimeDomain.ACCOUNT_COMPROMISE)
        if any(
            marker in text
            for marker in ("apk", "malware", "remote access", "screen sharing", "वायरस")
        ):
            include(CrimeDomain.MALWARE)
        if primary in {
            CrimeDomain.CHILD_SAFETY,
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
        }:
            include(CrimeDomain.ONLINE_HARASSMENT)
        if primary == CrimeDomain.CHILD_SAFETY:
            include(CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY)
        return related[:4]

    @staticmethod
    def _queue_new_incident(
        state: ConversationState, message: str, understanding: UnderstandingResult
    ) -> RoutedReply:
        CyberSaathiService._ensure_active_incident(state)
        if len(state.incidents) >= 10:
            return RoutedReply(
                "This conversation already contains 10 incidents. Please start a new conversation so none of the details are mixed.",
                TurnKind.MESSAGE,
            )
        record = ConversationIncident(
            sequence=len(state.incidents) + 1,
            queue_status=IncidentQueueStatus.QUEUED,
            incident=CyberSaathiService._incident_from_understanding(message, understanding),
            message_fingerprints=[message_fingerprint(message)],
        )
        state.incidents.append(record)
        active = CyberSaathiService._active_record(state)
        active_number = active.sequence if active is not None else 1
        domain_label = record.incident.crime_domain.value.replace("_", " ")
        question = CyberSaathiService._focused_question(state.incident.crime_domain, state.language)
        copy = {
            LanguageCode.EN: f"I detected a separate incident #{record.sequence} ({domain_label}) and saved it in this chat. We are still working on incident #{active_number} so its details do not get mixed. {question}",
            LanguageCode.HI: f"मैंने अलग घटना #{record.sequence} ({domain_label}) पहचानकर इस चैट में सुरक्षित कर ली है। विवरण न मिलें इसलिए अभी घटना #{active_number} पूरी करते हैं। {question}",
            LanguageCode.HINGLISH: f"Maine separate incident #{record.sequence} ({domain_label}) detect karke is chat mein save kar liya hai. Details mix na hon, isliye pehle incident #{active_number} complete karte hain. {question}",
        }
        return RoutedReply(copy.get(state.language, copy[LanguageCode.EN]), TurnKind.MESSAGE)

    @staticmethod
    def _route_duplicate_incident(
        state: ConversationState, matching: ConversationIncident
    ) -> RoutedReply:
        active = CyberSaathiService._active_record(state)
        active_number = active.sequence if active is not None else matching.sequence
        copy = {
            LanguageCode.EN: (
                f"This matches incident #{matching.sequence} already saved in this chat, so I did not create another incident. "
                f"We are still working on incident #{active_number}; you can say ‘move to incident #{matching.sequence}’ after it is ready."
            ),
            LanguageCode.HI: (
                f"यह इसी चैट में सुरक्षित घटना #{matching.sequence} से मेल खाता है, इसलिए नई घटना नहीं बनाई गई। "
                f"अभी घटना #{active_number} पर काम चल रहा है; इसके तैयार होने के बाद ‘घटना #{matching.sequence} पर जाएं’ कहें।"
            ),
            LanguageCode.HINGLISH: (
                f"Ye already saved incident #{matching.sequence} se match karta hai, isliye naya incident create nahi kiya. "
                f"Abhi incident #{active_number} par kaam chal raha hai; ready hone ke baad ‘incident #{matching.sequence} par chalo’ bol sakte hain."
            ),
        }
        return RoutedReply(copy.get(state.language, copy[LanguageCode.EN]), TurnKind.MESSAGE)

    @staticmethod
    def _refresh_report_preparation(state: ConversationState) -> None:
        record = CyberSaathiService._active_record(state)
        if record is not None:
            record.report_preparation = build_report_preparation(state, record)

    @staticmethod
    def _apply_report_readiness(state: ConversationState) -> None:
        # Availability for typed, non-report workflows is independent from the
        # incident report packet. Report-readiness rules must not erase these
        # action contracts after routing.
        if state.handoff is not None and state.handoff.target != HandoffTarget.REPORT_CRIME:
            return
        record = CyberSaathiService._active_record(state)
        if record is None:
            state.handoff = None
            return
        pending = any(
            entity.requires_confirmation and not entity.confirmed
            for entity in state.incident.entities
        )
        if pending:
            state.handoff = None
            state.incident.status = IncidentStatus.AWAITING_CONFIRMATION
            return
        # A handoff is exposed only after the citizen explicitly prepares the
        # redacted draft. Safety progress, a report-mode click, or an inferred
        # report intent must never skip the visible packet/draft stage.
        draft_prepared = record.report_preparation.draft_prepared
        if not draft_prepared or state.incident.crime_domain in {CrimeDomain.UNKNOWN, CrimeDomain.OTHER}:
            state.handoff = None
            # A report request without a recognised incident must keep the
            # dialogue open for one meaningful clarification; it must not look
            # as though the request was completed or silently discarded.
            if record.report_preparation.packet_ready:
                state.incident.status = IncidentStatus.AWAITING_USER_INPUT
            elif state.incident.status in {
                IncidentStatus.READY_TO_REPORT,
                IncidentStatus.IDENTIFIED,
            }:
                state.incident.status = IncidentStatus.AWAITING_USER_INPUT
            return
        # A formal report is deliberately editable. Optional fields such as a
        # UTR, provider, or an attachment must not hide the route into that
        # form; only unconfirmed high-impact values block the handoff.
        state.incident.status = (
            IncidentStatus.READY_TO_REPORT
            if record.report_preparation.ready_for_review
            else IncidentStatus.AWAITING_USER_INPUT
        )
        state.handoff = CyberSaathiService._report_handoff(state)

    @staticmethod
    def _prepare_report(
        state: ConversationState,
        *,
        prepare_draft: bool = False,
    ) -> RoutedReply:
        record = CyberSaathiService._active_record(state)
        if record is None:
            return RoutedReply(CyberSaathiService._copy(state.language, "clarify"), TurnKind.MESSAGE)
        record.report_preparation.packet_ready = True
        if prepare_draft:
            record.report_preparation.draft_prepared = True
            # Selecting Prepare report is explicit consent to retain the
            # redacted workflow draft on the server for resumption.
            state.storage_consent = True
        record.report_preparation = build_report_preparation(state, record)
        state.pending_confirmation_entity_ids = [
            entity.id
            for entity in state.incident.entities
            if entity.requires_confirmation and not entity.confirmed
        ]
        state.handoff = None
        if (
            not prepare_draft
            and not state.pending_confirmation_entity_ids
            and CyberSaathiService._needs_optional_suspect_question(state)
        ):
            CyberSaathiService._set_pending_question(
                state,
                "optional_suspect_details",
                ExpectedAnswerType.FREE_TEXT,
            )
            state.incident.status = IncidentStatus.AWAITING_USER_INPUT
            return RoutedReply(
                CyberSaathiService._question_copy("optional_suspect_details", state.language),
                TurnKind.MESSAGE,
                GroundingStatus.DETERMINISTIC_PLAYBOOK,
            )
        missing = record.report_preparation.missing_required_keys
        if "affected_person" in missing:
            copy = {
                LanguageCode.EN: "I have prepared the report checklist below. One required detail is still unclear: did this happen to you, your child, or someone else?",
                LanguageCode.HI: "मैंने नीचे रिपोर्ट सूची तैयार कर दी है। एक जरूरी बात स्पष्ट नहीं है: यह आपके साथ, आपके बच्चे के साथ, या किसी और के साथ हुआ?",
                LanguageCode.HINGLISH: "Maine report checklist neeche ready kar di hai. Ek required detail clear nahi hai: ye aapke saath, aapke child ke saath, ya kisi aur ke saath hua?",
            }
        elif missing:
            copy = {
                LanguageCode.EN: "I have prepared the report checklist below. Please provide the missing required detail or attach supporting evidence; I will update the packet without repeating earlier guidance.",
                LanguageCode.HI: "मैंने नीचे रिपोर्ट सूची तैयार कर दी है। बाकी जरूरी जानकारी दें या प्रमाण जोड़ें; मैं पुराना मार्गदर्शन दोहराए बिना पैकेट अपडेट करूंगा।",
                LanguageCode.HINGLISH: "Maine report checklist neeche ready kar di hai. Missing required detail dein ya evidence attach karein; main purani guidance repeat kiye bina packet update karunga.",
            }
        else:
            copy = {
                LanguageCode.EN: "Good. I have prepared the incident packet and checklist below. Review the extracted details, add any available PDF or image evidence, then choose the reporting mode to continue to the editable form.",
                LanguageCode.HI: "ठीक है। मैंने नीचे घटना पैकेट और सूची तैयार कर दी है। निकाली गई जानकारी जांचें, उपलब्ध PDF या चित्र प्रमाण जोड़ें, फिर संपादन योग्य फॉर्म पर जाने के लिए रिपोर्टिंग मोड चुनें।",
                LanguageCode.HINGLISH: "Good. Incident packet aur checklist neeche ready hai. Extracted details review karein, available PDF/image evidence add karein, phir editable form ke liye reporting mode choose karein.",
            }
        if prepare_draft and not state.pending_confirmation_entity_ids:
            state.handoff = CyberSaathiService._report_handoff(state)
            state.incident.status = IncidentStatus.READY_TO_REPORT
            prepared = {
                LanguageCode.EN: "The redacted report draft is saved. Use Review and edit report to verify every prefilled field before final submission.",
                LanguageCode.HI: "संपादित रिपोर्ट ड्राफ्ट सुरक्षित हो गया है। अंतिम सबमिशन से पहले हर भरी हुई जानकारी जांचने के लिए रिपोर्ट की समीक्षा और संपादन खोलें।",
                LanguageCode.HINGLISH: "Redacted report draft save ho gaya hai. Final submit se pehle har prefilled field check karne ke liye Review and edit report kholein.",
            }
            return RoutedReply(
                prepared.get(state.language, prepared[LanguageCode.EN]),
                TurnKind.HANDOFF,
            )
        return RoutedReply(
            copy.get(state.language, copy[LanguageCode.EN]),
            TurnKind.MESSAGE,
        )

    @staticmethod
    def _route_blocked_action(
        state: ConversationState,
        message: str,
        understanding: UnderstandingResult,
    ) -> RoutedReply:
        record = CyberSaathiService._active_record(state)
        if record is None:
            return RoutedReply(CyberSaathiService._copy(state.language, "clarify"), TurnKind.MESSAGE)
        action = blocked_action(message)
        record.blocked_actions[action] = record.blocked_actions.get(action, 0) + 1
        total_failures = sum(record.blocked_actions.values())
        escalated = total_failures >= 5
        if escalated:
            state.incident.urgency = Urgency.CRITICAL

        alternatives = CyberSaathiService._blocked_action_copy(
            state.language,
            action,
            state.incident.crime_domain,
            escalated,
        )
        effective = understanding.model_copy(
            update={"crime_domain": state.incident.crime_domain}
        )
        retrieval = CyberSaathiService._retrieve_knowledge(
            f"{state.incident.summary or ''} Alternative when {action} is unavailable. {message}",
            effective,
            state,
        )
        if retrieval.matches:
            generated = get_llm_gateway().generate(
                state=state,
                user_message=message,
                knowledge_context=retrieval.bounded_context,
                source_ids=[match.chunk_id for match in retrieval.matches],
                deterministic_playbook=alternatives,
            )
            if generated.response is not None:
                cited = set(generated.response.sources)
                matches = [match for match in retrieval.matches if match.chunk_id in cited]
                return RoutedReply(
                    generated.response.answer,
                    TurnKind.SAFETY if escalated else TurnKind.MESSAGE,
                    GroundingStatus.GROUNDED,
                    CyberSaathiService._conversation_sources(matches),
                    retrieval.retrieval_latency_ms,
                    generated.provider,
                    generated.model,
                    generated.fallback_used,
                    generated.latency_ms,
                    [flag[:80] for flag in generated.response.safety_flags],
                )
        return RoutedReply(
            alternatives,
            TurnKind.SAFETY if escalated else TurnKind.MESSAGE,
            GroundingStatus.DETERMINISTIC_GROUNDED if retrieval.matches else GroundingStatus.DETERMINISTIC_PLAYBOOK,
            CyberSaathiService._conversation_sources(retrieval.matches[:1]),
            retrieval.retrieval_latency_ms,
            safety_flags=["blocked_action_alternative"] + (["repeated_failure_escalation"] if escalated else []),
        )

    @staticmethod
    def add_attachment(
        conversation_id: UUID,
        state: ConversationState,
        analysis: AttachmentAnalysis,
    ) -> ConversationResponse:
        next_state = state.model_copy(deep=True)
        if next_state.id != conversation_id:
            raise APIError(
                status_code=409,
                code="CONVERSATION_STATE_MISMATCH",
                message="Conversation state does not match this conversation.",
            )
        record = CyberSaathiService._active_record(next_state)
        if record is None:
            raise APIError(
                status_code=409,
                code="INCIDENT_REQUIRED",
                message="Describe the incident before attaching evidence.",
            )
        analysis = CyberSaathiService._assess_attachment_relevance(
            next_state.incident, analysis
        )
        if analysis.relevance_status == "rejected":
            raise APIError(
                status_code=422,
                code="EVIDENCE_NOT_RELEVANT",
                message="This file appears unrelated to the current incident. Attach incident evidence, not a resume or unrelated document.",
            )
        if any(item.checksum == analysis.checksum for item in record.report_preparation.attachments):
            acknowledgement = {
                LanguageCode.EN: "This file is already attached to the current incident; I did not add a duplicate.",
                LanguageCode.HI: "यह फाइल मौजूदा घटना में पहले से जुड़ी है; मैंने इसकी दूसरी प्रति नहीं जोड़ी।",
                LanguageCode.HINGLISH: "Ye file current incident mein already attached hai; duplicate add nahi kiya.",
            }
        else:
            if len(record.report_preparation.attachments) >= 10:
                raise APIError(
                    status_code=422,
                    code="ATTACHMENT_LIMIT_REACHED",
                    message="A Cyber Saathi incident can hold at most 10 attachments before report review.",
                )
            record.report_preparation.attachments.append(analysis)
            existing = {
                (entity.type, entity.normalized_value or entity.value.casefold())
                for entity in next_state.incident.entities
            }
            for entity in analysis.extracted_entities:
                key = (entity.type, entity.normalized_value or entity.value.casefold())
                if key not in existing:
                    next_state.incident.entities.append(entity)
                    existing.add(key)
                    if entity.requires_confirmation:
                        next_state.pending_confirmation_entity_ids.append(entity.id)
            acknowledgement = {
                LanguageCode.EN: f"Added {analysis.file_name} to the report packet. I extracted only basic file information; please review any detected values before they enter the report.",
                LanguageCode.HI: f"{analysis.file_name} रिपोर्ट पैकेट में जोड़ दी गई है। मैंने केवल मूल फाइल जानकारी निकाली है; रिपोर्ट में जाने से पहले मिली हुई जानकारी जांचें।",
                LanguageCode.HINGLISH: f"{analysis.file_name} report packet mein add ho gayi. Maine sirf basic file info extract ki hai; report mein use hone se pehle detected values review karein.",
            }
        record.report_preparation = build_report_preparation(next_state, record)
        CyberSaathiService._apply_report_readiness(next_state)
        next_state.turns.extend(
            (
                ConversationTurn(
                    role="user",
                    content=f"[Attachment: {analysis.file_name}]",
                    language=next_state.language,
                    purpose=TurnPurpose.SAME_INCIDENT_DETAIL,
                ),
                ConversationTurn(
                    role="assistant",
                    content=acknowledgement.get(next_state.language, acknowledgement[LanguageCode.EN]),
                    language=next_state.language,
                    purpose=TurnPurpose.SAME_INCIDENT_DETAIL,
                ),
            )
        )
        CyberSaathiService._sync_active_incident(next_state)
        next_state.last_turn_purpose = TurnPurpose.SAME_INCIDENT_DETAIL
        next_state.updated_at = datetime.now(timezone.utc)
        return ConversationResponse(state=next_state)

    @staticmethod
    def _assess_attachment_relevance(
        incident: IncidentState,
        analysis: AttachmentAnalysis,
    ) -> AttachmentAnalysis:
        preview = normalized_text(analysis.extracted_text_preview or "")
        if not preview:
            return analysis.model_copy(update={"relevance_status": "uncertain"})
        resume_markers = (
            "curriculum vitae", "work experience", "employment history",
            "professional experience", "education", "resume",
        )
        resume_score = sum(marker in preview for marker in resume_markers)
        incident_tokens = {
            token for token in normalized_text(incident.summary or "").split() if len(token) >= 4
        }
        preview_tokens = set(preview.split())
        if resume_score >= 2 and len(incident_tokens & preview_tokens) < 2:
            return analysis.model_copy(update={"relevance_status": "rejected"})
        domain_terms = {
            CrimeDomain.FINANCIAL_FRAUD: {"bank", "payment", "transaction", "upi", "amount", "debited"},
            CrimeDomain.ECOMMERCE_FRAUD: {"order", "seller", "delivery", "refund", "invoice"},
            CrimeDomain.PHISHING_SCAM: {"link", "otp", "password", "login", "kyc"},
            CrimeDomain.ONLINE_HARASSMENT: {"message", "profile", "threat", "harassment", "username"},
            CrimeDomain.CHILD_SAFETY: {"message", "profile", "child", "minor", "morphed"},
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY: {"message", "profile", "child", "minor", "morphed"},
        }.get(incident.crime_domain, set())
        relevant = bool((incident_tokens & preview_tokens) or (domain_terms & preview_tokens))
        return analysis.model_copy(
            update={"relevance_status": "relevant" if relevant else "uncertain"}
        )

    @staticmethod
    def _activate_next_incident(state: ConversationState) -> RoutedReply:
        active = CyberSaathiService._active_record(state)
        queued = next(
            (
                record
                for record in state.incidents
                if record.queue_status == IncidentQueueStatus.QUEUED
            ),
            None,
        )
        if queued is None:
            return RoutedReply(
                CyberSaathiService._copy(state.language, "no_queued_incident"),
                TurnKind.MESSAGE,
            )
        if active is not None and state.incident.status not in {
            IncidentStatus.READY_TO_REPORT,
            IncidentStatus.REPORT_COMPLETED,
            IncidentStatus.RESOLVED,
        }:
            return RoutedReply(
                CyberSaathiService._copy(state.language, "finish_active_first")
                + " "
                + CyberSaathiService._focused_question(
                    state.incident.crime_domain, state.language
                ),
                TurnKind.MESSAGE,
            )
        if active is not None:
            active.queue_status = IncidentQueueStatus.COMPLETED
            active.incident = state.incident.model_copy(deep=True)
        queued.queue_status = IncidentQueueStatus.ACTIVE
        state.active_incident_id = queued.id
        state.incident = queued.incident.model_copy(deep=True)
        state.pending_confirmation_entity_ids = [
            entity.id
            for entity in state.incident.entities
            if entity.requires_confirmation and not entity.confirmed
        ]
        state.handoff = None
        return RoutedReply(
            CyberSaathiService._copy(state.language, "activated_incident").format(
                number=queued.sequence,
                domain=queued.incident.crime_domain.value.replace("_", " "),
            )
            + " "
            + CyberSaathiService._focused_question(
                queued.incident.crime_domain, state.language
            ),
            TurnKind.MESSAGE,
        )

    @staticmethod
    def _revise_pending_entities(
        state: ConversationState, replacements: list[Entity]
    ) -> RoutedReply:
        pending_types = {
            entity.type
            for entity in state.incident.entities
            if entity.id in set(state.pending_confirmation_entity_ids)
        }
        applicable = [entity for entity in replacements if entity.type in pending_types]
        if not applicable:
            return RoutedReply(
                CyberSaathiService._confirmation_copy(
                    state.language,
                    [
                        entity
                        for entity in state.incident.entities
                        if entity.id in set(state.pending_confirmation_entity_ids)
                    ],
                ),
                TurnKind.CONFIRMATION,
            )
        replacement_types = {entity.type for entity in applicable}
        untouched_pending = [
            entity
            for entity in state.incident.entities
            if entity.id in set(state.pending_confirmation_entity_ids)
            and entity.type not in replacement_types
        ]
        state.incident.entities = [
            entity
            for entity in state.incident.entities
            if entity.type not in replacement_types
        ] + applicable
        pending_entities = untouched_pending + applicable
        state.pending_confirmation_entity_ids = [entity.id for entity in pending_entities]
        state.incident.status = IncidentStatus.AWAITING_CONFIRMATION
        CyberSaathiService._set_pending_question(
            state,
            "confirm_entities",
            ExpectedAnswerType.CONFIRM_ENTITIES,
        )
        return RoutedReply(
            CyberSaathiService._copy(state.language, "updated_detail")
            + " "
            + CyberSaathiService._confirmation_copy(state.language, pending_entities),
            TurnKind.CONFIRMATION,
        )

    @staticmethod
    def _is_progress_followup(state: ConversationState, message: str) -> bool:
        if not state.incident.summary:
            return False
        lowered = normalized_text(message)
        contextual_answer = (
            state.pending_question is not None
            and state.pending_question.answer_type == ExpectedAnswerType.YES_NO
            and state.pending_question.key in {"bank_contact", "bank_contact_and_protect"}
            and CyberSaathiService._is_contextual_confirmation(message)
        )
        return (
            contextual_answer
            or any(marker in lowered for marker in BANK_CONTACT_MARKERS)
            or any(marker in lowered for marker in BANK_PROTECTION_MARKERS)
            or any(marker in lowered for marker in ALL_DONE_MARKERS)
            or any(marker in lowered for marker in ("what next", "ab kya", "now what"))
        )

    @staticmethod
    def _route_progress_followup(
        state: ConversationState, message: str, understanding: UnderstandingResult
    ) -> RoutedReply:
        lowered = normalized_text(message)
        record = CyberSaathiService._active_record(state)
        actions = record.completed_actions if record is not None else []
        all_done = any(marker in lowered for marker in ALL_DONE_MARKERS)
        bank_contacted, bank_protected = CyberSaathiService._financial_action_signals(
            state, message
        )
        if state.pending_question is not None:
            state.pending_question.last_answer = message.strip()[:500]
        # A progress update can contain fresh report facts too (for example, a
        # transaction reference in the same message as "I contacted my bank").
        # Merge it before the report packet is checked; otherwise those facts
        # appear to be ignored until the user repeats them.
        CyberSaathiService._merge_incident_detail(state, message, understanding)
        if bank_contacted and "bank_contacted" not in actions:
            actions.append("bank_contacted")
        if bank_protected and "bank_protection_requested" not in actions:
            actions.append("bank_protection_requested")
        if all_done:
            for action in ("bank_contacted", "evidence_preserved", "urgent_report_considered"):
                if action not in actions:
                    actions.append(action)
            # "All done" is an explicit request to move from advice into the
            # report workflow. It is not enough to mark the incident ready if
            # the later readiness gate cannot tell that the user wants a report.
            state.incident.intent = Intent.REPORT_INCIDENT
            state.incident.status = IncidentStatus.READY_TO_REPORT
            state.pending_confirmation_entity_ids = []
            if state.incident.crime_domain == CrimeDomain.ECOMMERCE_FRAUD:
                state.handoff = None
                playbook = CyberSaathiService._copy(
                    state.language, "ecommerce_all_done_next"
                )
            else:
                state.handoff = CyberSaathiService._report_handoff(state)
                playbook = CyberSaathiService._copy(state.language, "all_done_next")
        elif bank_contacted:
            playbook = CyberSaathiService._copy(state.language, "bank_contacted_next")
        else:
            if state.pending_question is not None:
                playbook = CyberSaathiService._question_copy(
                    state.pending_question.key, state.language
                )
            else:
                playbook = CyberSaathiService._progress_copy(
                    state.incident.crime_domain, state.language
                )

        CyberSaathiService._sync_active_incident(state)
        CyberSaathiService._refresh_report_preparation(state)
        record = CyberSaathiService._active_record(state)
        preparation = record.report_preparation if record is not None else None

        augmented = f"{state.incident.summary or ''} Follow-up: {message}"
        effective = understanding.model_copy(
            update={"crime_domain": state.incident.crime_domain}
        )
        retrieval = CyberSaathiService._retrieve_knowledge(augmented, effective, state)
        # Retrieval still cross-checks every follow-up and supplies the source
        # card. The report readiness copy itself is deliberately deterministic:
        # an LLM must not replace missing-field instructions with generic advice.
        content = (
            CyberSaathiService._financial_followup_question(
                state,
                preparation,
                bank_contacted=bank_contacted,
                bank_protected=bank_protected,
                fallback_playbook=playbook,
            )
            if state.incident.crime_domain == CrimeDomain.FINANCIAL_FRAUD
            else playbook
        )
        return RoutedReply(
            content,
            TurnKind.MESSAGE,
            GroundingStatus.DETERMINISTIC_GROUNDED if retrieval.matches else GroundingStatus.DETERMINISTIC_PLAYBOOK,
            CyberSaathiService._conversation_sources(retrieval.matches[:1]),
            retrieval_latency_ms=retrieval.retrieval_latency_ms,
        )

    @staticmethod
    def _financial_action_signals(
        state: ConversationState, message: str
    ) -> tuple[bool, bool]:
        """Interpret natural completion language against the stored question."""
        lowered = normalized_text(message)
        pending_key = state.pending_question.key if state.pending_question is not None else None
        contextual_yes = CyberSaathiService._is_contextual_confirmation(message)
        # A generic contextual yes proves only the action that was actually
        # pending. Explicit block/freeze wording can prove protection directly.
        bank_protected = any(marker in lowered for marker in BANK_PROTECTION_MARKERS) or (
            contextual_yes and pending_key == "bank_protection"
        )
        bank_contacted = bank_protected or any(
            marker in lowered for marker in BANK_CONTACT_MARKERS
        ) or (
            contextual_yes
            and pending_key in {"bank_contact", "bank_contact_and_protect"}
        )
        return bank_contacted, bank_protected

    @staticmethod
    def _financial_followup_question(
        state: ConversationState,
        preparation,
        *,
        bank_contacted: bool,
        bank_protected: bool,
        fallback_playbook: str,
    ) -> str:
        """Advance a financial-fraud conversation by one concrete user action."""
        if preparation is None:
            return fallback_playbook
        if bank_protected:
            CyberSaathiService._set_pending_question(
                state,
                "transaction_reference_or_evidence",
                ExpectedAnswerType.IDENTIFIER_OR_EVIDENCE,
            )
        elif bank_contacted:
            CyberSaathiService._set_pending_question(
                state,
                "bank_protection",
                ExpectedAnswerType.YES_NO,
            )
        else:
            CyberSaathiService._set_pending_question(
                state,
                "bank_contact_and_protect",
                ExpectedAnswerType.YES_NO,
            )
        if state.language == LanguageCode.HI:
            if bank_protected:
                return "1. बैंक की कार्रवाई दर्ज हो गई है।\n2. अब उपलब्ध transaction/UTR/reference number या payment screenshot/statement जोड़ें।\n3. बाकी जानकारी रिपोर्ट फॉर्म में संपादित की जा सकेगी—क्या आपके पास transaction reference या payment proof है?"
            if bank_contacted:
                return "1. बैंक से संपर्क करना दर्ज हो गया है।\n2. उनसे outgoing transactions रोकने और इस भुगतान को fraud के रूप में दर्ज करने को कहें।\n3. क्या बैंक ने कोई reference number दिया या account protection action लिया?"
            return "1. पहले बैंक/UPI provider के official app, card-back number या website से unauthorized payment report करें।\n2. outgoing transactions रोकने के लिए कहें; कॉलर का दिया नंबर इस्तेमाल न करें।\n3. हो जाने पर बताएं: बैंक ने protection action लिया या नहीं?"
        if state.language == LanguageCode.HINGLISH:
            if bank_protected:
                return "1. Bank wala action record ho gaya hai.\n2. Ab jo transaction/UTR/reference number ya payment screenshot/statement available ho, add karein.\n3. Baaki details report form mein edit kar sakte hain—transaction reference ya payment proof hai?"
            if bank_contacted:
                return "1. Bank se contact karna record ho gaya hai.\n2. Unse outgoing transactions block karne aur payment ko fraud ke taur par note karne ko boliye.\n3. Bank ne koi reference number diya ya account protection action liya?"
            return "1. Pehle bank/UPI provider ke official app, card-back number ya website se unauthorized payment report karein.\n2. Outgoing transactions block karne ko boliye; caller ka diya number use na karein.\n3. Ho jaye to batayein: bank ne protection action liya ya nahi?"
        if bank_protected:
            return "1. The bank action is recorded.\n2. Add any transaction/UTR/reference number or payment screenshot/statement you have.\n3. You can edit remaining details in the report form—do you have a transaction reference or payment proof?"
        if bank_contacted:
            return "1. Your bank contact is recorded.\n2. Ask the official bank channel to block outgoing transactions and mark the payment as fraud.\n3. Did the bank give a reference number or take an account-protection action?"
        return "1. Report the unauthorized payment through your bank or UPI provider's official app, card-back number, or website.\n2. Ask it to block outgoing transactions; do not use a number supplied by the caller.\n3. When this is done, tell me whether the bank took a protection action."

    @staticmethod
    def _route_mock_message(
        state: ConversationState, message: str, understanding: UnderstandingResult
    ) -> RoutedReply:
        language = state.language

        if understanding.intent == Intent.TRACK_REPORT:
            state.incident = IncidentState(
                status=IncidentStatus.TRACKING_REQUESTED,
                intent=Intent.TRACK_REPORT,
                language=language,
                confidence=0.9,
            )
            state.handoff = WorkflowHandoff(
                target=HandoffTarget.TRACK_COMPLAINT,
                reporting_mode=state.reporting_mode,
                route="/complaints/track",
            )
            return RoutedReply(CyberSaathiService._copy(language, "track"), TurnKind.HANDOFF)

        workflow_handoffs = {
            Intent.CYBER_WARRIOR: (
                HandoffTarget.CYBER_WARRIOR,
                "/cyber-warrior",
                HandoffImplementationStatus.AVAILABLE,
                "cyber_warrior_handoff",
            ),
            Intent.GENERAL_AWARENESS: (
                HandoffTarget.LEARNING_RESOURCES,
                "/resources",
                HandoffImplementationStatus.AVAILABLE,
                "learning_resources_handoff",
            ),
            Intent.CHECK_IDENTIFIER: (
                HandoffTarget.SEARCH_SUSPECT_REPORTS,
                "/suspects/search",
                HandoffImplementationStatus.AVAILABLE,
                "search_suspect_handoff",
            ),
            Intent.EXPLORE_CYBER_RISK: (
                HandoffTarget.SECURE_INDIA,
                "/secure-india",
                HandoffImplementationStatus.AVAILABLE,
                "secure_india_handoff",
            ),
        }
        workflow_handoff = workflow_handoffs.get(understanding.intent)
        if workflow_handoff:
            target, route, implementation_status, copy_key = workflow_handoff
            state.handoff = WorkflowHandoff(
                target=target,
                reporting_mode=state.reporting_mode,
                route=route,
                implementation_status=implementation_status,
                identifier=(
                    CyberSaathiService._confirmed_suspect_identifier(state)
                    if target == HandoffTarget.SEARCH_SUSPECT_REPORTS
                    else None
                ),
            )
            return RoutedReply(
                CyberSaathiService._copy(language, copy_key), TurnKind.HANDOFF
            )

        continuing_incident = bool(
            state.incident.summary
            and state.incident.crime_domain not in {CrimeDomain.UNKNOWN, CrimeDomain.OTHER}
        )
        if continuing_incident:
            CyberSaathiService._merge_incident_detail(state, message, understanding)
            crime_domain = state.incident.crime_domain
            intent = (
                understanding.intent
                if understanding.intent != Intent.UNKNOWN
                else state.incident.intent
            )
            state.incident.intent = intent
            response_understanding = understanding.model_copy(
                update={
                    "crime_domain": crime_domain,
                    "intent": intent,
                    "needs_clarification": False,
                }
            )
        else:
            crime_domain = (
                understanding.crime_domain
                if understanding.crime_domain != CrimeDomain.UNKNOWN
                else state.incident.crime_domain
            )
            intent = (
                understanding.intent
                if understanding.intent != Intent.UNKNOWN
                else state.incident.intent
            )
            state.incident = CyberSaathiService._incident_from_understanding(
                message, understanding
            )
            state.incident.intent = intent
            state.incident.crime_domain = crime_domain
            response_understanding = understanding
        entities = state.incident.entities
        pending_entities = [
            entity
            for entity in entities
            if entity.requires_confirmation and not entity.confirmed
        ]
        state.pending_confirmation_entity_ids = [entity.id for entity in pending_entities]

        if crime_domain == CrimeDomain.FINANCIAL_FRAUD and not continuing_incident:
            state.incident = IncidentState(
                status=(
                    IncidentStatus.AWAITING_CONFIRMATION
                    if pending_entities
                    else IncidentStatus.URGENT
                ),
                intent=intent if intent != Intent.UNKNOWN else Intent.REPORT_INCIDENT,
                crime_domain=CrimeDomain.FINANCIAL_FRAUD,
                related_domains=CyberSaathiService._related_domains(
                    message,
                    CrimeDomain.FINANCIAL_FRAUD,
                ),
                urgency=understanding.urgency,
                sentiment=understanding.sentiment,
                language=understanding.language,
                response_language=understanding.response_language,
                confidence=understanding.confidence,
                entities=entities,
                summary=message.strip(),
                occurred_recently=understanding.urgency in {Urgency.HIGH, Urgency.CRITICAL},
                needs_clarification=understanding.needs_clarification,
            )
            state.handoff = None
            # Capture protection work already stated in the opening message so
            # confirmation advances to the next missing action instead of
            # asking the citizen to repeat that they contacted the bank.
            CyberSaathiService._sync_active_incident(state)
            bank_contacted, bank_protected = CyberSaathiService._financial_action_signals(
                state, message
            )
            record = CyberSaathiService._active_record(state)
            if record is not None:
                if bank_contacted and "bank_contacted" not in record.completed_actions:
                    record.completed_actions.append("bank_contacted")
                if (
                    bank_protected
                    and "bank_protection_requested" not in record.completed_actions
                ):
                    record.completed_actions.append("bank_protection_requested")
            safety = CyberSaathiService._with_sentiment_strategy(
                language,
                understanding.sentiment,
                CyberSaathiService._copy(language, "financial_safety"),
            )
            if pending_entities:
                CyberSaathiService._set_pending_question(
                    state,
                    (
                        "final_loss_amount"
                        if CyberSaathiService._has_ambiguous_pending_amounts(state)
                        else "confirm_entities"
                    ),
                    (
                        ExpectedAnswerType.FINAL_LOSS_AMOUNT
                        if CyberSaathiService._has_ambiguous_pending_amounts(state)
                        else ExpectedAnswerType.CONFIRM_ENTITIES
                    ),
                )
                safety += " " + CyberSaathiService._confirmation_copy(
                    language, pending_entities
                )
            retrieval = CyberSaathiService._retrieve_knowledge(message, understanding, state)
            return RoutedReply(
                safety,
                TurnKind.SAFETY,
                (
                    GroundingStatus.DETERMINISTIC_GROUNDED
                    if retrieval.matches
                    else GroundingStatus.DETERMINISTIC_PLAYBOOK
                ),
                CyberSaathiService._conversation_sources(retrieval.matches[:1]),
                retrieval.retrieval_latency_ms,
            )

        if (
            intent == Intent.REPORT_INCIDENT
            and crime_domain != CrimeDomain.ECOMMERCE_FRAUD
            and crime_domain not in DOMAIN_QUESTION_FLOWS
            and not understanding.needs_clarification
        ):
            state.incident.status = (
                IncidentStatus.AWAITING_CONFIRMATION
                if pending_entities
                else IncidentStatus.READY_TO_REPORT
            )
            state.handoff = None
            if pending_entities:
                CyberSaathiService._set_pending_question(
                    state,
                    "confirm_entities",
                    ExpectedAnswerType.CONFIRM_ENTITIES,
                )
                return RoutedReply(
                    CyberSaathiService._confirmation_copy(language, pending_entities),
                    TurnKind.CONFIRMATION,
                )
            return RoutedReply(CyberSaathiService._copy(language, "report"), TurnKind.HANDOFF)

        if not response_understanding.needs_clarification and (
            response_understanding.intent in {Intent.SEEK_GUIDANCE, Intent.GENERAL_AWARENESS}
            or crime_domain == CrimeDomain.ECOMMERCE_FRAUD
            or (
                response_understanding.confidence_band.value == "high"
                and crime_domain != CrimeDomain.UNKNOWN
            )
            or continuing_incident
        ):
            retrieval = CyberSaathiService._retrieve_knowledge(
                f"{state.incident.summary or ''} Current question: {message}",
                response_understanding,
                state,
            )
            if (
                crime_domain in DOMAIN_QUESTION_FLOWS
                and response_understanding.intent != Intent.GENERAL_AWARENESS
                and not CyberSaathiService._is_general_guidance_request(message)
            ):
                CyberSaathiService._infer_flow_answers_from_message(state, message)
                question = CyberSaathiService._next_domain_question(state)
                if question is not None:
                    state.incident.status = IncidentStatus.GUIDANCE_GIVEN
                    answer = question
                    if not continuing_incident:
                        answer = (
                            CyberSaathiService._domain_safety_copy(crime_domain, language)
                            + "\n"
                            + question
                        )
                    return RoutedReply(
                        CyberSaathiService._with_sentiment_strategy(
                            language, response_understanding.sentiment, answer
                        ),
                        TurnKind.MESSAGE,
                        (
                            GroundingStatus.DETERMINISTIC_GROUNDED
                            if retrieval.matches
                            else GroundingStatus.DETERMINISTIC_PLAYBOOK
                        ),
                        CyberSaathiService._conversation_sources(retrieval.matches[:1]),
                        retrieval.retrieval_latency_ms,
                    )
            if retrieval.matches:
                state.incident.status = IncidentStatus.GUIDANCE_GIVEN
                generated = get_llm_gateway().generate(
                    state=state,
                    user_message=message,
                    knowledge_context=retrieval.bounded_context,
                    source_ids=[match.chunk_id for match in retrieval.matches],
                    deterministic_playbook=CyberSaathiService._copy(
                        language, "guidance"
                    ),
                )
                if generated.response is not None:
                    cited = set(generated.response.sources)
                    cited_matches = [
                        match for match in retrieval.matches if match.chunk_id in cited
                    ]
                    return RoutedReply(
                        CyberSaathiService._ensure_focused_question(
                            generated.response.answer, crime_domain, language
                        ),
                        TurnKind.MESSAGE,
                        GroundingStatus.GROUNDED,
                        CyberSaathiService._conversation_sources(cited_matches),
                        retrieval.retrieval_latency_ms,
                        generated.provider,
                        generated.model,
                        generated.fallback_used,
                        generated.latency_ms,
                        [flag[:80] for flag in generated.response.safety_flags],
                    )
                # Knowledge is evidence for the response, not a document dump
                # for a stressed citizen. If every LLM provider is unavailable,
                # retain the citation metadata but ask the next useful question.
                answer = CyberSaathiService._focused_question(crime_domain, language)
                return RoutedReply(
                    CyberSaathiService._with_sentiment_strategy(
                        language, response_understanding.sentiment, answer
                    ),
                    TurnKind.MESSAGE,
                    GroundingStatus.DETERMINISTIC_GROUNDED,
                    CyberSaathiService._conversation_sources(retrieval.matches[:1]),
                    retrieval.retrieval_latency_ms,
                    llm_fallback_used=generated.fallback_used,
                    llm_latency_ms=generated.latency_ms,
                    safety_flags=["deterministic_grounded_fallback"],
                )
            # When verified retrieval has no sufficiently relevant chunk, use
            # the provider gateway for bounded conversational help. The
            # deterministic playbook remains the safety boundary and provider
            # failure still falls back to the explicit no-result response.
            deterministic_fallback = CyberSaathiService._domain_safety_copy(
                crime_domain, language
            )
            generated = get_llm_gateway().generate(
                state=state,
                user_message=message,
                knowledge_context="",
                source_ids=[],
                deterministic_playbook=deterministic_fallback,
            )
            if generated.response is not None:
                state.incident.status = IncidentStatus.GUIDANCE_GIVEN
                return RoutedReply(
                    CyberSaathiService._ensure_focused_question(
                        generated.response.answer, crime_domain, language
                    ),
                    TurnKind.MESSAGE,
                    GroundingStatus.NO_RESULT,
                    retrieval_latency_ms=retrieval.retrieval_latency_ms,
                    llm_provider=generated.provider,
                    llm_model=generated.model,
                    llm_fallback_used=generated.fallback_used,
                    llm_latency_ms=generated.latency_ms,
                    safety_flags=[
                        "llm_without_retrieved_source",
                        *[flag[:80] for flag in generated.response.safety_flags],
                    ],
                )
            state.incident.status = IncidentStatus.AWAITING_USER_INPUT
            return RoutedReply(
                CyberSaathiService._with_sentiment_strategy(
                    language,
                    response_understanding.sentiment,
                    CyberSaathiService._copy(language, "knowledge_no_result"),
                ),
                TurnKind.MESSAGE,
                GroundingStatus.NO_RESULT,
                retrieval_latency_ms=retrieval.retrieval_latency_ms,
                llm_fallback_used=generated.fallback_used,
                llm_latency_ms=generated.latency_ms,
                safety_flags=["deterministic_no_result_fallback"],
            )

        state.incident.status = IncidentStatus.AWAITING_USER_INPUT
        clarification = understanding.clarification_prompt or CyberSaathiService._copy(
            language, "clarify"
        )
        return RoutedReply(
            CyberSaathiService._with_sentiment_strategy(
                language, understanding.sentiment, clarification
            ),
            TurnKind.MESSAGE,
        )

    @staticmethod
    def _retrieve_knowledge(
        message: str,
        understanding: UnderstandingResult,
        state: ConversationState | None = None,
    ) -> KnowledgeSearchResponse:
        normalized_message = normalized_text(message)
        domain = CyberSaathiService._knowledge_domain(normalized_message, understanding)
        # No keyword expansion is added here. A fixed per-domain keyword blob used
        # to be appended to every query, and because it was long and on-topic it
        # dominated the score: within one domain the same chunks came back whatever
        # the citizen wrote - "banana bread recipe" scored higher than most real
        # questions. Retrieval now runs on the citizen's own words plus the incident
        # context, with semantic embeddings carrying the paraphrases the keywords
        # were compensating for.
        retrieval_query = CyberSaathiService._build_retrieval_query(
            state=state,
            message=normalized_message,
        )
        try:
            response = KnowledgeService.search(
                KnowledgeSearchRequest(
                    query=retrieval_query,
                    domain=domain,
                    language=understanding.response_language,
                    top_k=2,
                )
            )
            return CyberSaathiService._apply_audience_guard(retrieval_query, response, domain)
        except APIError:
            # Knowledge is an optional grounding layer. A missing, stale, or rejected
            # index must never suppress deterministic urgent-safety instructions.
            return KnowledgeSearchResponse(
                query=normalized_message,
                domain_filter=domain,
                retrieval_latency_ms=0,
                index_version="unavailable",
                no_result=True,
                matches=[],
                bounded_context="",
                retrieval_strategy="unavailable",
            )

    @staticmethod
    def _build_retrieval_query(
        *,
        state: ConversationState | None,
        message: str,
    ) -> str:
        """Anchor short follow-ups to the active incident instead of pronouns alone."""
        parts = [f"Current request: {message}"]
        if state is not None:
            incident = state.incident
            if incident.summary:
                parts.append(f"Active incident: {incident.summary}")
            confirmed_entities = [
                f"{entity.type.value}: {entity.normalized_value or entity.value}"
                for entity in incident.entities
                if entity.confirmed
            ]
            if confirmed_entities:
                parts.append("Confirmed incident details: " + "; ".join(confirmed_entities[:8]))
            previous_user_turn = next(
                (
                    turn.content
                    for turn in reversed(state.turns[:-1])
                    if turn.role == "user" and turn.content.strip()
                ),
                None,
            )
            if previous_user_turn:
                parts.append(f"Previous citizen detail: {previous_user_turn}")
        return normalized_text(" ".join(parts))[:1000]

    @staticmethod
    def _knowledge_domain(
        message: str, understanding: UnderstandingResult
    ) -> KnowledgeDomain | None:
        lowered = message.casefold()
        domain = understanding.crime_domain
        if understanding.intent == Intent.CHECK_IDENTIFIER:
            return KnowledgeDomain.SUSPICIOUS_IDENTIFIERS
        if any(term in lowered for term in ("digital arrest", "fake police", "fake officer")):
            return KnowledgeDomain.IMPERSONATION
        if any(term in lowered for term in ("fake profile", "pretend", "impersonat")):
            return KnowledgeDomain.IMPERSONATION
        if any(term in lowered for term in ("cyberstalk", "stalk", "पीछा", "लोकेशन")):
            return KnowledgeDomain.CYBERSTALKING
        if understanding.intent == Intent.GENERAL_AWARENESS:
            return KnowledgeDomain.GENERAL_CYBER_SAFETY
        if domain == CrimeDomain.ECOMMERCE_FRAUD:
            return KnowledgeDomain.ECOMMERCE_CONSUMER_GRIEVANCE
        if domain == CrimeDomain.ACCOUNT_COMPROMISE:
            return KnowledgeDomain.ACCOUNT_COMPROMISE
        if domain == CrimeDomain.IMPERSONATION:
            return KnowledgeDomain.IMPERSONATION
        if domain == CrimeDomain.CYBERSTALKING:
            return KnowledgeDomain.CYBERSTALKING
        if domain == CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY:
            return KnowledgeDomain.WOMEN_CHILD_ONLINE_SAFETY
        if domain == CrimeDomain.FINANCIAL_FRAUD:
            if any(term in lowered for term in ("upi", "wallet", "payment app", "qr")):
                return KnowledgeDomain.UPI_PAYMENT_FRAUD
            return KnowledgeDomain.FINANCIAL_FRAUD
        if domain == CrimeDomain.PHISHING_SCAM:
            if any(term in lowered for term in ("hacked", "compromised", "account access")):
                return KnowledgeDomain.ACCOUNT_COMPROMISE
            return KnowledgeDomain.PHISHING
        if domain == CrimeDomain.IDENTITY_THEFT:
            return KnowledgeDomain.IDENTITY_THEFT
        if domain == CrimeDomain.ONLINE_HARASSMENT:
            return KnowledgeDomain.HARASSMENT_ABUSE
        if domain == CrimeDomain.CHILD_SAFETY:
            return KnowledgeDomain.WOMEN_CHILD_ONLINE_SAFETY
        if domain == CrimeDomain.MALWARE:
            return KnowledgeDomain.MALWARE_DEVICE_COMPROMISE
        return None

    @staticmethod
    def _apply_audience_guard(
        message: str, response: KnowledgeSearchResponse, domain: KnowledgeDomain | None = None
    ) -> KnowledgeSearchResponse:
        """Keep women/child specific guidance out of unrelated answers.

        The classified domain is the primary signal, not the wording. This used to
        look only for English words in the retrieval query, which quietly depended
        on a per-domain keyword blob that was appended to every query and happened
        to contain "minor child women". With that blob gone, a citizen writing
        "Meri 15 saal ki cousin ko ... private photos" matched none of the terms,
        so the CERT-In child-safety sources were stripped from their own answer.
        A guard on how a distressed person phrases something, in one language, is
        the wrong guard; the understanding engine has already decided who this is
        about.
        """
        if domain is KnowledgeDomain.WOMEN_CHILD_ONLINE_SAFETY:
            return response
        lowered = message.casefold()
        audience_terms = (
            "child", "minor", "kid", "teen", "girl", "woman", "women", "mahila",
            "बच्च", "नाबालिग", "महिला", "लड़की", "morphed", "intimate image",
            # Romanised Hindi: how the same citizens actually type it.
            "bachch", "bachcha", "bachchi", "ladki", "larki", "beti", "behen",
            "nabalig", "naabalig", "saal ki", "saal ka",
        )
        if any(term in lowered for term in audience_terms):
            return response
        restricted_sources = {
            "ncrp_women_child_faq",
            "certin_cyber_smart_kids",
            "certin_mahila_raksha_en",
            "certin_mahila_raksha_hi",
        }
        matches = [
            match for match in response.matches if match.source_id not in restricted_sources
        ]
        context_parts: list[str] = []
        context_length = 0
        for match in matches:
            part = f"[{match.source_title} — {match.section_title}] {match.text}"
            if context_parts and context_length + len(part) + 2 > 2400:
                break
            context_parts.append(part)
            context_length += len(part) + 2
        return response.model_copy(
            update={
                "matches": matches,
                "no_result": not matches,
                "bounded_context": "\n\n".join(context_parts),
            }
        )

    @staticmethod
    def _ensure_focused_question(
        answer: str, domain: CrimeDomain, language: LanguageCode
    ) -> str:
        if "?" in answer or "？" in answer:
            return answer
        return f"{answer.rstrip()} {CyberSaathiService._focused_question(domain, language)}"

    @staticmethod
    def _question_copy(key: str, language: LanguageCode) -> str:
        questions: dict[str, dict[LanguageCode, str]] = {
            "optional_suspect_details": {
                LanguageCode.EN: "If you know anything about the suspect, share any available name, alias, phone number, account, profile, or link. This is optional—if you do not know, say ‘not known’; that is completely okay.",
                LanguageCode.HI: "यदि आपको संदिग्ध व्यक्ति के बारे में कुछ पता है, तो उपलब्ध नाम, उपनाम, फोन नंबर, अकाउंट, प्रोफाइल या लिंक बताएं। यह वैकल्पिक है—नहीं पता हो तो ‘पता नहीं’ कहें; कोई बात नहीं।",
                LanguageCode.HINGLISH: "Agar suspect ke baare mein kuch pata ho to available name, alias, phone number, account, profile ya link batayein. Ye optional hai—nahi pata ho to ‘pata nahi’ bol dein; koi baat nahi.",
            },
            "seller_contacted": {LanguageCode.EN: "Have you contacted the seller or marketplace through its official support channel?", LanguageCode.HI: "क्या आपने विक्रेता या मार्केटप्लेस से उसके आधिकारिक सहायता माध्यम से संपर्क किया?", LanguageCode.HINGLISH: "Kya seller ya marketplace ko official support channel se contact kiya?"},
            "order_reference": {LanguageCode.EN: "What order number, seller name, or listing URL do you have?", LanguageCode.HI: "आपके पास कौन सा ऑर्डर नंबर, विक्रेता का नाम या लिस्टिंग URL है?", LanguageCode.HINGLISH: "Aapke paas order number, seller name ya listing URL kya hai?"},
            "payment_proof": {LanguageCode.EN: "Do you have the payment receipt, bank entry, or order confirmation?", LanguageCode.HI: "क्या आपके पास भुगतान रसीद, बैंक प्रविष्टि या ऑर्डर पुष्टि है?", LanguageCode.HINGLISH: "Payment receipt, bank entry ya order confirmation available hai?"},
            "delivery_or_refund_promise": {LanguageCode.EN: "What delivery or refund date was promised, and what happened after it passed?", LanguageCode.HI: "डिलीवरी या रिफंड की कौन सी तारीख बताई गई थी, और उसके बाद क्या हुआ?", LanguageCode.HINGLISH: "Delivery ya refund ki kya date promise hui thi, aur date nikalne ke baad kya hua?"},
            "account_access_available": {LanguageCode.EN: "Can you still access the affected account from a trusted device?", LanguageCode.HI: "क्या आप भरोसेमंद डिवाइस से प्रभावित अकाउंट अभी भी खोल सकते हैं?", LanguageCode.HINGLISH: "Trusted device se affected account abhi access ho raha hai?"},
            "password_changed_trusted_device": {LanguageCode.EN: "Have you changed its password from a trusted device using the official app or site?", LanguageCode.HI: "क्या आपने आधिकारिक ऐप या साइट पर भरोसेमंद डिवाइस से पासवर्ड बदला है?", LanguageCode.HINGLISH: "Official app/site par trusted device se password change kiya?"},
            "sessions_and_mfa_secured": {LanguageCode.EN: "Have you signed out unknown sessions and secured recovery details and two-step verification?", LanguageCode.HI: "क्या आपने अनजान सत्र बंद करके रिकवरी विवरण और दो-चरण सत्यापन सुरक्षित किया?", LanguageCode.HINGLISH: "Unknown sessions sign out karke recovery details aur two-step verification secure ki?"},
            "unknown_activity_evidence": {LanguageCode.EN: "What unknown login, transaction, app, or device evidence can you preserve?", LanguageCode.HI: "आप कौन सा अनजान लॉगिन, लेन-देन, ऐप या डिवाइस प्रमाण सुरक्षित रख सकते हैं?", LanguageCode.HINGLISH: "Unknown login, transaction, app ya device ka kya evidence preserve kar sakte hain?"},
            "impersonator_still_connected": {LanguageCode.EN: "Is the caller or impersonator still connected or contacting you?", LanguageCode.HI: "क्या कॉलर या नकली अधिकारी अभी भी जुड़ा है या संपर्क कर रहा है?", LanguageCode.HINGLISH: "Caller ya impersonator abhi connected hai ya contact kar raha hai?"},
            "money_or_sensitive_data_shared": {LanguageCode.EN: "Did anyone send money or share an OTP, PIN, password, card detail, or identity document?", LanguageCode.HI: "क्या किसी ने पैसे भेजे या OTP, PIN, पासवर्ड, कार्ड विवरण या पहचान दस्तावेज साझा किया?", LanguageCode.HINGLISH: "Kya paise bheje ya OTP, PIN, password, card detail ya identity document share hua?"},
            "remote_access_granted": {LanguageCode.EN: "Was screen sharing, video monitoring, remote access, or an app installation allowed?", LanguageCode.HI: "क्या स्क्रीन शेयरिंग, वीडियो निगरानी, रिमोट एक्सेस या ऐप इंस्टॉल करने की अनुमति दी गई?", LanguageCode.HINGLISH: "Screen sharing, video monitoring, remote access ya app install allow kiya tha?"},
            "money_or_account_affected": {LanguageCode.EN: "After the app or remote access, was any money lost or was any account accessed or changed?", LanguageCode.HI: "ऐप या रिमोट एक्सेस के बाद क्या पैसे गए या किसी अकाउंट को एक्सेस या बदला गया?", LanguageCode.HINGLISH: "App ya remote access ke baad paise gaye, ya koi account access/change hua?"},
            "impersonator_identifiers": {LanguageCode.EN: "What phone number, account, profile, case number, message, or payment detail can you preserve?", LanguageCode.HI: "कौन सा फोन नंबर, अकाउंट, प्रोफाइल, केस नंबर, संदेश या भुगतान विवरण सुरक्षित है?", LanguageCode.HINGLISH: "Phone number, account, profile, case number, message ya payment detail mein se kya preserve hai?"},
            "identity_items_exposed": {LanguageCode.EN: "Which identity details or documents were exposed or copied?", LanguageCode.HI: "कौन से पहचान विवरण या दस्तावेज उजागर हुए या कॉपी किए गए?", LanguageCode.HINGLISH: "Kaunse identity details ya documents expose ya copy hue?"},
            "identity_misuse_observed": {LanguageCode.EN: "Have you seen a new account, SIM, loan, login, or profile created using those details?", LanguageCode.HI: "क्या उन विवरणों से बना कोई नया अकाउंट, SIM, ऋण, लॉगिन या प्रोफाइल दिखा?", LanguageCode.HINGLISH: "Un details se bana naya account, SIM, loan, login ya profile dikha?"},
            "affected_accounts_secured": {LanguageCode.EN: "Have you contacted the affected service through its official channel and secured the related accounts?", LanguageCode.HI: "क्या आपने प्रभावित सेवा से आधिकारिक माध्यम से संपर्क करके संबंधित अकाउंट सुरक्षित किए?", LanguageCode.HINGLISH: "Affected service ko official channel se contact karke related accounts secure kiye?"},
            "misuse_evidence": {LanguageCode.EN: "What alert, statement, application, profile, or reference number shows the misuse?", LanguageCode.HI: "कौन सा अलर्ट, विवरण, आवेदन, प्रोफाइल या रेफरेंस नंबर दुरुपयोग दिखाता है?", LanguageCode.HINGLISH: "Kaunsa alert, statement, application, profile ya reference number misuse dikhata hai?"},
            "immediate_danger": {LanguageCode.EN: "Are you or the affected person in immediate physical danger right now?", LanguageCode.HI: "क्या आप या प्रभावित व्यक्ति अभी तत्काल शारीरिक खतरे में हैं?", LanguageCode.HINGLISH: "Kya aap ya affected person abhi immediate physical danger mein hain?"},
            "platform_and_profile": {LanguageCode.EN: "Which platform and profile, username, phone number, or URL are involved?", LanguageCode.HI: "कौन सा प्लेटफॉर्म और प्रोफाइल, यूजरनेम, फोन नंबर या URL शामिल है?", LanguageCode.HINGLISH: "Kaunsa platform aur profile, username, phone number ya URL involved hai?"},
            "harassment_evidence_preserved": {LanguageCode.EN: "Have you preserved the original messages, dates, profile URL, and screenshots before blocking?", LanguageCode.HI: "क्या आपने ब्लॉक करने से पहले मूल संदेश, तारीखें, प्रोफाइल URL और स्क्रीनशॉट सुरक्षित किए?", LanguageCode.HINGLISH: "Block karne se pehle original messages, dates, profile URL aur screenshots preserve kiye?"},
            "platform_block_report": {LanguageCode.EN: "After preserving evidence, have you blocked and reported the account through the platform?", LanguageCode.HI: "प्रमाण सुरक्षित करने के बाद क्या आपने प्लेटफॉर्म पर अकाउंट ब्लॉक और रिपोर्ट किया?", LanguageCode.HINGLISH: "Evidence preserve karne ke baad platform par account block aur report kiya?"},
            "affected_person_and_age": {LanguageCode.EN: "Is the affected person you, your child, or someone else, and what is their age group?", LanguageCode.HI: "प्रभावित व्यक्ति आप, आपका बच्चा या कोई और है, और उनका आयु वर्ग क्या है?", LanguageCode.HINGLISH: "Affected person aap, aapka child ya koi aur hai, aur age group kya hai?"},
            "safe_evidence_preserved": {LanguageCode.EN: "Without downloading or forwarding harmful content, have you safely preserved the profile URL, message details, and available screenshots?", LanguageCode.HI: "हानिकारक सामग्री डाउनलोड या आगे भेजे बिना क्या आपने प्रोफाइल URL, संदेश विवरण और उपलब्ध स्क्रीनशॉट सुरक्षित रखे?", LanguageCode.HINGLISH: "Harmful content download/forward kiye bina profile URL, message details aur available screenshots safely preserve kiye?"},
            "stalker_knows_location": {LanguageCode.EN: "Does the person know your live location, home, workplace, school, or daily route?", LanguageCode.HI: "क्या उस व्यक्ति को आपका लाइव स्थान, घर, कार्यस्थल, स्कूल या रोज का रास्ता पता है?", LanguageCode.HINGLISH: "Kya us person ko live location, home, workplace, school ya daily route pata hai?"},
            "stalking_evidence_preserved": {LanguageCode.EN: "Have you preserved the repeated contacts, dates, locations, account details, and screenshots as one timeline?", LanguageCode.HI: "क्या आपने बार-बार हुए संपर्क, तारीखें, स्थान, अकाउंट विवरण और स्क्रीनशॉट एक समयरेखा में सुरक्षित किए?", LanguageCode.HINGLISH: "Repeated contacts, dates, locations, account details aur screenshots ko ek timeline mein preserve kiya?"},
            "link_opened": {LanguageCode.EN: "Did you open or tap the suspicious link?", LanguageCode.HI: "क्या आपने संदिग्ध लिंक खोला या दबाया?", LanguageCode.HINGLISH: "Suspicious link open ya tap kiya tha?"},
            "credentials_or_otp_entered": {LanguageCode.EN: "After opening it, did you enter a password, OTP, PIN, card detail, or other credential?", LanguageCode.HI: "लिंक खोलने के बाद क्या आपने पासवर्ड, OTP, PIN, कार्ड विवरण या कोई क्रेडेंशियल डाला?", LanguageCode.HINGLISH: "Open karne ke baad password, OTP, PIN, card detail ya credential dala?"},
            "additional_sensitive_data_shared": {LanguageCode.EN: "Besides the password already mentioned, did you also share an OTP, PIN, card, bank, or UPI detail?", LanguageCode.HI: "बताए गए पासवर्ड के अलावा क्या आपने OTP, PIN, कार्ड, बैंक या UPI की जानकारी भी साझा की?", LanguageCode.HINGLISH: "Jo password bataya uske alawa OTP, PIN, card, bank ya UPI detail bhi share ki thi?"},
            "money_lost_after_phishing": {LanguageCode.EN: "After using the link, was any money debited or transferred?", LanguageCode.HI: "लिंक इस्तेमाल करने के बाद क्या कोई पैसा कटा या ट्रांसफर हुआ?", LanguageCode.HINGLISH: "Link use karne ke baad koi paisa debit ya transfer hua?"},
            "app_or_remote_access": {LanguageCode.EN: "Did it make you download an app/APK, share the screen, or grant device access?", LanguageCode.HI: "क्या उसने ऐप/APK डाउनलोड, स्क्रीन शेयर या डिवाइस एक्सेस देने को कहा?", LanguageCode.HINGLISH: "Kya app/APK download, screen share ya device access grant kiya?"},
            "affected_account_secured": {LanguageCode.EN: "Have you secured the affected account from a trusted device and contacted the provider officially?", LanguageCode.HI: "क्या आपने भरोसेमंद डिवाइस से प्रभावित अकाउंट सुरक्षित करके सेवा प्रदाता से आधिकारिक संपर्क किया?", LanguageCode.HINGLISH: "Trusted device se affected account secure karke provider ko officially contact kiya?"},
            "phishing_source_and_time": {LanguageCode.EN: "What sender, phone number, profile, link, and approximate date or time can you preserve?", LanguageCode.HI: "कौन सा भेजने वाला, फोन नंबर, प्रोफाइल, लिंक और अनुमानित तारीख या समय सुरक्षित है?", LanguageCode.HINGLISH: "Sender, phone number, profile, link aur approximate date/time mein se kya preserve hai?"},
            "app_or_apk_installed": {LanguageCode.EN: "Which app or APK was installed, and is it still on the device?", LanguageCode.HI: "कौन सा ऐप या APK इंस्टॉल हुआ, और क्या वह अभी भी डिवाइस पर है?", LanguageCode.HINGLISH: "Kaunsa app ya APK install hua, aur kya abhi device par hai?"},
            "device_disconnected": {LanguageCode.EN: "Have you disconnected the affected device from mobile data, Wi-Fi, and any remote session?", LanguageCode.HI: "क्या आपने प्रभावित डिवाइस को मोबाइल डेटा, Wi-Fi और किसी रिमोट सत्र से अलग किया?", LanguageCode.HINGLISH: "Affected device ko mobile data, Wi-Fi aur remote session se disconnect kiya?"},
            "claim_and_source": {LanguageCode.EN: "What exact claim did you receive, and who or which account published it?", LanguageCode.HI: "आपको कौन सा सटीक दावा मिला, और उसे किसने या किस अकाउंट ने प्रकाशित किया?", LanguageCode.HINGLISH: "Exact claim kya tha, aur kis person ya account ne publish kiya?"},
            "immediate_harm_risk": {LanguageCode.EN: "Could this claim cause immediate physical, financial, communal, or public-safety harm?", LanguageCode.HI: "क्या इस दावे से तत्काल शारीरिक, वित्तीय, सामुदायिक या सार्वजनिक सुरक्षा का नुकसान हो सकता है?", LanguageCode.HINGLISH: "Kya is claim se immediate physical, financial, communal ya public-safety harm ho sakta hai?"},
            "source_link_or_capture": {LanguageCode.EN: "Do you have the original source link, account name, date, and an unedited capture?", LanguageCode.HI: "क्या आपके पास मूल स्रोत लिंक, अकाउंट नाम, तारीख और बिना संपादित कैप्चर है?", LanguageCode.HINGLISH: "Original source link, account name, date aur unedited capture available hai?"},
            "platform_reported": {LanguageCode.EN: "Have you reported the content to the platform without forwarding it further?", LanguageCode.HI: "क्या आपने सामग्री को आगे भेजे बिना प्लेटफॉर्म पर रिपोर्ट किया?", LanguageCode.HINGLISH: "Content ko aage forward kiye bina platform par report kiya?"},
            "trusted_adult_and_evidence": {LanguageCode.EN: "Is a trusted adult supporting the child, and has evidence been preserved without downloading or redistributing harmful content?", LanguageCode.HI: "क्या कोई भरोसेमंद वयस्क बच्चे की सहायता कर रहा है, और हानिकारक सामग्री डाउनलोड या आगे बांटे बिना प्रमाण सुरक्षित है?", LanguageCode.HINGLISH: "Kya trusted adult child ko support kar raha hai, aur harmful content download/redistribute kiye bina evidence preserve hai?"},
            "immediate_physical_threat": {LanguageCode.EN: "Is there a credible immediate threat to any person, place, or essential service?", LanguageCode.HI: "क्या किसी व्यक्ति, स्थान या आवश्यक सेवा को विश्वसनीय तत्काल खतरा है?", LanguageCode.HINGLISH: "Kya kisi person, place ya essential service ko credible immediate threat hai?"},
            "threat_is_ongoing": {LanguageCode.EN: "Is the threat, recruitment, instruction, or attack activity still ongoing?", LanguageCode.HI: "क्या धमकी, भर्ती, निर्देश या हमले की गतिविधि अभी भी जारी है?", LanguageCode.HINGLISH: "Kya threat, recruitment, instruction ya attack activity abhi ongoing hai?"},
            "source_account_or_url": {LanguageCode.EN: "What original account, phone number, channel, URL, time, or message identifies the source?", LanguageCode.HI: "कौन सा मूल अकाउंट, फोन नंबर, चैनल, URL, समय या संदेश स्रोत की पहचान करता है?", LanguageCode.HINGLISH: "Original account, phone number, channel, URL, time ya message mein se source ko kya identify karta hai?"},
            "threat_evidence_preserved": {LanguageCode.EN: "Have you preserved the original evidence without replying, joining, downloading, or forwarding it?", LanguageCode.HI: "क्या आपने जवाब दिए, जुड़ने, डाउनलोड या आगे भेजने के बिना मूल प्रमाण सुरक्षित रखा?", LanguageCode.HINGLISH: "Reply, join, download ya forward kiye bina original evidence preserve kiya?"},
        }
        localized = questions.get(key)
        if localized is None:
            return CyberSaathiService._copy(language, "clarify")
        return localized.get(language, localized[LanguageCode.EN])

    @staticmethod
    def _needs_optional_suspect_question(state: ConversationState) -> bool:
        record = CyberSaathiService._active_record(state)
        if record is None or "answered:optional_suspect_details" in record.completed_actions:
            return False
        return not any(
            entity.type in SUSPECT_IDENTIFIER_TYPES for entity in state.incident.entities
        )

    @staticmethod
    def _suspect_name_and_alias(details: str | None) -> tuple[str | None, str | None]:
        if not details:
            return None, None
        name_match = re.search(
            r"\b(?:name|naam)\s*(?:(?:is|was|hai|tha)\s+)?"
            r"(?P<value>[a-z][a-z.'-]*(?:\s+[a-z][a-z.'-]*){0,2}?)"
            r"(?=\s+(?:tha|hai|is|was|aur|and|alias|username|profile)\b|[,.;]|$)",
            details,
            re.IGNORECASE,
        )
        alias_match = re.search(
            r"\b(?:alias|username)\s*"
            r"(?:(?:is|was|hai|tha)\s+)?@?(?P<value>[a-z0-9_.-]{2,80})",
            details,
            re.IGNORECASE,
        )
        name = name_match.group("value").strip() if name_match else None
        alias = alias_match.group("value").strip() if alias_match else None
        return name, alias

    @staticmethod
    def _domain_safety_copy(domain: CrimeDomain, language: LanguageCode) -> str:
        safety: dict[CrimeDomain, dict[LanguageCode, str]] = {
            CrimeDomain.ECOMMERCE_FRAUD: {
                LanguageCode.EN: "1. Save the order page, payment receipt, seller messages, and promised delivery date.\n2. Contact the marketplace or seller only through its official support/refund process.\n3. Do not pay any extra fee to release a refund or delivery.",
                LanguageCode.HI: "1. ऑर्डर पेज, भुगतान रसीद, विक्रेता के संदेश और बताई गई डिलीवरी तारीख सुरक्षित रखें।\n2. केवल आधिकारिक सहायता या रिफंड प्रक्रिया से संपर्क करें।\n3. रिफंड या डिलीवरी के लिए कोई अतिरिक्त शुल्क न दें।",
                LanguageCode.HINGLISH: "1. Order page, payment receipt, seller messages aur promised delivery date save rakhein.\n2. Marketplace/seller ko sirf official support ya refund process se contact karein.\n3. Refund ya delivery release karne ke naam par extra fee na dein.",
            },
            CrimeDomain.ACCOUNT_COMPROMISE: {
                LanguageCode.EN: "1. Use a trusted device and the provider's official app or site.\n2. Change the password, sign out unknown sessions, and secure recovery details and two-step verification.\n3. Preserve login alerts and unknown-activity evidence before deleting anything.",
                LanguageCode.HI: "1. भरोसेमंद डिवाइस और सेवा के आधिकारिक ऐप या साइट का उपयोग करें।\n2. पासवर्ड बदलें, अनजान सत्र बंद करें और रिकवरी तथा दो-चरण सत्यापन सुरक्षित करें।\n3. कुछ हटाने से पहले लॉगिन अलर्ट और अनजान गतिविधि के प्रमाण रखें।",
                LanguageCode.HINGLISH: "1. Trusted device aur provider ka official app/site use karein.\n2. Password change karke unknown sessions sign out karein aur recovery plus two-step verification secure karein.\n3. Kuch delete karne se pehle login alerts aur unknown activity ka evidence save karein.",
            },
            CrimeDomain.IMPERSONATION: {
                LanguageCode.EN: "1. End the call or chat and do not transfer money or share OTP, PIN, passwords, or documents.\n2. Verify the claim independently using the organisation's official public number or website.\n3. Preserve the caller number, profile, messages, case claim, and payment request.",
                LanguageCode.HI: "1. कॉल या चैट बंद करें और पैसे, OTP, PIN, पासवर्ड या दस्तावेज साझा न करें।\n2. संस्था के सार्वजनिक आधिकारिक नंबर या वेबसाइट से दावे की स्वतंत्र पुष्टि करें।\n3. कॉलर नंबर, प्रोफाइल, संदेश, केस का दावा और भुगतान मांग सुरक्षित रखें।",
                LanguageCode.HINGLISH: "1. Call/chat end karein; paise transfer ya OTP, PIN, password, documents share na karein.\n2. Organisation ke official public number/website se claim independently verify karein.\n3. Caller number, profile, messages, case claim aur payment request preserve karein.",
            },
            CrimeDomain.IDENTITY_THEFT: {
                LanguageCode.EN: "1. Secure the accounts and documents connected to the exposed identity details.\n2. Contact the issuing authority or affected provider through its official channel.\n3. Preserve alerts, applications, profiles, statements, and reference numbers showing misuse.",
                LanguageCode.HI: "1. उजागर पहचान विवरण से जुड़े अकाउंट और दस्तावेज सुरक्षित करें।\n2. जारीकर्ता संस्था या प्रभावित सेवा से आधिकारिक माध्यम से संपर्क करें।\n3. दुरुपयोग दिखाने वाले अलर्ट, आवेदन, प्रोफाइल, विवरण और रेफरेंस नंबर रखें।",
                LanguageCode.HINGLISH: "1. Exposed identity details se linked accounts aur documents secure karein.\n2. Issuing authority ya affected provider ko official channel se contact karein.\n3. Misuse dikhane wale alerts, applications, profiles, statements aur reference numbers save karein.",
            },
            CrimeDomain.ONLINE_HARASSMENT: {
                LanguageCode.EN: "1. If there is immediate physical danger, move to safety and contact a trusted person or local emergency help.\n2. Preserve original messages, dates, profile URLs, and screenshots before blocking.\n3. Block and report the account through the platform after saving evidence.",
                LanguageCode.HI: "1. तत्काल शारीरिक खतरा हो तो सुरक्षित स्थान पर जाएं और भरोसेमंद व्यक्ति या स्थानीय आपात सहायता से संपर्क करें।\n2. ब्लॉक करने से पहले मूल संदेश, तारीखें, प्रोफाइल URL और स्क्रीनशॉट रखें।\n3. प्रमाण रखने के बाद प्लेटफॉर्म पर अकाउंट ब्लॉक और रिपोर्ट करें।",
                LanguageCode.HINGLISH: "1. Immediate physical danger ho to safe jagah jayein aur trusted person/local emergency help ko contact karein.\n2. Block karne se pehle platform aur profile URL, original messages, dates aur screenshots save karein.\n3. Evidence save karke account ko platform par block/report karein.",
            },
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY: {
                LanguageCode.EN: "1. Do not pay, comply with further demands, or continue contact; do not download, edit, or forward the intimate content.\n2. Safely preserve the profile URL, threats, dates, and available screenshots without redistributing the content.\n3. After saving evidence, block/report the account and involve a trusted person; specified intimate-content reports may offer an anonymous reporting option.",
                LanguageCode.HI: "1. पैसे न दें, आगे की मांग न मानें और संपर्क जारी न रखें; निजी सामग्री डाउनलोड, संपादित या आगे न भेजें।\n2. सामग्री को दोबारा साझा किए बिना प्रोफाइल URL, धमकियां, तारीखें और उपलब्ध स्क्रीनशॉट सुरक्षित रखें।\n3. प्रमाण रखने के बाद अकाउंट ब्लॉक/रिपोर्ट करें और भरोसेमंद व्यक्ति को साथ लें; निर्धारित निजी-सामग्री रिपोर्ट में गुमनाम विकल्प मिल सकता है।",
                LanguageCode.HINGLISH: "1. Paise na dein, aage ki demand na maanein aur contact continue na karein; intimate content download ya forward na karein, aur edit bhi na karein.\n2. Content redistribute kiye bina profile URL, threats, dates aur available screenshots safely preserve karein.\n3. Evidence save karke account block/report karein aur trusted person ko involve karein; eligible intimate-content cases mein anonymous reporting option mil sakta hai.",
            },
            CrimeDomain.CYBERSTALKING: {
                LanguageCode.EN: "1. If you feel physically unsafe, move to a safe place and contact a trusted person or local emergency help.\n2. Turn off unnecessary live-location sharing and review account/device access from a trusted device.\n3. Preserve repeated contacts, locations, dates, profiles, and screenshots as one timeline.",
                LanguageCode.HI: "1. शारीरिक खतरा लगे तो सुरक्षित स्थान पर जाएं और भरोसेमंद व्यक्ति या स्थानीय आपात सहायता से संपर्क करें।\n2. अनावश्यक लाइव लोकेशन बंद करें और भरोसेमंद डिवाइस से अकाउंट/डिवाइस एक्सेस जांचें।\n3. बार-बार हुए संपर्क, स्थान, तारीखें, प्रोफाइल और स्क्रीनशॉट एक समयरेखा में रखें।",
                LanguageCode.HINGLISH: "1. Physical safety ka risk ho to safe jagah jayein aur trusted person/local emergency help ko contact karein.\n2. Unnecessary live-location sharing off karke trusted device se account/device access review karein.\n3. Repeated contacts, locations, dates, profiles aur screenshots ko ek timeline mein preserve karein.",
            },
            CrimeDomain.PHISHING_SCAM: {
                LanguageCode.EN: "1. Do not reopen the link or reply to the sender.\n2. If you entered a credential, use a trusted device to change it on the official app/site and secure active sessions.\n3. Preserve the original sender, link, message, and time without forwarding it.",
                LanguageCode.HI: "1. लिंक दोबारा न खोलें और भेजने वाले को जवाब न दें।\n2. कोई क्रेडेंशियल डाला हो तो भरोसेमंद डिवाइस से आधिकारिक ऐप/साइट पर उसे बदलें और सक्रिय सत्र सुरक्षित करें।\n3. मूल भेजने वाला, लिंक, संदेश और समय आगे भेजे बिना सुरक्षित रखें।",
                LanguageCode.HINGLISH: "1. Link dobara na kholein aur sender ko reply na karein.\n2. Credential enter kiya ho to trusted device se official app/site par change karke active sessions secure karein.\n3. Original sender, link, message aur time ko forward kiye bina preserve karein.",
            },
            CrimeDomain.MALWARE: {
                LanguageCode.EN: "1. Disconnect the affected device from mobile data, Wi-Fi, and remote sessions.\n2. From a different trusted device, secure important accounts and contact any affected provider officially.\n3. Preserve the app/APK name, permissions, messages, and unknown activity before removing evidence.",
                LanguageCode.HI: "1. प्रभावित डिवाइस को मोबाइल डेटा, Wi-Fi और रिमोट सत्रों से अलग करें।\n2. दूसरे भरोसेमंद डिवाइस से महत्वपूर्ण अकाउंट सुरक्षित करें और प्रभावित सेवा से आधिकारिक संपर्क करें।\n3. प्रमाण हटाने से पहले ऐप/APK नाम, अनुमतियां, संदेश और अनजान गतिविधि सुरक्षित रखें।",
                LanguageCode.HINGLISH: "1. Affected device ko mobile data, Wi-Fi aur remote sessions se disconnect karein.\n2. Dusre trusted device se important accounts secure karke affected provider ko officially contact karein.\n3. Evidence remove karne se pehle app/APK name, permissions, messages aur unknown activity save karein.",
            },
            CrimeDomain.MISINFORMATION: {
                LanguageCode.EN: "1. Do not forward the claim while it is unverified.\n2. Preserve the original source, account, date, URL, and an unedited capture.\n3. Compare it with authoritative primary sources and report harmful content through the platform.",
                LanguageCode.HI: "1. दावे की पुष्टि न होने तक उसे आगे न भेजें।\n2. मूल स्रोत, अकाउंट, तारीख, URL और बिना संपादित कैप्चर सुरक्षित रखें।\n3. आधिकारिक प्राथमिक स्रोतों से तुलना करें और हानिकारक सामग्री प्लेटफॉर्म पर रिपोर्ट करें।",
                LanguageCode.HINGLISH: "1. Claim verify hone tak forward na karein.\n2. Original source, account, date, URL aur unedited capture preserve karein.\n3. Authoritative primary sources se compare karke harmful content platform par report karein.",
            },
            CrimeDomain.CHILD_SAFETY: {
                LanguageCode.EN: "1. Prioritise the child's immediate safety and involve a trusted adult now.\n2. Do not pay, negotiate, send more material, or confront the person; do not download, redistribute, or edit harmful content.\n3. Safely preserve the account, threats, dates, and available screenshots, then block/report the account with the trusted adult.",
                LanguageCode.HI: "1. बच्चे की तत्काल सुरक्षा को प्राथमिकता दें और अभी भरोसेमंद वयस्क को साथ लें।\n2. पैसे न दें, बातचीत या सौदा न करें, और सामग्री न भेजें; हानिकारक सामग्री डाउनलोड, आगे या संपादित न करें।\n3. अकाउंट, धमकियां, तारीखें और उपलब्ध स्क्रीनशॉट सुरक्षित रखें, फिर भरोसेमंद वयस्क के साथ अकाउंट ब्लॉक/रिपोर्ट करें।",
                LanguageCode.HINGLISH: "1. Child ki immediate safety prioritise karke trusted adult ko abhi involve karein.\n2. Paise na dein, negotiate na karein, aur material na bhejein; harmful content download, redistribute ya edit na karein.\n3. Account, threats, dates aur available screenshots safely preserve karke trusted adult ke saath account block/report karein.",
            },
            CrimeDomain.CYBER_TERRORISM: {
                LanguageCode.EN: "1. Do not reply, join, download, or forward the threatening material.\n2. Preserve the original account, channel, URL, message, and time without altering it.\n3. If a person, place, or essential service faces a credible immediate threat, contact local emergency authorities now.",
                LanguageCode.HI: "1. धमकी वाली सामग्री का जवाब न दें, न जुड़ें, डाउनलोड या आगे न भेजें।\n2. मूल अकाउंट, चैनल, URL, संदेश और समय बिना बदलाव सुरक्षित रखें।\n3. व्यक्ति, स्थान या आवश्यक सेवा को विश्वसनीय तत्काल खतरा हो तो अभी स्थानीय आपात अधिकारियों से संपर्क करें।",
                LanguageCode.HINGLISH: "1. Threatening material ko reply, join, download ya forward na karein.\n2. Original account, channel, URL, message aur time bina alter kiye preserve karein.\n3. Person, place ya essential service ko credible immediate threat ho to local emergency authorities ko abhi contact karein.",
            },
        }
        localized = safety.get(domain)
        if localized is None:
            return CyberSaathiService._copy(language, "clarify")
        return localized.get(language, localized[LanguageCode.EN])

    @staticmethod
    def _is_general_guidance_request(message: str) -> bool:
        lowered = normalized_text(message)
        return any(marker in lowered for marker in GENERAL_GUIDANCE_MARKERS)

    @staticmethod
    def _infer_flow_answers_from_message(state: ConversationState, message: str) -> None:
        """Do not ask for a fact the citizen already stated in the first message."""
        record = CyberSaathiService._active_record(state)
        if record is None:
            return
        lowered = normalized_text(message)
        rules: dict[CrimeDomain, tuple[tuple[str, tuple[str, ...]], ...]] = {
            CrimeDomain.ECOMMERCE_FRAUD: (
                ("seller_contacted", ("seller reply", "seller response", "contacted seller", "seller ko contact", "marketplace ko contact")),
            ),
            CrimeDomain.PHISHING_SCAM: (
                ("link_opened", ("opened", "open kar", "click kiya", "click karke", "clicked", "tap kiya", "khol diya")),
                ("credentials_or_otp_entered", ("entered otp", "shared otp", "entered password", "password enter", "password dala", "otp dala")),
                ("app_or_remote_access", ("remote access", "screen share", "app install", "apk install")),
            ),
            CrimeDomain.MALWARE: (
                ("app_or_apk_installed", ("installed", "install ki", "install kiya", "apk")),
                ("remote_access_granted", ("gave remote access", "remote access diya", "remote access de diya", "access de diya", "screen share")),
            ),
            CrimeDomain.ACCOUNT_COMPROMISE: (
                ("account_access_available", ("cannot log in", "can't log in", "cant log in", "access nahi")),
                ("password_changed_trusted_device", ("changed my password", "password change kar diya")),
            ),
            CrimeDomain.ONLINE_HARASSMENT: (
                ("platform_and_profile", ("instagram", "facebook", "whatsapp", "telegram", "snapchat")),
            ),
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY: (
                ("platform_and_profile", ("instagram", "facebook", "whatsapp", "telegram", "snapchat")),
            ),
            CrimeDomain.CHILD_SAFETY: (
                ("platform_and_profile", ("instagram", "facebook", "whatsapp", "telegram", "snapchat")),
            ),
            CrimeDomain.CYBERSTALKING: (
                ("platform_and_profile", ("instagram", "facebook", "whatsapp", "telegram", "snapchat")),
            ),
            CrimeDomain.MISINFORMATION: (
                ("claim_and_source", ("post contains", "message claims", "video claims", "viral post")),
            ),
        }
        for key, markers in rules.get(state.incident.crime_domain, ()):
            marker = f"answered:{key}"
            if marker not in record.completed_actions and any(value in lowered for value in markers):
                record.completed_actions.append(marker)
        if (
            state.incident.crime_domain
            in {CrimeDomain.CHILD_SAFETY, CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY}
            and UnderstandingEngine.has_child_context(lowered)
            and "answered:affected_person_and_age" not in record.completed_actions
        ):
            record.completed_actions.append("answered:affected_person_and_age")

    @staticmethod
    def _next_domain_question(state: ConversationState) -> str | None:
        flow = DOMAIN_QUESTION_FLOWS.get(state.incident.crime_domain)
        record = CyberSaathiService._active_record(state)
        if flow is None or record is None:
            state.pending_question = None
            return None
        completed = set(record.completed_actions)
        for key, answer_type in flow:
            if f"answered:{key}" not in completed:
                CyberSaathiService._set_pending_question(state, key, answer_type)
                return CyberSaathiService._question_copy(key, state.language)
        state.pending_question = None
        return None

    @staticmethod
    def _route_expected_answer(
        state: ConversationState,
        message: str,
        understanding: UnderstandingResult,
    ) -> RoutedReply:
        pending = state.pending_question
        record = CyberSaathiService._active_record(state)
        if pending is None or record is None:
            return RoutedReply(CyberSaathiService._copy(state.language, "clarify"), TurnKind.MESSAGE)
        pending.attempts += 1
        pending.last_answer = message.strip()[:500]
        answer_class = CyberSaathiService._expected_answer_class(message)
        if pending.answer_type in {
            ExpectedAnswerType.CONFIRM_ENTITIES,
            ExpectedAnswerType.FINAL_LOSS_AMOUNT,
        }:
            copy = {
                LanguageCode.EN: "I will not confirm that value. Please enter the corrected value in numbers, or say that it is unknown.",
                LanguageCode.HI: "मैं उस जानकारी की पुष्टि नहीं करूंगा। सही जानकारी अंकों में लिखें, या बताएं कि वह अज्ञात है।",
                LanguageCode.HINGLISH: "Main us value ko confirm nahi karunga. Correct value numbers mein likhein, ya batayein ki wo unknown hai.",
            }
            return RoutedReply(
                copy.get(state.language, copy[LanguageCode.EN]),
                TurnKind.CONFIRMATION,
            )
        if (
            state.incident.crime_domain == CrimeDomain.FINANCIAL_FRAUD
            and pending.answer_type == ExpectedAnswerType.YES_NO
            and pending.key in {"bank_contact", "bank_contact_and_protect", "bank_protection"}
            and answer_class in {"no", "uncertain", "other"}
        ):
            CyberSaathiService._merge_incident_detail(state, message, understanding)
            copy = {
                LanguageCode.EN: "Use the bank or UPI provider's official app, website, or card-back number and ask it to block outgoing transactions. Tell me when that protection action is complete, or say why it is unavailable.",
                LanguageCode.HI: "बैंक या UPI provider के official app, website या card के पीछे दिए नंबर से संपर्क करके outgoing transactions रोकने को कहें। सुरक्षा कार्रवाई पूरी हो जाए तो बताएं, या बताएं कि यह उपलब्ध क्यों नहीं है।",
                LanguageCode.HINGLISH: "Bank ya UPI provider ke official app, website ya card-back number se outgoing transactions block karwayein. Protection action complete ho to batayein, ya batayein ki ye available kyun nahi hai.",
            }
            return RoutedReply(
                copy.get(state.language, copy[LanguageCode.EN]),
                TurnKind.MESSAGE,
                GroundingStatus.DETERMINISTIC_PLAYBOOK,
            )
        marker = f"answered:{pending.key}"
        if marker not in record.completed_actions:
            record.completed_actions.append(marker)
        if (
            pending.key == "optional_suspect_details"
            and answer_class not in {"no", "uncertain"}
        ):
            record.report_preparation.suspect_details = message.strip()[:1000]
        if pending.answer_type == ExpectedAnswerType.YES_NO:
            answer_marker = f"answer:{pending.key}:{answer_class}"
            if answer_marker not in record.completed_actions:
                record.completed_actions.append(answer_marker)
        CyberSaathiService._merge_incident_detail(state, message, understanding)
        state.pending_question = None
        next_question = CyberSaathiService._next_domain_question(state)
        if next_question is None:
            state.incident.intent = Intent.REPORT_INCIDENT
            return CyberSaathiService._prepare_report(state)
        acknowledgements = {
            LanguageCode.EN: "I recorded that for this incident. Next:",
            LanguageCode.HI: "मैंने इसे इस घटना में दर्ज कर लिया है। अगला सवाल:",
            LanguageCode.HINGLISH: "Ye detail current incident mein record ho gayi. Agla sawal:",
        }
        return RoutedReply(
            acknowledgements.get(state.language, acknowledgements[LanguageCode.EN])
            + " "
            + next_question,
            TurnKind.MESSAGE,
            GroundingStatus.DETERMINISTIC_PLAYBOOK,
        )

    @staticmethod
    def _progress_copy(domain: CrimeDomain, language: LanguageCode) -> str:
        if domain == CrimeDomain.FINANCIAL_FRAUD:
            return CyberSaathiService._copy(language, "progress_next")
        intro = {
            LanguageCode.EN: "I have kept the earlier incident details and will give only the next relevant step.",
            LanguageCode.HI: "मैंने पहले की घटना का विवरण सुरक्षित रखा है और अब केवल संबंधित अगला कदम बताऊंगा।",
            LanguageCode.HINGLISH: "Pehle incident details safe hain; ab main sirf relevant next step bataunga.",
        }
        return (
            intro.get(language, intro[LanguageCode.EN])
            + " "
            + CyberSaathiService._focused_question(domain, language)
        )

    @staticmethod
    def _focused_question(domain: CrimeDomain, language: LanguageCode) -> str:
        flow = DOMAIN_QUESTION_FLOWS.get(domain)
        if flow:
            return CyberSaathiService._question_copy(flow[0][0], language)
        questions = {
            CrimeDomain.FINANCIAL_FRAUD: {
                LanguageCode.EN: "Have you received the bank complaint reference number, and have you called 1930 if the loss was recent?",
                LanguageCode.HI: "क्या बैंक शिकायत का रेफरेंस नंबर मिला है, और हाल की हानि होने पर क्या आपने 1930 पर कॉल किया?",
                LanguageCode.HINGLISH: "Kya bank complaint ka reference number mila, aur recent loss hai to 1930 call kiya?",
            },
            CrimeDomain.PHISHING_SCAM: {
                LanguageCode.EN: "After opening the link, did you enter a password or OTP, download an app, or grant device access?",
                LanguageCode.HI: "लिंक खोलने के बाद क्या आपने पासवर्ड या OTP डाला, कोई ऐप डाउनलोड किया, या डिवाइस एक्सेस दिया?",
                LanguageCode.HINGLISH: "Link kholne ke baad password/OTP dala, app download ki, ya device access diya tha?",
            },
            CrimeDomain.ECOMMERCE_FRAUD: {
                LanguageCode.EN: "Do you still have the order confirmation, payment proof, and the seller's written response or complaint number?",
                LanguageCode.HI: "क्या आपके पास ऑर्डर पुष्टि, भुगतान प्रमाण और विक्रेता का लिखित उत्तर या शिकायत नंबर है?",
                LanguageCode.HINGLISH: "Kya order confirmation, payment proof aur seller ka written response ya complaint number aapke paas hai?",
            },
            CrimeDomain.ACCOUNT_COMPROMISE: {
                LanguageCode.EN: "Can you still access the account, and have you changed its password from a trusted device?",
                LanguageCode.HI: "क्या आप अभी भी अकाउंट खोल सकते हैं, और क्या भरोसेमंद डिवाइस से पासवर्ड बदला है?",
                LanguageCode.HINGLISH: "Kya account abhi access ho raha hai, aur trusted device se password change kiya?",
            },
            CrimeDomain.MALWARE: {
                LanguageCode.EN: "Did you install an app or APK, grant remote access, or notice unknown transactions?",
                LanguageCode.HI: "क्या आपने कोई ऐप या APK इंस्टॉल किया, रिमोट एक्सेस दिया, या अनजान लेनदेन देखा?",
                LanguageCode.HINGLISH: "Kya app/APK install ki, remote access diya, ya unknown transaction dikha?",
            },
        }
        if domain in {CrimeDomain.CHILD_SAFETY, CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY}:
            localized = {
                LanguageCode.EN: "Is the child in immediate danger? Do not download or redistribute the harmful content; preserve the profile URL, message details, and screenshots safely. Anonymous reporting is limited to eligible Women and Child Safety content.",
                LanguageCode.HI: "क्या बच्चे को तत्काल खतरा है? हानिकारक सामग्री डाउनलोड या आगे साझा न करें; प्रोफाइल URL, संदेश विवरण और स्क्रीनशॉट सुरक्षित रखें। गुमनाम रिपोर्टिंग केवल पात्र महिला एवं बाल सुरक्षा सामग्री तक सीमित है।",
                LanguageCode.HINGLISH: "Kya child immediate danger mein hai? Harmful content download ya forward na karein; profile URL, message details aur screenshots safely preserve karein. Anonymous reporting sirf eligible Women and Child Safety content ke liye hai.",
            }
            return localized.get(language, localized[LanguageCode.EN])
        if domain in {CrimeDomain.ONLINE_HARASSMENT, CrimeDomain.CYBERSTALKING}:
            localized = {
                LanguageCode.EN: "Are you in immediate danger? Preserve the original messages, profile URL, dates, and screenshots before blocking or reporting the account. Which platform and profile are involved?",
                LanguageCode.HI: "क्या आपको तत्काल खतरा है? अकाउंट ब्लॉक या रिपोर्ट करने से पहले मूल संदेश, प्रोफाइल URL, तारीखें और स्क्रीनशॉट सुरक्षित रखें। कौन सा प्लेटफॉर्म और प्रोफाइल शामिल है?",
                LanguageCode.HINGLISH: "Kya aap immediate danger mein hain? Account block/report karne se pehle original messages, profile URL, dates aur screenshots preserve karein. Kaunsa platform aur profile involved hai?",
            }
            return localized.get(language, localized[LanguageCode.EN])
        if domain == CrimeDomain.IMPERSONATION:
            localized = {
                LanguageCode.EN: "Is the caller still connected, or did they get remote access to a device or account?",
                LanguageCode.HI: "क्या कॉलर अभी भी जुड़ा है, या उसे डिवाइस या अकाउंट का रिमोट एक्सेस मिला?",
                LanguageCode.HINGLISH: "Kya caller abhi connected hai, ya usko device/account ka remote access mila?",
            }
            return localized.get(language, localized[LanguageCode.EN])
        default = {
            LanguageCode.EN: "What happened next, and which account, device, or person is affected?",
            LanguageCode.HI: "इसके बाद क्या हुआ, और कौन सा अकाउंट, डिवाइस या व्यक्ति प्रभावित है?",
            LanguageCode.HINGLISH: "Uske baad kya hua, aur kaunsa account, device ya person affected hai?",
        }
        localized = questions.get(domain, default)
        return localized.get(language, localized[LanguageCode.EN])

    @staticmethod
    def _conversation_sources(matches: list[KnowledgeMatch]) -> list[ConversationSource]:
        return [
            ConversationSource(
                chunk_id=match.chunk_id,
                source_id=match.source_id,
                source_title=match.source_title,
                source_url=match.source_url,
                source_type=match.source_type,
                jurisdiction=match.jurisdiction,
                version=match.version,
                section_title=match.section_title,
            )
            for match in matches
        ]

    @staticmethod
    def _with_sentiment_strategy(
        language: LanguageCode, sentiment: Sentiment, response: str
    ) -> str:
        strategies = {
            Sentiment.DISTRESSED: {
                LanguageCode.EN: "I know this is stressful. Let us take the safest next step now.",
                LanguageCode.HI: "मैं समझता हूं कि यह तनावपूर्ण है। आइए अभी सबसे सुरक्षित अगला कदम उठाएं।",
                LanguageCode.HINGLISH: "Main samajhta hoon ye stressful hai. Chaliye abhi safest next step lete hain.",
            },
            Sentiment.ANGRY: {
                LanguageCode.EN: "I understand this is frustrating. Here is the direct next action.",
                LanguageCode.HI: "मैं समझता हूं कि यह निराशाजनक है। यह सीधा अगला कदम है।",
                LanguageCode.HINGLISH: "Main samajhta hoon ye frustrating hai. Ye direct next action hai.",
            },
            Sentiment.CONFUSED: {
                LanguageCode.EN: "I will keep this simple.",
                LanguageCode.HI: "मैं इसे सरल तरीके से समझाता हूं।",
                LanguageCode.HINGLISH: "Main ise simple rakhta hoon.",
            },
            Sentiment.FEARFUL: {
                LanguageCode.EN: "You are not alone. Focus first on your immediate safety.",
                LanguageCode.HI: "आप अकेले नहीं हैं। पहले अपनी तत्काल सुरक्षा पर ध्यान दें।",
                LanguageCode.HINGLISH: "Aap akele nahi hain. Pehle immediate safety par focus karein.",
            },
        }
        localized = strategies.get(sentiment)
        if localized is None:
            return response
        prefix = localized.get(language, localized[LanguageCode.EN])
        separator = "\n" if response.lstrip().startswith("1.") else " "
        return f"{prefix}{separator}{response}"

    @staticmethod
    def _confirmation_copy(language: LanguageCode, entities: list[Entity]) -> str:
        values = ", ".join(
            f"{entity.type.value}: "
            + (
                UnderstandingEngine.format_amount_for_display(entity.normalized_value)
                if entity.type == EntityType.AMOUNT and entity.normalized_value
                else entity.value
            )
            for entity in entities
        )
        copy = {
            LanguageCode.EN: f"Please confirm these details before I use them: {values}.",
            LanguageCode.HI: f"इन विवरणों की पुष्टि करें: {values}।",
            LanguageCode.HINGLISH: f"In details ko confirm karein: {values}.",
        }
        return copy.get(language, copy[LanguageCode.EN])

    @staticmethod
    def _has_ambiguous_pending_amounts(state: ConversationState) -> bool:
        pending = set(state.pending_confirmation_entity_ids)
        amounts = [
            entity
            for entity in state.incident.entities
            if entity.id in pending and entity.type == EntityType.AMOUNT
        ]
        return len(amounts) > 1

    @staticmethod
    def _ambiguous_amount_reply(language: LanguageCode, *, repeated: bool = False) -> RoutedReply:
        first_copy = {
            LanguageCode.EN: "I found more than one amount. Please give the corrected total loss as one amount before I confirm it.",
            LanguageCode.HI: "मुझे एक से अधिक राशि मिली है। पुष्टि से पहले कृपया कुल हानि एक राशि में बताएं।",
            LanguageCode.HINGLISH: "Mujhe ek se zyada amount mile hain. Confirm karne se pehle corrected total loss ek amount mein batayein.",
        }
        repeated_copy = {
            LanguageCode.EN: "A yes cannot select between these amounts. Enter the total numeric loss, for example ₹2,30,000.",
            LanguageCode.HI: "केवल हाँ से इन राशियों में चुनाव नहीं हो सकता। कुल हानि अंकों में लिखें, जैसे ₹2,30,000।",
            LanguageCode.HINGLISH: "Sirf haan se amounts select nahi ho sakte. Total loss numeric form mein likhein, jaise ₹2,30,000.",
        }
        copy = repeated_copy if repeated else first_copy
        return RoutedReply(copy.get(language, copy[LanguageCode.EN]), TurnKind.CONFIRMATION)

    @staticmethod
    def _confirm_pending_entities(state: ConversationState) -> None:
        pending = set(state.pending_confirmation_entity_ids)
        for entity in state.incident.entities:
            if entity.id in pending:
                entity.confirmed = True
        state.pending_confirmation_entity_ids = []
        state.incident.status = IncidentStatus.IDENTIFIED
        state.handoff = None
        state.pending_question = None

    @staticmethod
    def _next_question_after_confirmation(state: ConversationState) -> RoutedReply:
        """A confirmation must advance the citizen, never acknowledge and stop."""
        domain = state.incident.crime_domain
        record = CyberSaathiService._active_record(state)
        # A packet can surface newly extracted critical identifiers (for
        # example a UTR and transaction time) for explicit confirmation. Once
        # those packet values are confirmed, keep the citizen at the packet
        # stage instead of restarting the earlier amount/bank questionnaire.
        if record is not None and record.report_preparation.packet_ready:
            if CyberSaathiService._needs_optional_suspect_question(state):
                CyberSaathiService._set_pending_question(
                    state,
                    "optional_suspect_details",
                    ExpectedAnswerType.FREE_TEXT,
                )
                return RoutedReply(
                    CyberSaathiService._question_copy(
                        "optional_suspect_details", state.language
                    ),
                    TurnKind.MESSAGE,
                    GroundingStatus.DETERMINISTIC_PLAYBOOK,
                )
            copy = {
                LanguageCode.EN: "Those report details are confirmed. The incident packet is updated; review it and choose Prepare report draft when ready.",
                LanguageCode.HI: "रिपोर्ट की उन जानकारियों की पुष्टि हो गई है। घटना पैकेट अपडेट है; इसे जांचें और तैयार होने पर रिपोर्ट ड्राफ्ट तैयार करें चुनें।",
                LanguageCode.HINGLISH: "Report ki woh details confirm ho gayi hain. Incident packet update hai; review karke ready hone par Prepare report draft choose karein.",
            }
            return RoutedReply(
                copy.get(state.language, copy[LanguageCode.EN]),
                TurnKind.MESSAGE,
                GroundingStatus.DETERMINISTIC_PLAYBOOK,
            )
        if domain == CrimeDomain.FINANCIAL_FRAUD:
            completed = set(record.completed_actions) if record is not None else set()
            bank_protected = "bank_protection_requested" in completed
            bank_contacted = bank_protected or "bank_contacted" in completed
            if bank_contacted:
                return RoutedReply(
                    CyberSaathiService._financial_followup_question(
                        state,
                        record.report_preparation if record is not None else None,
                        bank_contacted=bank_contacted,
                        bank_protected=bank_protected,
                        fallback_playbook=CyberSaathiService._copy(
                            state.language, "progress_next"
                        ),
                    ),
                    TurnKind.MESSAGE,
                    GroundingStatus.DETERMINISTIC_PLAYBOOK,
                )
            CyberSaathiService._set_pending_question(
                state,
                "bank_contact_and_protect",
                ExpectedAnswerType.YES_NO,
            )
            copy = {
                LanguageCode.EN: "The amount is confirmed. Next, have you reported the unauthorized payment through your bank or UPI provider's official channel and asked it to block outgoing transactions?",
                LanguageCode.HI: "राशि की पुष्टि हो गई है। अब क्या आपने बैंक या UPI provider के आधिकारिक माध्यम से अनधिकृत भुगतान रिपोर्ट करके outgoing transactions रोकने को कहा है?",
                LanguageCode.HINGLISH: "Amount confirm ho gaya hai. Ab kya aapne bank ya UPI provider ke official channel se unauthorized payment report karke outgoing transactions block karne ko bola hai?",
            }
            return RoutedReply(copy.get(state.language, copy[LanguageCode.EN]), TurnKind.MESSAGE)
        return RoutedReply(
            CyberSaathiService._focused_question(domain, state.language),
            TurnKind.MESSAGE,
        )

    @staticmethod
    def _set_pending_question(
        state: ConversationState,
        key: str,
        answer_type: ExpectedAnswerType,
    ) -> None:
        incident_id = state.active_incident_id
        if incident_id is None:
            record = CyberSaathiService._active_record(state)
            incident_id = record.id if record is not None else None
        if incident_id is None:
            return
        if (
            state.pending_question is not None
            and state.pending_question.key == key
            and state.pending_question.incident_id == incident_id
        ):
            return
        state.pending_question = PendingQuestion(
            key=key,
            answer_type=answer_type,
            incident_id=incident_id,
        )

    @staticmethod
    def _is_contextual_confirmation(message: str) -> bool:
        normalized = normalized_text(message)
        if normalized in CONTEXTUAL_YES_MARKERS:
            return True
        return bool(
            re.search(
                r"\b(?:kar|kr|karva|karwa|krva|krwa|bol|bata)\s+diya(?:\s+hai)?\b",
                normalized,
            )
        )

    @staticmethod
    def _expected_answer_class(message: str) -> str:
        normalized = normalized_text(message)
        if CyberSaathiService._is_contextual_confirmation(message):
            return "yes"
        if normalized in NO_MARKERS:
            return "no"
        if normalized in UNCERTAIN_MARKERS:
            return "uncertain"
        return "other"

    @staticmethod
    def _confirmed_suspect_identifier(state: ConversationState) -> dict[str, str] | None:
        identifier_types = {
            EntityType.PHONE_NUMBER: "PHONE",
            EntityType.EMAIL: "EMAIL",
            EntityType.UPI_ID: "UPI",
            EntityType.ACCOUNT_ID: "BANK_ACCOUNT",
            EntityType.URL: "WEBSITE",
            EntityType.USERNAME: "SOCIAL_MEDIA",
        }
        entity = next(
            (item for item in reversed(state.incident.entities) if item.confirmed and item.type in identifier_types),
            None,
        )
        if entity is None:
            return None
        return {"identifier_type": identifier_types[entity.type], "identifier_value": entity.normalized_value or entity.value}

    @staticmethod
    def _report_handoff(state: ConversationState) -> WorkflowHandoff:
        record = CyberSaathiService._active_record(state)
        preparation = record.report_preparation if record is not None else None
        amount = next(
            (
                entity.normalized_value or entity.value
                for entity in reversed(state.incident.entities)
                if entity.type == EntityType.AMOUNT and entity.confirmed
            ),
            None,
        )
        incident_at = next(
            (
                entity.normalized_value or entity.value
                for entity in reversed(state.incident.entities)
                if entity.type == EntityType.DATE_TIME
            ),
            None,
        )
        if incident_at is None:
            incident_at = next(
                (
                    entity.normalized_value or entity.value
                    for entity in reversed(state.incident.entities)
                    if entity.type == EntityType.DATE
                ),
                None,
            )
        identifiers = [
            entity.normalized_value or entity.value
            for entity in state.incident.entities
            if entity.type in SUSPECT_IDENTIFIER_TYPES
        ]
        location = next(
            (
                entity.normalized_value or entity.value
                for entity in reversed(state.incident.entities)
                if entity.type == EntityType.LOCATION
            ),
            None,
        )
        city = location.title() if location else None
        state_name = CITY_STATE_BY_CITY.get(location.casefold()) if location else None
        suspect_details = preparation.suspect_details if preparation is not None else None
        suspect_name, suspect_alias = CyberSaathiService._suspect_name_and_alias(
            suspect_details
        )
        domain_label = state.incident.crime_domain.value.replace("_", " ").title()
        return WorkflowHandoff(
            target=HandoffTarget.REPORT_CRIME,
            reporting_mode=state.reporting_mode,
            route="/report-crime",
            prefill=ComplaintPrefill(
                title=f"Cyber Saathi - {domain_label}",
                description=state.incident.summary,
                crime_domain=state.incident.crime_domain,
                related_domains=state.incident.related_domains,
                financial_loss_amount=amount,
                incident_at=incident_at,
                suspect_identifiers=identifiers[:20],
                suspect_details=suspect_details,
                suspect_name=suspect_name,
                suspect_alias=suspect_alias,
                city=city,
                state=state_name,
                reporting_for=(
                    preparation.reporting_for if preparation is not None else "UNKNOWN"
                ),
                affected_person_name=(
                    preparation.affected_person_name if preparation is not None else None
                ),
                attachment_ids=(
                    [item.id for item in preparation.attachments]
                    if preparation is not None
                    else []
                ),
            ),
        )

    @staticmethod
    def _is_confirmation(message: str) -> bool:
        return message.strip().casefold() in YES_MARKERS

    @staticmethod
    def _blocked_action_copy(
        language: LanguageCode,
        action: str,
        domain: CrimeDomain,
        escalated: bool,
    ) -> str:
        if action == "screenshot":
            copy = {
                LanguageCode.EN: "That is okay—do not stop the report only because a screenshot is unavailable. Preserve any order confirmation, transaction statement, URL, email/SMS, chat export, profile name, and approximate date/time you still have. Which one of these is available?",
                LanguageCode.HI: "ठीक है—स्क्रीनशॉट न होने से रिपोर्ट न रोकें। उपलब्ध ऑर्डर पुष्टि, लेन-देन विवरण, URL, ईमेल/SMS, चैट एक्सपोर्ट, प्रोफाइल नाम और अनुमानित तारीख/समय सुरक्षित रखें। इनमें से क्या उपलब्ध है?",
                LanguageCode.HINGLISH: "Theek hai—screenshot na hone se report mat rokiye. Available order confirmation, transaction statement, URL, email/SMS, chat export, profile name aur approximate date/time safe rakhein. Inmein se kya available hai?",
            }
        elif action == "bank_contact":
            copy = {
                LanguageCode.EN: "If the bank's main line is unreachable, use only the official app, card-back number, branch, or official website support channel. Keep failed-call times as part of your notes and do not use a number sent by the caller. Which official channel can you access?",
                LanguageCode.HI: "यदि बैंक की मुख्य लाइन नहीं मिल रही, केवल आधिकारिक ऐप, कार्ड के पीछे का नंबर, शाखा या आधिकारिक वेबसाइट सहायता उपयोग करें। असफल कॉल का समय लिखें और कॉलर द्वारा भेजा नंबर उपयोग न करें। कौन सा आधिकारिक माध्यम उपलब्ध है?",
                LanguageCode.HINGLISH: "Bank main line na mile to sirf official app, card-back number, branch ya official website support use karein. Failed calls ka time note karein aur caller ka diya number use na karein. Kaunsa official channel available hai?",
            }
        else:
            copy = {
                LanguageCode.EN: "I understand that step is not possible. Do not keep retrying the same unsafe or unavailable route. Tell me exactly what stopped you, and I will offer one practical alternative while preserving the report details.",
                LanguageCode.HI: "मैं समझता हूं कि यह कदम संभव नहीं है। उसी अनुपलब्ध या असुरक्षित तरीके को बार-बार न आजमाएं। बताएं क्या बाधा आई, मैं रिपोर्ट विवरण रखते हुए एक व्यावहारिक विकल्प दूंगा।",
                LanguageCode.HINGLISH: "Samajh gaya ki ye step possible nahi hai. Same unavailable ya unsafe route baar-baar retry mat karein. Exact blocker batayein; report details safe rakhte hue main ek practical alternative dunga.",
            }
        answer = copy.get(language, copy[LanguageCode.EN])
        if escalated:
            escalation = {
                LanguageCode.EN: (
                    " You have been blocked several times, so stop repeating failed steps and get human help now."
                    + (" For an urgent financial-fraud incident, call 1930." if domain == CrimeDomain.FINANCIAL_FRAUD else " If anyone is in immediate physical danger, use the appropriate emergency service.")
                ),
                LanguageCode.HI: (
                    " कई बार बाधा आने के कारण वही असफल कदम दोहराना बंद करें और अभी मानवीय सहायता लें।"
                    + (" तत्काल वित्तीय धोखाधड़ी के लिए 1930 पर कॉल करें।" if domain == CrimeDomain.FINANCIAL_FRAUD else " किसी को तत्काल शारीरिक खतरा हो तो उपयुक्त आपात सेवा लें।")
                ),
                LanguageCode.HINGLISH: (
                    " Kai baar blocker aaya hai, isliye same failed steps repeat na karein aur ab human help lein."
                    + (" Urgent financial fraud ke liye 1930 call karein." if domain == CrimeDomain.FINANCIAL_FRAUD else " Immediate physical danger ho to appropriate emergency service use karein.")
                ),
            }
            answer += escalation.get(language, escalation[LanguageCode.EN])
        return answer

    @staticmethod
    def _copy(language: LanguageCode, key: str) -> str:
        copy = {
            "welcome": {
                LanguageCode.EN: "Namaste. Tell me what happened online, in your own words. I will help you choose a safe next step.",
                LanguageCode.HI: "नमस्ते। ऑनलाइन क्या हुआ, अपने शब्दों में बताइए। मैं सुरक्षित अगला कदम चुनने में आपकी मदद करूंगा।",
                LanguageCode.HINGLISH: "Namaste. Online kya hua, apne words mein batayein. Main safe next step choose karne mein help karunga.",
            },
            "financial_safety": {
                LanguageCode.EN: "1. Contact the bank or payment provider through an official channel—its app, website, or card-back number—and ask it to block outgoing transactions.\n2. Do not send more money or share an OTP/PIN/password.\n3. Preserve screenshots, transaction details, the provider reference, and the conversation as evidence.",
                LanguageCode.HI: "1. बैंक या भुगतान प्रदाता के आधिकारिक माध्यम—ऐप, वेबसाइट या कार्ड के पीछे दिए नंबर—से संपर्क करके outgoing transactions रोकने को कहें।\n2. और पैसे न भेजें तथा OTP/PIN/password साझा न करें।\n3. स्क्रीनशॉट, ट्रांज़ैक्शन विवरण, प्रदाता रेफरेंस और बातचीत को प्रमाण के रूप में सुरक्षित रखें।",
                LanguageCode.HINGLISH: "1. Bank/payment provider ke official channel—app, website ya card-back number—se contact karke outgoing transactions block karwayein.\n2. Aur paise na bhejein aur OTP/PIN/password share na karein.\n3. Screenshots, transaction details, provider reference aur chat ko evidence ke taur par preserve karein.",
            },
            "confirm_amount": {
                LanguageCode.EN: "I understood the amount as ₹{amount}. Is that correct?",
                LanguageCode.HI: "मैंने राशि ₹{amount} समझी है। क्या यह सही है?",
                LanguageCode.HINGLISH: "Maine amount ₹{amount} samjha hai. Kya ye correct hai?",
            },
            "confirmed": {
                LanguageCode.EN: "Confirmed. I saved those values. I will keep asking only for details still required before a report can continue.",
                LanguageCode.HI: "पुष्टि हो गई। ये विवरण सुरक्षित हैं। रिपोर्ट जारी होने से पहले मैं केवल बाकी जरूरी जानकारी पूछूंगा।",
                LanguageCode.HINGLISH: "Confirm ho gaya. Ye values save hain. Report continue hone se pehle main sirf remaining required details poochunga.",
            },
            "updated_detail": {
                LanguageCode.EN: "I updated the corrected detail; I will not repeat the earlier safety checklist.",
                LanguageCode.HI: "मैंने सही किया गया विवरण अपडेट कर दिया है; पहले वाली सुरक्षा सूची दोबारा नहीं दोहराऊंगा।",
                LanguageCode.HINGLISH: "Maine corrected detail update kar di; pehli safety checklist repeat nahi karunga.",
            },
            "bank_contacted_next": {
                LanguageCode.EN: "Good—you have contacted the bank. Save its complaint/reference number. If the loss was recent and you have not done so, call 1930 and prepare the cybercrime report. Did the bank give you a reference number, or have you called 1930?",
                LanguageCode.HI: "ठीक है—आपने बैंक से संपर्क कर लिया है। शिकायत/रेफरेंस नंबर सुरक्षित रखें। हानि हाल की है तो 1930 पर कॉल करें और साइबर अपराध रिपोर्ट तैयार करें। क्या बैंक ने रेफरेंस नंबर दिया, या आपने 1930 पर कॉल किया?",
                LanguageCode.HINGLISH: "Achha—bank contact ho gaya. Complaint/reference number safe rakhein. Loss recent hai aur abhi nahi kiya to 1930 call karke cybercrime report ready karein. Bank reference number mila, ya 1930 call kiya?",
            },
            "all_done_next": {
                LanguageCode.EN: "Good—the immediate safety steps are complete. The next step is to review and submit the incident report; if it is already reported, keep the acknowledgement for tracking. Do you want to continue with this report now?",
                LanguageCode.HI: "ठीक है—तत्काल सुरक्षा कदम पूरे हो गए हैं। अगला कदम घटना रिपोर्ट की समीक्षा और सबमिशन है; यदि रिपोर्ट हो चुकी है तो ट्रैकिंग के लिए पावती रखें। क्या आप अब इस रिपोर्ट को जारी रखना चाहते हैं?",
                LanguageCode.HINGLISH: "Achha—immediate safety steps complete hain. Ab incident report review karke submit karein; already report kiya hai to tracking ke liye acknowledgement rakhein. Kya ab is report ko continue karna hai?",
            },
            "ecommerce_all_done_next": {
                LanguageCode.EN: "Good—the seller/platform contact and evidence steps are complete. If it remains unresolved, the next option is an official National Consumer Helpline grievance; keep the NCH docket number for follow-up. Has the seller replied, or do you want to prepare the NCH grievance?",
                LanguageCode.HI: "ठीक है—विक्रेता/प्लेटफॉर्म संपर्क और प्रमाण के कदम पूरे हैं। समस्या हल न हो तो राष्ट्रीय उपभोक्ता हेल्पलाइन में आधिकारिक शिकायत अगला विकल्प है; NCH डॉकेट नंबर सुरक्षित रखें। क्या विक्रेता ने उत्तर दिया, या आप NCH शिकायत तैयार करना चाहते हैं?",
                LanguageCode.HINGLISH: "Achha—seller/platform contact aur evidence steps complete hain. Issue unresolved hai to official National Consumer Helpline grievance next option hai; NCH docket number safe rakhein. Seller ne reply diya, ya NCH grievance prepare karna hai?",
            },
            "progress_next": {
                LanguageCode.EN: "I have kept the earlier incident details. Tell me which safety step you completed, and I will give only the next missing step. Have you contacted the bank/provider and saved its reference number?",
                LanguageCode.HI: "मैंने पहले की घटना का विवरण सुरक्षित रखा है। बताएं कौन सा सुरक्षा कदम पूरा हुआ, मैं केवल अगला बाकी कदम बताऊंगा। क्या आपने बैंक/प्रदाता से संपर्क करके रेफरेंस नंबर सुरक्षित किया?",
                LanguageCode.HINGLISH: "Pehle incident details mere paas hain. Batayein kaunsa safety step complete hua; main sirf next missing step bataunga. Bank/provider contact karke reference number save kiya?",
            },
            "finish_active_first": {
                LanguageCode.EN: "The current incident is not ready yet. I have kept the other incident queued; let us finish this one first.",
                LanguageCode.HI: "मौजूदा घटना अभी तैयार नहीं है। दूसरी घटना कतार में सुरक्षित है; पहले इसे पूरा करते हैं।",
                LanguageCode.HINGLISH: "Current incident abhi ready nahi hai. Doosra incident queue mein safe hai; pehle isko complete karte hain.",
            },
            "no_queued_incident": {
                LanguageCode.EN: "There is no other queued incident in this chat. Tell me if a separate event happened and I will keep it apart from the current one.",
                LanguageCode.HI: "इस चैट में कोई दूसरी घटना कतार में नहीं है। अलग घटना हुई हो तो बताएं, मैं उसे मौजूदा घटना से अलग रखूंगा।",
                LanguageCode.HINGLISH: "Is chat mein koi queued incident nahi hai. Separate event hua ho to batayein; main current incident se alag rakhunga.",
            },
            "activated_incident": {
                LanguageCode.EN: "Now working on incident #{number}: {domain}.",
                LanguageCode.HI: "अब घटना #{number}: {domain} पर काम कर रहे हैं।",
                LanguageCode.HINGLISH: "Ab incident #{number}: {domain} par kaam kar rahe hain.",
            },
            "track": {
                LanguageCode.EN: "I can take you to complaint tracking. Keep your complaint number ready; I do not have live access to police or government systems.",
                LanguageCode.HI: "मैं आपको शिकायत ट्रैकिंग पर ले जा सकता हूं। शिकायत नंबर तैयार रखें; मेरे पास पुलिस या सरकारी सिस्टम की लाइव पहुंच नहीं है।",
                LanguageCode.HINGLISH: "Main aapko complaint tracking par le ja sakta hoon. Complaint number ready rakhein; mere paas police ya government systems ka live access nahi hai.",
            },
            "cyber_warrior_handoff": {
                LanguageCode.EN: "I can take you to the Cyber Warrior programme, where you can learn about the role and start an application.",
                LanguageCode.HI: "मैं आपको साइबर वॉरियर कार्यक्रम पर ले जा सकता हूं, जहां आप भूमिका के बारे में जानकर आवेदन शुरू कर सकते हैं।",
                LanguageCode.HINGLISH: "Main aapko Cyber Warrior programme par le ja sakta hoon, jahan role samajhkar application start kar sakte hain.",
            },
            "learning_resources_handoff": {
                LanguageCode.EN: "I can take you to practical cyber-safety resources. Choose a topic there to learn the relevant warning signs and safe actions.",
                LanguageCode.HI: "मैं आपको व्यावहारिक साइबर सुरक्षा संसाधनों पर ले जा सकता हूं। संबंधित चेतावनी संकेत और सुरक्षित कदम जानने के लिए वहां विषय चुनें।",
                LanguageCode.HINGLISH: "Main aapko practical cyber-safety resources par le ja sakta hoon. Warning signs aur safe actions ke liye wahan topic choose karein.",
            },
            "search_suspect_handoff": {
                LanguageCode.EN: "I can take you to the exact identifier search. I have not performed a live lookup in this chat, and a reported signal never proves that a person or identifier is criminal.",
                LanguageCode.HI: "मैं आपको पूरे पहचानकर्ता की खोज पर ले जा सकता हूं। इस चैट में मैंने कोई लाइव lookup नहीं किया है, और रिपोर्टेड संकेत किसी व्यक्ति या पहचानकर्ता को अपराधी साबित नहीं करता।",
                LanguageCode.HINGLISH: "Main aapko exact identifier search par le ja sakta hoon. Is chat mein maine live lookup nahi kiya hai, aur reported signal kisi person ya identifier ko criminal prove nahi karta.",
            },
            "secure_india_handoff": {
                LanguageCode.EN: "I can open the interactive Secure India prototype. It uses a clearly labelled synthetic dataset and does not show live crime, police, government, or complaint data.",
                LanguageCode.HI: "मैं इंटरैक्टिव सिक्योर इंडिया प्रोटोटाइप खोल सकता हूं। इसमें स्पष्ट रूप से चिह्नित कृत्रिम डेटासेट है और लाइव अपराध, पुलिस, सरकारी या शिकायत डेटा नहीं दिखता।",
                LanguageCode.HINGLISH: "Main interactive Secure India prototype khol sakta hoon. Isme clearly labelled synthetic dataset hai aur live crime, police, government ya complaint data nahi dikhaya jata.",
            },
            "report": {
                LanguageCode.EN: "I can open the reporting flow with the incident description prepared. You will review every detail before submission.",
                LanguageCode.HI: "मैं घटना विवरण तैयार करके रिपोर्टिंग प्रक्रिया खोल सकता हूं। सबमिट करने से पहले आप हर जानकारी की समीक्षा करेंगे।",
                LanguageCode.HINGLISH: "Main incident description ready karke reporting flow open kar sakta hoon. Submit karne se pehle aap har detail review karenge.",
            },
            "clarify": {
                LanguageCode.EN: "I am not fully certain yet. Was money lost, was an account accessed, did someone threaten you, or did you receive a suspicious link or message?",
                LanguageCode.HI: "मुझे अभी पूरी तरह स्पष्ट नहीं है। क्या पैसे गए, अकाउंट एक्सेस हुआ, किसी ने धमकी दी, या कोई संदिग्ध लिंक या संदेश मिला?",
                LanguageCode.HINGLISH: "Mujhe abhi fully clear nahi hai. Kya paise gaye, account access hua, kisi ne threaten kiya, ya suspicious link/message mila?",
            },
            "guidance": {
                LanguageCode.EN: "Preserve the relevant messages and screenshots, avoid further contact or payments, and use the official reporting flow when you are ready.",
                LanguageCode.HI: "संबंधित संदेश और स्क्रीनशॉट सुरक्षित रखें, आगे संपर्क या भुगतान न करें, और तैयार होने पर आधिकारिक रिपोर्टिंग प्रक्रिया का उपयोग करें।",
                LanguageCode.HINGLISH: "Relevant messages aur screenshots safe rakhein, aage contact ya payment na karein, aur ready hone par official reporting flow use karein.",
            },
            "grounded_intro": {
                LanguageCode.EN: "Relevant official guidance:",
                LanguageCode.HI: "संबंधित आधिकारिक मार्गदर्शन:",
                LanguageCode.HINGLISH: "Relevant official guidance:",
            },
            "knowledge_no_result": {
                LanguageCode.EN: "I could not find sufficiently relevant official guidance for that yet. Please tell me what happened, which account or device was involved, and whether money was lost or someone threatened you.",
                LanguageCode.HI: "मुझे अभी इसके लिए पर्याप्त रूप से संबंधित आधिकारिक मार्गदर्शन नहीं मिला। कृपया बताएं कि क्या हुआ, कौन सा अकाउंट या डिवाइस शामिल था, और क्या पैसे गए या किसी ने धमकी दी।",
                LanguageCode.HINGLISH: "Mujhe abhi iske liye sufficiently relevant official guidance nahi mili. Batayein kya hua, kaunsa account ya device involved tha, aur kya paise gaye ya kisi ne threaten kiya.",
            },
        }
        localized = copy[key]
        return localized.get(language, localized[LanguageCode.EN])
