from datetime import datetime, timezone
from uuid import UUID

from app.core.errors import APIError
from app.schemas.cyber_saathi import (
    ComplaintPrefill,
    ConversationCreate,
    ConversationMessageRequest,
    ConversationResponse,
    ConversationState,
    ConversationStatus,
    ConversationTurn,
    CrimeDomain,
    Entity,
    EntityType,
    HandoffTarget,
    IncidentState,
    IncidentStatus,
    Intent,
    LanguageCode,
    ReportingMode,
    TurnKind,
    Urgency,
    UnderstandingResult,
    WorkflowHandoff,
)
from app.services.cyber_saathi_understanding import UnderstandingEngine


YES_MARKERS = {"yes", "correct", "confirm", "haan", "ha", "हाँ", "सही"}


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
            answer = CyberSaathiService._copy(language, "confirmed")
            kind = TurnKind.HANDOFF
        else:
            answer, kind = CyberSaathiService._route_mock_message(
                state, payload.message, understanding
            )

        state.turns.append(
            ConversationTurn(role="assistant", content=answer, language=language, kind=kind)
        )
        state.updated_at = datetime.now(timezone.utc)
        return ConversationResponse(state=state)

    @staticmethod
    def _route_mock_message(
        state: ConversationState, message: str, understanding: UnderstandingResult
    ) -> tuple[str, TurnKind]:
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
            return CyberSaathiService._copy(language, "track"), TurnKind.HANDOFF

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
            safety = CyberSaathiService._copy(language, "financial_safety")
            if pending_entities:
                safety += " " + CyberSaathiService._confirmation_copy(
                    language, pending_entities
                )
            return safety, TurnKind.SAFETY

        if intent == Intent.REPORT_INCIDENT and not understanding.needs_clarification:
            state.incident.status = (
                IncidentStatus.AWAITING_CONFIRMATION
                if pending_entities
                else IncidentStatus.READY_TO_REPORT
            )
            state.handoff = CyberSaathiService._report_handoff(state)
            if pending_entities:
                return CyberSaathiService._confirmation_copy(language, pending_entities), TurnKind.CONFIRMATION
            return CyberSaathiService._copy(language, "report"), TurnKind.HANDOFF

        if understanding.confidence_band.value == "high" and crime_domain != CrimeDomain.UNKNOWN:
            state.incident.status = IncidentStatus.GUIDANCE_GIVEN
            return CyberSaathiService._copy(language, "guidance"), TurnKind.MESSAGE

        state.incident.status = IncidentStatus.AWAITING_USER_INPUT
        return CyberSaathiService._copy(language, "clarify"), TurnKind.MESSAGE

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
        }
        localized = copy[key]
        return localized.get(language, localized[LanguageCode.EN])
