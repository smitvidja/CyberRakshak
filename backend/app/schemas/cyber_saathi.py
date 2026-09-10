from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LanguageCode(str, Enum):
    EN = "EN"
    HI = "HI"
    HINGLISH = "HINGLISH"
    MIXED = "MIXED"


class ConversationStatus(str, Enum):
    ACTIVE = "active"
    HANDED_OFF = "handed_off"
    COMPLETED = "completed"


class IncidentStatus(str, Enum):
    UNKNOWN = "unknown"
    SUSPECTED = "suspected"
    IDENTIFIED = "identified"
    URGENT = "urgent"
    AWAITING_CONFIRMATION = "awaiting_confirmation"
    AWAITING_USER_INPUT = "awaiting_user_input"
    GUIDANCE_GIVEN = "guidance_given"
    READY_TO_REPORT = "ready_to_report"
    REPORT_STARTED = "report_started"
    REPORT_COMPLETED = "report_completed"
    TRACKING_REQUESTED = "tracking_requested"
    RESOLVED = "resolved"


class Intent(str, Enum):
    REPORT_INCIDENT = "report_incident"
    SEEK_GUIDANCE = "seek_guidance"
    CHECK_IDENTIFIER = "check_identifier"
    TRACK_REPORT = "track_report"
    CYBER_WARRIOR = "cyber_warrior"
    GENERAL_AWARENESS = "general_awareness"
    EXPLORE_CYBER_RISK = "explore_cyber_risk"
    UNKNOWN = "unknown"


class CrimeDomain(str, Enum):
    FINANCIAL_FRAUD = "financial_fraud"
    ECOMMERCE_FRAUD = "ecommerce_fraud"
    ACCOUNT_COMPROMISE = "account_compromise"
    IMPERSONATION = "impersonation"
    IDENTITY_THEFT = "identity_theft"
    ONLINE_HARASSMENT = "online_harassment"
    WOMEN_CHILD_ONLINE_SAFETY = "women_child_online_safety"
    CYBERSTALKING = "cyberstalking"
    PHISHING_SCAM = "phishing_scam"
    MALWARE = "malware"
    MISINFORMATION = "misinformation"
    CHILD_SAFETY = "child_safety"
    CYBER_TERRORISM = "cyber_terrorism"
    OTHER = "other"
    UNKNOWN = "unknown"


class KnowledgeDomain(str, Enum):
    FINANCIAL_FRAUD = "financial_fraud"
    UPI_PAYMENT_FRAUD = "upi_payment_fraud"
    PHISHING = "phishing"
    ACCOUNT_COMPROMISE = "account_compromise"
    IMPERSONATION = "impersonation"
    HARASSMENT_ABUSE = "harassment_abuse"
    WOMEN_CHILD_ONLINE_SAFETY = "women_child_online_safety"
    CYBERSTALKING = "cyberstalking"
    MALWARE_DEVICE_COMPROMISE = "malware_device_compromise"
    IDENTITY_THEFT = "identity_theft"
    SUSPICIOUS_IDENTIFIERS = "suspicious_identifiers"
    GENERAL_CYBER_SAFETY = "general_cyber_safety"
    ECOMMERCE_CONSUMER_GRIEVANCE = "ecommerce_consumer_grievance"


class IncidentQueueStatus(str, Enum):
    ACTIVE = "active"
    QUEUED = "queued"
    COMPLETED = "completed"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Sentiment(str, Enum):
    NEUTRAL = "neutral"
    CONCERNED = "concerned"
    DISTRESSED = "distressed"
    FEARFUL = "fearful"
    ANGRY = "angry"
    CONFUSED = "confused"


class EntityType(str, Enum):
    AMOUNT = "amount"
    PHONE_NUMBER = "phone_number"
    UPI_ID = "upi_id"
    TRANSACTION_ID = "transaction_id"
    PROVIDER = "provider"
    DATE_TIME = "date_time"
    URL = "url"
    EMAIL = "email"
    ACCOUNT_ID = "account_id"
    USERNAME = "username"
    DATE = "date"
    TIME = "time"
    SOCIAL_PLATFORM = "social_platform"
    LOCATION = "location"
    ACCOUNT_SERVICE = "account_service"


class ConfidenceBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ReportingMode(str, Enum):
    UNDECIDED = "undecided"
    ANONYMOUS = "anonymous"
    IDENTIFIED = "identified"


