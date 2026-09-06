from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID

from app.core.errors import APIError
from app.schemas.cyber_saathi import (
    ComplaintPrefill,
    ConversationCreate,
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
    IncidentStatus,
    Intent,
    KnowledgeDomain,
    KnowledgeMatch,
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    LanguageCode,
    ReportingMode,
    Sentiment,
    TurnKind,
    Urgency,
    UnderstandingResult,
    WorkflowHandoff,
)
from app.services.cyber_saathi_knowledge import KnowledgeService
from app.services.cyber_saathi_understanding import UnderstandingEngine


YES_MARKERS = {"yes", "correct", "confirm", "haan", "ha", "हाँ", "सही"}


@dataclass
class RoutedReply:
    content: str
    kind: TurnKind
    grounding_status: GroundingStatus = GroundingStatus.NOT_USED
    sources: list[ConversationSource] = field(default_factory=list)
    retrieval_latency_ms: float | None = None


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
            and effective_domain != CrimeDomain.CHILD_SAFETY
        ):
            raise APIError(
                status_code=403,
                code="ANONYMOUS_REPORTING_NOT_AVAILABLE",
                message="Anonymous reporting is available only for Women and Child Safety incidents.",
            )
        state.language = language
        state.turns.append(
            ConversationTurn(role="user", content=payload.message.strip(), language=language)
        )

        if state.pending_confirmation_entity_ids and CyberSaathiService._is_confirmation(payload.message):
            CyberSaathiService._confirm_pending_entities(state)
            routed = RoutedReply(
                content=CyberSaathiService._copy(language, "confirmed"),
                kind=TurnKind.HANDOFF,
            )
        else:
            routed = CyberSaathiService._route_mock_message(
                state, payload.message, understanding
            )

        state.turns.append(
            ConversationTurn(
                role="assistant",
                content=routed.content,
                language=language,
                kind=routed.kind,
                grounding_status=routed.grounding_status,
                sources=routed.sources,
                retrieval_latency_ms=routed.retrieval_latency_ms,
            )
        )
        state.updated_at = datetime.now(timezone.utc)
        return ConversationResponse(state=state)

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
        entities = understanding.entities
        pending_entities = [entity for entity in entities if entity.requires_confirmation]
        state.pending_confirmation_entity_ids = [entity.id for entity in pending_entities]
        state.incident = IncidentState(
            status=(
                IncidentStatus.AWAITING_CONFIRMATION
                if pending_entities
                else IncidentStatus.IDENTIFIED
            ),
            intent=intent,
            crime_domain=crime_domain,
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

        if crime_domain == CrimeDomain.FINANCIAL_FRAUD:
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

        if intent == Intent.REPORT_INCIDENT and not understanding.needs_clarification:
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

        if not understanding.needs_clarification and (
            understanding.intent in {Intent.SEEK_GUIDANCE, Intent.GENERAL_AWARENESS}
            or (
                understanding.confidence_band.value == "high"
                and crime_domain != CrimeDomain.UNKNOWN
            )
        ):
            retrieval = CyberSaathiService._retrieve_knowledge(message, understanding)
            if retrieval.matches:
                state.incident.status = IncidentStatus.GUIDANCE_GIVEN
                answer = (
                    CyberSaathiService._copy(language, "grounded_intro")
                    + " "
                    + retrieval.matches[0].text
                )
                return RoutedReply(
                    CyberSaathiService._with_sentiment_strategy(
                        language, understanding.sentiment, answer
                    ),
                    TurnKind.MESSAGE,
                    GroundingStatus.GROUNDED,
                    CyberSaathiService._conversation_sources(retrieval.matches[:1]),
                    retrieval.retrieval_latency_ms,
                )
            state.incident.status = IncidentStatus.AWAITING_USER_INPUT
            return RoutedReply(
                CyberSaathiService._with_sentiment_strategy(
                    language,
                    understanding.sentiment,
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
        domain = CyberSaathiService._knowledge_domain(message, understanding)
        try:
            return KnowledgeService.search(
                KnowledgeSearchRequest(
                    query=message,
                    domain=domain,
                    language=understanding.response_language,
                    top_k=2,
                )
            )
        except APIError:
            # Knowledge is an optional grounding layer. A missing, stale, or rejected
            # index must never suppress deterministic urgent-safety instructions.
            return KnowledgeSearchResponse(
                query=message,
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
        amount = next(
            (
                entity.normalized_value or entity.value
                for entity in state.incident.entities
                if entity.type == EntityType.AMOUNT
            ),
            None,
        )
        return WorkflowHandoff(
            target=HandoffTarget.REPORT_CRIME,
            reporting_mode=state.reporting_mode,
            route="/report-crime",
            prefill=ComplaintPrefill(
                description=state.incident.summary,
                crime_domain=state.incident.crime_domain,
                financial_loss_amount=amount,
            ),
        )

    @staticmethod
    def _is_confirmation(message: str) -> bool:
        return message.strip().casefold() in YES_MARKERS

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
