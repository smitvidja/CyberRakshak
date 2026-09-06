from dataclasses import dataclass, field
from datetime import datetime, timezone
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
    GroundingStatus,
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
BANK_CONTACT_MARKERS = (
    "called the bank", "contacted the bank", "bank complaint", "bank ko call",
    "bank me call", "bank mein call", "bank se baat", "bank contact",
)
ALL_DONE_MARKERS = (
    "all done", "did all", "done everything", "sab kar liya", "sab kr liya",
    "ye sab kar liya", "ye sab kr liya", "everything complete",
)


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
    def start(payload: ConversationCreate) -> ConversationResponse:
        welcome = CyberSaathiService._copy(payload.language, "welcome")
        state = ConversationState(
            language=payload.language,
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
        language = understanding.response_language
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
            CyberSaathiService._confirm_pending_entities(state)
            routed = RoutedReply(
                content=CyberSaathiService._copy(language, "confirmed"),
                kind=TurnKind.HANDOFF,
            )
        elif state.pending_confirmation_entity_ids and understanding.entities:
            purpose = TurnPurpose.CORRECTION
            routed = CyberSaathiService._revise_pending_entities(state, understanding.entities)
        elif purpose == TurnPurpose.ACTION_BLOCKED:
            routed = CyberSaathiService._route_blocked_action(
                state, payload.message, understanding
            )
        elif purpose == TurnPurpose.REPORT_PREPARATION:
            routed = CyberSaathiService._prepare_report(state)
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
        else:
            routed = CyberSaathiService._route_mock_message(
                state, payload.message, understanding
            )

        CyberSaathiService._sync_active_incident(state)
        CyberSaathiService._refresh_report_preparation(state)
        if (
            state.handoff is not None
            and state.incident.crime_domain != CrimeDomain.ECOMMERCE_FRAUD
        ):
            state.handoff = CyberSaathiService._report_handoff(state)
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
        return ConversationResponse(state=state, mock_provider=routed.llm_provider is None)

    @staticmethod
    def _handle_reporting_mode_selection(state: ConversationState) -> RoutedReply:
        state.incident.status = IncidentStatus.READY_TO_REPORT
        state.handoff = (
            None
            if state.incident.crime_domain == CrimeDomain.ECOMMERCE_FRAUD
            else CyberSaathiService._report_handoff(state)
        )
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
    def _prepare_report(state: ConversationState) -> RoutedReply:
        record = CyberSaathiService._active_record(state)
        if record is None:
            return RoutedReply(CyberSaathiService._copy(state.language, "clarify"), TurnKind.MESSAGE)
        record.report_preparation = build_report_preparation(state, record)
        state.incident.status = IncidentStatus.READY_TO_REPORT
        state.pending_confirmation_entity_ids = [
            entity.id
            for entity in state.incident.entities
            if entity.requires_confirmation and not entity.confirmed
        ]
        state.handoff = (
            None
            if state.incident.crime_domain == CrimeDomain.ECOMMERCE_FRAUD
            else CyberSaathiService._report_handoff(state)
        )
        if state.incident.crime_domain == CrimeDomain.ECOMMERCE_FRAUD:
            return RoutedReply(
                CyberSaathiService._copy(state.language, "ecommerce_all_done_next"),
                TurnKind.MESSAGE,
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
        return RoutedReply(copy.get(state.language, copy[LanguageCode.EN]), TurnKind.HANDOFF)

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
            GroundingStatus.GROUNDED if retrieval.matches else GroundingStatus.DETERMINISTIC_PLAYBOOK,
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
        if (
            next_state.handoff is not None
            and next_state.incident.crime_domain != CrimeDomain.ECOMMERCE_FRAUD
        ):
            next_state.handoff = CyberSaathiService._report_handoff(next_state)
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
        state.incident.entities = [
            entity
            for entity in state.incident.entities
            if entity.type not in replacement_types
        ] + applicable
        state.pending_confirmation_entity_ids = [entity.id for entity in applicable]
        state.incident.status = IncidentStatus.AWAITING_CONFIRMATION
        return RoutedReply(
            CyberSaathiService._copy(state.language, "updated_detail")
            + " "
            + CyberSaathiService._confirmation_copy(state.language, applicable),
            TurnKind.CONFIRMATION,
        )

    @staticmethod
    def _is_progress_followup(state: ConversationState, message: str) -> bool:
        if not state.incident.summary:
            return False
        lowered = message.casefold()
        return (
            any(marker in lowered for marker in BANK_CONTACT_MARKERS)
            or any(marker in lowered for marker in ALL_DONE_MARKERS)
            or any(marker in lowered for marker in ("what next", "ab kya", "now what"))
        )

    @staticmethod
    def _route_progress_followup(
        state: ConversationState, message: str, understanding: UnderstandingResult
    ) -> RoutedReply:
        lowered = message.casefold()
        record = CyberSaathiService._active_record(state)
        actions = record.completed_actions if record is not None else []
        all_done = any(marker in lowered for marker in ALL_DONE_MARKERS)
        bank_contacted = any(marker in lowered for marker in BANK_CONTACT_MARKERS)
        if bank_contacted and "bank_contacted" not in actions:
            actions.append("bank_contacted")
        if all_done:
            for action in ("bank_contacted", "evidence_preserved", "urgent_report_considered"):
                if action not in actions:
                    actions.append(action)
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
            playbook = CyberSaathiService._progress_copy(
                state.incident.crime_domain, state.language
            )

        augmented = f"{state.incident.summary or ''} Follow-up: {message}"
        effective = understanding.model_copy(
            update={"crime_domain": state.incident.crime_domain}
        )
        retrieval = CyberSaathiService._retrieve_knowledge(augmented, effective)
        if retrieval.matches:
            generated = get_llm_gateway().generate(
                state=state,
                user_message=message,
                knowledge_context=retrieval.bounded_context,
                source_ids=[match.chunk_id for match in retrieval.matches],
                deterministic_playbook=playbook,
            )
            if generated.response is not None:
                answer = CyberSaathiService._ensure_focused_question(
                    generated.response.answer, state.incident.crime_domain, state.language
                )
                cited = set(generated.response.sources)
                cited_matches = [
                    match for match in retrieval.matches if match.chunk_id in cited
                ]
                return RoutedReply(
                    answer,
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
            return RoutedReply(
                playbook,
                TurnKind.MESSAGE,
                GroundingStatus.GROUNDED,
                CyberSaathiService._conversation_sources(retrieval.matches[:1]),
                retrieval.retrieval_latency_ms,
                llm_fallback_used=generated.fallback_used,
                llm_latency_ms=generated.latency_ms,
                safety_flags=["deterministic_progress_fallback"],
            )
        return RoutedReply(
            playbook,
            TurnKind.MESSAGE,
            GroundingStatus.DETERMINISTIC_PLAYBOOK,
            retrieval_latency_ms=retrieval.retrieval_latency_ms,
        )

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
            state.handoff = CyberSaathiService._report_handoff(state)
            safety = CyberSaathiService._with_sentiment_strategy(
                language,
                understanding.sentiment,
                CyberSaathiService._copy(language, "financial_safety"),
            )
            if pending_entities:
                safety += " " + CyberSaathiService._confirmation_copy(
                    language, pending_entities
                )
            retrieval = CyberSaathiService._retrieve_knowledge(message, understanding)
            return RoutedReply(
                safety,
                TurnKind.SAFETY,
                (
                    GroundingStatus.GROUNDED
                    if retrieval.matches
                    else GroundingStatus.DETERMINISTIC_PLAYBOOK
                ),
                CyberSaathiService._conversation_sources(retrieval.matches[:1]),
                retrieval.retrieval_latency_ms,
            )

        if (
            intent == Intent.REPORT_INCIDENT
            and crime_domain != CrimeDomain.ECOMMERCE_FRAUD
            and not understanding.needs_clarification
        ):
            state.incident.status = (
                IncidentStatus.AWAITING_CONFIRMATION
                if pending_entities
                else IncidentStatus.READY_TO_REPORT
            )
            state.handoff = CyberSaathiService._report_handoff(state)
            if pending_entities:
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
                answer = CyberSaathiService._ensure_focused_question(
                    (
                    CyberSaathiService._copy(language, "grounded_intro")
                    + " "
                    + retrieval.matches[0].text
                    ),
                    crime_domain,
                    language,
                )
                return RoutedReply(
                    CyberSaathiService._with_sentiment_strategy(
                        language, response_understanding.sentiment, answer
                    ),
                    TurnKind.MESSAGE,
                    GroundingStatus.GROUNDED,
                    CyberSaathiService._conversation_sources(retrieval.matches[:1]),
                    retrieval.retrieval_latency_ms,
                    llm_fallback_used=generated.fallback_used,
                    llm_latency_ms=generated.latency_ms,
                    safety_flags=["deterministic_grounded_fallback"],
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
        message: str, understanding: UnderstandingResult
    ) -> KnowledgeSearchResponse:
        normalized_message = normalized_text(message)
        domain = CyberSaathiService._knowledge_domain(normalized_message, understanding)
        query_expansions = {
            KnowledgeDomain.FINANCIAL_FRAUD: "unauthorized transaction bank fraud money loss",
            KnowledgeDomain.UPI_PAYMENT_FRAUD: "upi payment qr wallet fraud transaction",
            KnowledgeDomain.PHISHING: "phishing suspicious link otp password credential",
            KnowledgeDomain.ACCOUNT_COMPROMISE: "hacked account access password recovery",
            KnowledgeDomain.IMPERSONATION: "fake officer profile impersonation digital arrest",
            KnowledgeDomain.HARASSMENT_ABUSE: "online harassment abuse threats preserve evidence",
            KnowledgeDomain.WOMEN_CHILD_ONLINE_SAFETY: "image morphing fake profile minor child women harassment blackmail",
            KnowledgeDomain.CYBERSTALKING: "cyberstalking location tracking threats evidence",
            KnowledgeDomain.MALWARE_DEVICE_COMPROMISE: "malware apk remote access compromised device",
            KnowledgeDomain.IDENTITY_THEFT: "identity theft personal information fake profile",
            KnowledgeDomain.ECOMMERCE_CONSUMER_GRIEVANCE: "online order delivery refund seller website payment proof",
        }
        retrieval_query = " ".join(
            part for part in (normalized_message, query_expansions.get(domain)) if part
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
            return CyberSaathiService._apply_audience_guard(retrieval_query, response)
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
            )

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
        message: str, response: KnowledgeSearchResponse
    ) -> KnowledgeSearchResponse:
        lowered = message.casefold()
        audience_terms = (
            "child", "minor", "kid", "teen", "girl", "woman", "women", "mahila",
            "बच्च", "नाबालिग", "महिला", "लड़की", "morphed", "intimate image",
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
        harassment_domains = {
            CrimeDomain.ONLINE_HARASSMENT,
            CrimeDomain.WOMEN_CHILD_ONLINE_SAFETY,
            CrimeDomain.CHILD_SAFETY,
            CrimeDomain.CYBERSTALKING,
        }
        if domain in harassment_domains:
            localized = {
                LanguageCode.EN: "Is anyone in immediate danger, and have you preserved the original messages, profile URL, and screenshots?",
                LanguageCode.HI: "क्या किसी को तत्काल खतरा है, और क्या आपने मूल संदेश, प्रोफाइल URL और स्क्रीनशॉट सुरक्षित किए हैं?",
                LanguageCode.HINGLISH: "Kya koi immediate danger mein hai, aur original messages, profile URL aur screenshots safe hain?",
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
        return f"{prefix} {response}"

    @staticmethod
    def _confirmation_copy(language: LanguageCode, entities: list[Entity]) -> str:
        values = ", ".join(f"{entity.type.value}: {entity.value}" for entity in entities)
        copy = {
            LanguageCode.EN: f"Please confirm these details before I use them: {values}.",
            LanguageCode.HI: f"इन विवरणों की पुष्टि करें: {values}।",
            LanguageCode.HINGLISH: f"In details ko confirm karein: {values}.",
        }
        return copy.get(language, copy[LanguageCode.EN])

    @staticmethod
    def _confirm_pending_entities(state: ConversationState) -> None:
        pending = set(state.pending_confirmation_entity_ids)
        for entity in state.incident.entities:
            if entity.id in pending:
                entity.confirmed = True
        state.pending_confirmation_entity_ids = []
        state.incident.status = IncidentStatus.READY_TO_REPORT
        state.handoff = CyberSaathiService._report_handoff(state)

    @staticmethod
    def _report_handoff(state: ConversationState) -> WorkflowHandoff:
        record = CyberSaathiService._active_record(state)
        preparation = record.report_preparation if record is not None else None
        amount = next(
            (
                entity.normalized_value or entity.value
                for entity in state.incident.entities
                if entity.type == EntityType.AMOUNT
            ),
            None,
        )
        incident_at = next(
            (
                entity.normalized_value or entity.value
                for entity in state.incident.entities
                if entity.type in {EntityType.DATE, EntityType.DATE_TIME}
            ),
            None,
        )
        identifiers = [
            entity.normalized_value or entity.value
            for entity in state.incident.entities
            if entity.type
            in {
                EntityType.PHONE_NUMBER,
                EntityType.UPI_ID,
                EntityType.TRANSACTION_ID,
                EntityType.URL,
                EntityType.EMAIL,
                EntityType.USERNAME,
                EntityType.ACCOUNT_ID,
            }
        ]
        domain_label = state.incident.crime_domain.value.replace("_", " ").title()
        return WorkflowHandoff(
            target=HandoffTarget.REPORT_CRIME,
            reporting_mode=state.reporting_mode,
            route="/report-crime",
            prefill=ComplaintPrefill(
                title=f"Cyber Saathi - {domain_label}",
                description=state.incident.summary,
                crime_domain=state.incident.crime_domain,
                financial_loss_amount=amount,
                incident_at=incident_at,
                suspect_identifiers=identifiers[:20],
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
                LanguageCode.EN: "Act promptly: preserve screenshots and transaction details, contact your bank or payment provider through its official channel, record the reference number, do not share an OTP/PIN/password, do not send more money, and keep the conversation as evidence.",
                LanguageCode.HI: "जल्दी कदम उठाएं: स्क्रीनशॉट और ट्रांज़ैक्शन विवरण सुरक्षित रखें, आधिकारिक माध्यम से बैंक या भुगतान प्रदाता से संपर्क करें, रेफरेंस नंबर लिखें, OTP/PIN/पासवर्ड साझा न करें, और पैसे न भेजें। बातचीत को सबूत के रूप में सुरक्षित रखें।",
                LanguageCode.HINGLISH: "Jaldi action lein: screenshots aur transaction details safe rakhein, official channel se bank/payment provider ko contact karein, reference number note karein, OTP/PIN/password share na karein, aur paise na bhejein. Chat evidence delete na karein.",
            },
            "confirm_amount": {
                LanguageCode.EN: "I understood the amount as ₹{amount}. Is that correct?",
                LanguageCode.HI: "मैंने राशि ₹{amount} समझी है। क्या यह सही है?",
                LanguageCode.HINGLISH: "Maine amount ₹{amount} samjha hai. Kya ye correct hai?",
            },
            "confirmed": {
                LanguageCode.EN: "Confirmed. I can now take these incident details into the reporting flow. Choose anonymous or identified reporting before continuing.",
                LanguageCode.HI: "पुष्टि हो गई। अब इन घटना विवरणों को रिपोर्टिंग प्रक्रिया में ले जाया जा सकता है। आगे बढ़ने से पहले गुमनाम या पहचान सहित रिपोर्ट चुनें।",
                LanguageCode.HINGLISH: "Confirm ho gaya. Ab incident details reporting flow mein le ja sakte hain. Continue karne se pehle anonymous ya identified reporting choose karein.",
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