class HandoffTarget(str, Enum):
    REPORT_CRIME = "report_crime"
    TRACK_COMPLAINT = "track_complaint"
    CYBER_WARRIOR = "cyber_warrior"
    LEARNING_RESOURCES = "learning_resources"
    SEARCH_SUSPECT_REPORTS = "search_suspect_reports"
    SECURE_INDIA = "secure_india"


class HandoffImplementationStatus(str, Enum):
    AVAILABLE = "available"
    PREVIEW = "preview"
    PLANNED = "planned"


class TurnKind(str, Enum):
    MESSAGE = "message"
    SAFETY = "safety"
    CONFIRMATION = "confirmation"
    HANDOFF = "handoff"
    ERROR = "error"


class TurnPurpose(str, Enum):
    NEW_INCIDENT = "new_incident"
    SAME_INCIDENT_DETAIL = "same_incident_detail"
    DUPLICATE_INCIDENT = "duplicate_incident"
    CORRECTION = "correction"
    CONFIRMATION = "confirmation"
    ACTION_COMPLETED = "action_completed"
    ACTION_BLOCKED = "action_blocked"
    NEXT_STEP = "next_step"
    SWITCH_INCIDENT = "switch_incident"
    REPORT_PREPARATION = "report_preparation"
    REPORTING_MODE = "reporting_mode"
    GENERAL_QUESTION = "general_question"


class ExpectedAnswerType(str, Enum):
    CONFIRM_ENTITIES = "confirm_entities"
    FINAL_LOSS_AMOUNT = "final_loss_amount"
    YES_NO = "yes_no"
    IDENTIFIER_OR_EVIDENCE = "identifier_or_evidence"
    FREE_TEXT = "free_text"


class PendingQuestion(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]+$", min_length=1, max_length=80)
    answer_type: ExpectedAnswerType
    incident_id: UUID
    attempts: int = Field(default=0, ge=0, le=20)
    last_answer: str | None = Field(default=None, max_length=500)


class ChecklistStatus(str, Enum):
    MISSING = "missing"
    COLLECTED = "collected"
    NOT_AVAILABLE = "not_available"
    OPTIONAL = "optional"


class GroundingStatus(str, Enum):
    NOT_USED = "not_used"
    GROUNDED = "grounded"
    NO_RESULT = "no_result"
    DETERMINISTIC_PLAYBOOK = "deterministic_playbook"


class LLMProvider(str, Enum):
    GEMINI = "gemini"
    GROK = "grok"
    NVIDIA = "nvidia"


class LLMWorkflowAction(str, Enum):
    NONE = "none"
    REPORT_CRIME = "report_crime"
    TRACK_COMPLAINT = "track_complaint"
    CHECK_SUSPECT = "check_suspect"
    CYBER_WARRIOR = "cyber_warrior"


LLMSuggestedAction = Annotated[str, Field(min_length=1, max_length=300)]
LLMSourceChunkId = Annotated[
    str, Field(pattern=r"^[a-z0-9_:-]+$", min_length=1, max_length=150)
]
LLMSafetyFlag = Annotated[
    str, Field(pattern=r"^[a-z0-9_:-]+$", min_length=1, max_length=80)
]


class LLMStructuredResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=2400)
    confidence: float = Field(ge=0, le=1)
    urgency: Urgency
    suggested_actions: list[LLMSuggestedAction] = Field(default_factory=list, max_length=5)
    clarification_needed: bool
    workflow_action: LLMWorkflowAction = LLMWorkflowAction.NONE
    sources: list[LLMSourceChunkId] = Field(default_factory=list, max_length=3)
    safety_flags: list[LLMSafetyFlag] = Field(default_factory=list, max_length=10)


class LLMProviderAttempt(BaseModel):
    provider: LLMProvider
    model: str = Field(min_length=1, max_length=150)
    status: Literal[
        "success",
        "not_configured",
        "timeout",
        "rate_limited",
        "provider_error",
        "malformed_output",
        "safety_rejected",
        "deadline_exceeded",
    ]
    latency_ms: float = Field(ge=0)


class LLMGenerationResult(BaseModel):
    response: LLMStructuredResponse | None = None
    provider: LLMProvider | None = None
    model: str | None = Field(default=None, max_length=150)
    fallback_used: bool = False
    deterministic_fallback: bool = False
    latency_ms: float = Field(ge=0)
    attempts: list[LLMProviderAttempt] = Field(default_factory=list, max_length=8)


