from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, model_validator


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
    UNKNOWN = "unknown"


class CrimeDomain(str, Enum):
    FINANCIAL_FRAUD = "financial_fraud"
    IDENTITY_THEFT = "identity_theft"
    ONLINE_HARASSMENT = "online_harassment"
    PHISHING_SCAM = "phishing_scam"
    MALWARE = "malware"
    MISINFORMATION = "misinformation"
    CHILD_SAFETY = "child_safety"
    CYBER_TERRORISM = "cyber_terrorism"
    OTHER = "other"
    UNKNOWN = "unknown"


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


class TurnKind(str, Enum):
    MESSAGE = "message"
    SAFETY = "safety"
    CONFIRMATION = "confirmation"
    HANDOFF = "handoff"
    ERROR = "error"


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


class ConversationTurn(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    role: Literal["assistant", "user"]
    content: str = Field(min_length=1, max_length=8000)
    language: LanguageCode
    kind: TurnKind = TurnKind.MESSAGE
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ComplaintPrefill(BaseModel):
    description: str | None = Field(default=None, max_length=8000)
    crime_domain: CrimeDomain = CrimeDomain.UNKNOWN
    financial_loss_amount: str | None = Field(default=None, max_length=100)
    incident_at: str | None = Field(default=None, max_length=100)
    suspect_identifiers: list[str] = Field(default_factory=list, max_length=20)


class WorkflowHandoff(BaseModel):
    target: HandoffTarget
    reporting_mode: ReportingMode
    route: str = Field(pattern=r"^/", max_length=300)
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
    reporting_mode: ReportingMode = ReportingMode.UNDECIDED
    turns: list[ConversationTurn] = Field(default_factory=list, max_length=50)
    incident: IncidentState = Field(default_factory=IncidentState)
    pending_confirmation_entity_ids: list[UUID] = Field(default_factory=list, max_length=30)
    handoff: WorkflowHandoff | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ConversationCreate(BaseModel):
    language: LanguageCode = LanguageCode.EN
    reporting_mode: ReportingMode = ReportingMode.UNDECIDED


class ConversationMessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    state: ConversationState
    reporting_mode: ReportingMode | None = None


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


class ConversationResponse(BaseModel):
    state: ConversationState
    latency_budget: LatencyBudget = Field(default_factory=LatencyBudget)
    mock_provider: bool = True