class LLMProviderHealth(BaseModel):
    provider: LLMProvider
    model: str
    status: Literal["available", "not_configured", "unavailable"]
    latency_ms: float = Field(ge=0)


ConfidenceScore = Annotated[float, Field(ge=0, le=1)]


def confidence_band(score: float) -> ConfidenceBand:
    if score >= 0.8:
        return ConfidenceBand.HIGH
    if score >= 0.5:
        return ConfidenceBand.MEDIUM
    return ConfidenceBand.LOW


class Entity(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    type: EntityType
    value: str = Field(min_length=1, max_length=500)
    normalized_value: str | None = Field(default=None, max_length=500)
    confidence: ConfidenceScore
    requires_confirmation: bool = False
    confirmed: bool = False


class IncidentState(BaseModel):
    status: IncidentStatus = IncidentStatus.UNKNOWN
    intent: Intent = Intent.UNKNOWN
    crime_domain: CrimeDomain = CrimeDomain.UNKNOWN
    related_domains: list[CrimeDomain] = Field(default_factory=list, max_length=4)
    urgency: Urgency = Urgency.LOW
    sentiment: Sentiment = Sentiment.NEUTRAL
    language: LanguageCode = LanguageCode.EN
    confidence: ConfidenceScore = 0
    entities: list[Entity] = Field(default_factory=list, max_length=30)
    summary: str | None = Field(default=None, max_length=2000)
    occurred_recently: bool | None = None
    needs_clarification: bool = True
    response_language: LanguageCode = LanguageCode.EN

    @property
    def confidence_band(self) -> ConfidenceBand:
        return confidence_band(self.confidence)


class ReportChecklistItem(BaseModel):
    key: str = Field(pattern=r"^[a-z0-9_]+$", max_length=80)
    label: str = Field(min_length=1, max_length=240)
    status: ChecklistStatus = ChecklistStatus.MISSING
    required: bool = True
    value_preview: str | None = Field(default=None, max_length=300)


class AttachmentAnalysis(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    file_name: str = Field(min_length=1, max_length=255)
    mime_type: Literal["application/pdf", "image/png", "image/jpeg"]
    file_size: int = Field(ge=1, le=10 * 1024 * 1024)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    media_summary: str = Field(min_length=1, max_length=300)
    extraction_method: Literal["pdf_text", "tesseract_ocr", "metadata_only"] = "metadata_only"
    extraction_status: Literal["completed", "unavailable", "no_text"] = "no_text"
    relevance_status: Literal["relevant", "uncertain", "rejected"] = "uncertain"
    extracted_text_preview: str | None = Field(default=None, max_length=500)
    extracted_entities: list[Entity] = Field(default_factory=list, max_length=20)
    needs_user_review: bool = True


class ReportPreparation(BaseModel):
    reporting_for: Literal["SELF", "CHILD", "OTHER", "UNKNOWN"] = "UNKNOWN"
    affected_person_name: str | None = Field(default=None, max_length=255)
    checklist: list[ReportChecklistItem] = Field(default_factory=list, max_length=20)
    attachments: list[AttachmentAnalysis] = Field(default_factory=list, max_length=10)
    missing_required_keys: list[str] = Field(default_factory=list, max_length=20)
    ready_for_review: bool = False
    packet_ready: bool = False
    draft_prepared: bool = False
    suspect_details: str | None = Field(default=None, max_length=1000)


class ConversationIncident(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    sequence: int = Field(ge=1, le=10)
    queue_status: IncidentQueueStatus
    incident: IncidentState
    completed_actions: list[str] = Field(default_factory=list, max_length=20)
    blocked_actions: dict[str, int] = Field(default_factory=dict)
    message_fingerprints: list[str] = Field(default_factory=list, max_length=30)
    report_preparation: ReportPreparation = Field(default_factory=ReportPreparation)


class ConversationSource(BaseModel):
    chunk_id: str = Field(pattern=r"^[a-z0-9_:-]+$", max_length=150)
    source_id: str = Field(pattern=r"^[a-z0-9_]+$", max_length=100)
    source_title: str = Field(min_length=1, max_length=300)
    source_url: str = Field(min_length=1, max_length=1000)
    source_type: str = Field(min_length=1, max_length=100)
    jurisdiction: str = Field(min_length=1, max_length=100)
    version: str = Field(min_length=1, max_length=100)
    section_title: str = Field(min_length=1, max_length=300)


class ConversationTurn(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: Literal["assistant", "user"]
    content: str = Field(min_length=1, max_length=8000)
    language: LanguageCode
    kind: TurnKind = TurnKind.MESSAGE
    grounding_status: GroundingStatus = GroundingStatus.NOT_USED
    sources: list[ConversationSource] = Field(default_factory=list, max_length=3)
    retrieval_latency_ms: float | None = Field(default=None, ge=0)
    llm_provider: LLMProvider | None = None
    llm_model: str | None = Field(default=None, max_length=150)
    llm_fallback_used: bool = False
    llm_latency_ms: float | None = Field(default=None, ge=0)
    safety_flags: list[str] = Field(default_factory=list, max_length=10)
    purpose: TurnPurpose | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintPrefill(BaseModel):
    title: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=8000)
    crime_domain: CrimeDomain = CrimeDomain.UNKNOWN
    related_domains: list[CrimeDomain] = Field(default_factory=list, max_length=4)
    financial_loss_amount: str | None = Field(default=None, max_length=100)
    incident_at: str | None = Field(default=None, max_length=100)
    suspect_identifiers: list[str] = Field(default_factory=list, max_length=20)
    suspect_details: str | None = Field(default=None, max_length=1000)
    suspect_name: str | None = Field(default=None, max_length=255)
    suspect_alias: str | None = Field(default=None, max_length=255)
    city: str | None = Field(default=None, max_length=100)
    state: str | None = Field(default=None, max_length=100)
    reporting_for: Literal["SELF", "CHILD", "OTHER", "UNKNOWN"] = "UNKNOWN"
    affected_person_name: str | None = Field(default=None, max_length=255)
    attachment_ids: list[UUID] = Field(default_factory=list, max_length=10)


class SuspectIdentifierHandoff(BaseModel):
    identifier_type: Literal["PHONE", "EMAIL", "UPI", "BANK_ACCOUNT", "WEBSITE", "SOCIAL_MEDIA", "OTHER"]
    identifier_value: str = Field(min_length=2, max_length=500)


class WorkflowHandoff(BaseModel):
    target: HandoffTarget
    reporting_mode: ReportingMode
    route: str = Field(pattern=r"^/", max_length=300)
    implementation_status: HandoffImplementationStatus = HandoffImplementationStatus.AVAILABLE
    identifier: SuspectIdentifierHandoff | None = None
    prefill: ComplaintPrefill = Field(default_factory=ComplaintPrefill)

    @model_validator(mode="after")
    def anonymous_handoff_has_no_identity_payload(self) -> "WorkflowHandoff":
        # ComplaintPrefill intentionally has no reporter identity fields. Keep this
        # explicit guard so future schema expansion cannot silently cross the boundary.
        forbidden = {"full_name", "email", "mobile", "aadhaar", "user_id", "identity"}
        if self.reporting_mode == ReportingMode.ANONYMOUS:
            present = forbidden.intersection(self.prefill.model_dump().keys())
            if present:
                raise ValueError("Anonymous handoff cannot contain reporter identity")
        return self


class ConversationState(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    status: ConversationStatus = ConversationStatus.ACTIVE
    language: LanguageCode = LanguageCode.EN
    storage_consent: bool = False
    reporting_mode: ReportingMode = ReportingMode.UNDECIDED
    turns: list[ConversationTurn] = Field(default_factory=list, max_length=50)
    incident: IncidentState = Field(default_factory=IncidentState)
    incidents: list[ConversationIncident] = Field(default_factory=list, max_length=10)
    active_incident_id: UUID | None = None
    pending_question_incident_id: UUID | None = None
    pending_question: PendingQuestion | None = None
    pending_confirmation_entity_ids: list[UUID] = Field(default_factory=list, max_length=30)
    handoff: WorkflowHandoff | None = None
    last_turn_purpose: TurnPurpose | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationCreate(BaseModel):
    language: LanguageCode = LanguageCode.EN
    reporting_mode: ReportingMode = ReportingMode.UNDECIDED
    storage_consent: bool = False


class ConversationMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    state: ConversationState
    reporting_mode: ReportingMode | None = None
    prepare_report_draft: bool = False


class ConversationFeedback(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=1000)


class ConversationAttachmentRequest(BaseModel):
    state: ConversationState


class UnderstandingRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    preferred_language: LanguageCode | None = None


class UnderstandingResult(BaseModel):
    language: LanguageCode
    response_language: LanguageCode
    intent: Intent
    crime_domain: CrimeDomain
    entities: list[Entity] = Field(default_factory=list, max_length=30)
    urgency: Urgency
    sentiment: Sentiment
    confidence: ConfidenceScore
    confidence_band: ConfidenceBand
    needs_clarification: bool
    clarification_prompt: str | None = Field(default=None, max_length=500)


class LatencyBudget(BaseModel):
    language_detection_ms: int = Field(default=50, ge=0)
    deterministic_safety_ms: int = Field(default=100, ge=0)
    orchestration_ms: int = Field(default=250, ge=0)
    provider_first_token_ms: int = Field(default=2000, ge=0)
    response_overhead_ms: int = Field(default=500, ge=0)
    first_useful_response_ms: int = Field(default=2900, ge=0)


class KnowledgeSourceMetadata(BaseModel):
    source_id: str = Field(pattern=r"^[a-z0-9_]+$", max_length=100)
    source_title: str = Field(min_length=1, max_length=300)
    source_type: str = Field(min_length=1, max_length=100)
    source_url: str = Field(min_length=1, max_length=1000)
    jurisdiction: str = Field(min_length=1, max_length=100)
    domains: list[KnowledgeDomain] = Field(min_length=1, max_length=12)
    language: LanguageCode
    version: str = Field(min_length=1, max_length=100)
    published_at: str = Field(min_length=1, max_length=50)


class KnowledgeChunk(BaseModel):
    chunk_id: str = Field(pattern=r"^[a-z0-9_:-]+$", max_length=150)
    source: KnowledgeSourceMetadata
    domains: list[KnowledgeDomain] = Field(min_length=1, max_length=6)
    section_title: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=1200)
    retrieval_terms: list[str] = Field(default_factory=list, max_length=30)
    content_hash: str = Field(min_length=64, max_length=64)
    embedding: list[float] = Field(min_length=384, max_length=384)
    # Optional multilingual dense vector. It is created only during explicit
    # ingestion, so a normal API start or test run never downloads a local model.
    semantic_embedding: list[float] | None = Field(default=None, min_length=128, max_length=3072)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    domain: KnowledgeDomain | None = None
    language: LanguageCode | None = None
    top_k: int = Field(default=3, ge=1, le=5)
    minimum_relevance: float = Field(default=0.16, ge=0, le=1)


class KnowledgeMatch(BaseModel):
    chunk_id: str
    source_id: str
    source_title: str
    source_url: str
    source_type: str
    jurisdiction: str
    domains: list[KnowledgeDomain]
    language: LanguageCode
    version: str
    section_title: str
    text: str
    relevance_score: float = Field(ge=0, le=1)
    retrieval_strategy: str = Field(default="sparse_lexical", max_length=50)
    lexical_score: float | None = Field(default=None, ge=0, le=1)
    sparse_score: float | None = Field(default=None, ge=0, le=1)
    semantic_score: float | None = Field(default=None, ge=0, le=1)


class KnowledgeSearchResponse(BaseModel):
    query: str
    domain_filter: KnowledgeDomain | None = None
    retrieval_latency_ms: float = Field(ge=0)
    index_version: str
    no_result: bool
    matches: list[KnowledgeMatch] = Field(default_factory=list, max_length=5)
    bounded_context: str = Field(default="", max_length=2400)
    retrieval_strategy: str = Field(default="sparse_lexical", max_length=50)


class ConversationResponse(BaseModel):
    state: ConversationState
    latency_budget: LatencyBudget = Field(default_factory=LatencyBudget)
    mock_provider: bool = True


class VoiceCapabilities(BaseModel):
    provider: Literal["sarvam"] = "sarvam"
    enabled: bool
    configured: bool
    realtime_stt: bool
    rest_stt_fallback: bool
    streaming_tts: bool
    stt_model: str
    realtime_stt_model: str
    tts_model: str
    max_recording_seconds: int


class VoiceTranscription(BaseModel):
    transcript: str = Field(min_length=1, max_length=4000)
    detected_language_code: str | None = Field(default=None, max_length=20)
    language_probability: float | None = Field(default=None, ge=0, le=1)
    provider: Literal["sarvam"] = "sarvam"
    model: str
    stt_latency_ms: float = Field(ge=0)


class VoiceSpeechRequest(BaseModel):
    text: str = Field(min_length=1, max_length=3500)
    language: LanguageCode
