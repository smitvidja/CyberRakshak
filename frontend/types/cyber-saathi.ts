export type SaathiLanguage = "EN" | "HI" | "HINGLISH" | "MIXED";
export type ReportingMode = "undecided" | "anonymous" | "identified";
export type IncidentStatus =
  | "unknown" | "suspected" | "identified" | "urgent"
  | "awaiting_confirmation" | "awaiting_user_input" | "guidance_given"
  | "ready_to_report" | "report_started" | "report_completed"
  | "tracking_requested" | "resolved";

export type SaathiEntity = {
  id: string;
  type: "amount" | "phone_number" | "upi_id" | "transaction_id" | "provider" | "date_time" | "url" | "email" | "account_id" | "username" | "date" | "time" | "social_platform" | "location" | "account_service";
  value: string;
  normalized_value: string | null;
  confidence: number;
  requires_confirmation: boolean;
  confirmed: boolean;
};

export type SaathiTurn = {
  id: string;
  role: "assistant" | "user";
  content: string;
  language: SaathiLanguage;
  kind: "message" | "safety" | "confirmation" | "handoff" | "error";
  created_at: string;
};

export type SaathiIncident = {
  status: IncidentStatus;
  intent: string;
  crime_domain: string;
  urgency: "low" | "medium" | "high" | "critical";
  sentiment: string;
  language: SaathiLanguage;
  confidence: number;
  entities: SaathiEntity[];
  summary: string | null;
  occurred_recently: boolean | null;
  needs_clarification: boolean;
  response_language: SaathiLanguage;
};

export type ConfidenceBand = "low" | "medium" | "high";

export type UnderstandingResult = {
  language: SaathiLanguage;
  response_language: SaathiLanguage;
  intent: string;
  crime_domain: string;
  entities: SaathiEntity[];
  urgency: "low" | "medium" | "high" | "critical";
  sentiment: string;
  confidence: number;
  confidence_band: ConfidenceBand;
  needs_clarification: boolean;
  clarification_prompt: string | null;
};

export type SaathiHandoff = {
  target: "report_crime" | "track_complaint" | "cyber_warrior";
  reporting_mode: ReportingMode;
  route: string;
  prefill: {
    description: string | null;
    crime_domain: string;
    financial_loss_amount: string | null;
    incident_at: string | null;
    suspect_identifiers: string[];
  };
};

export type ConversationState = {
  id: string;
  status: "active" | "handed_off" | "completed";
  language: SaathiLanguage;
  reporting_mode: ReportingMode;
  turns: SaathiTurn[];
  incident: SaathiIncident;
  pending_confirmation_entity_ids: string[];
  handoff: SaathiHandoff | null;
  created_at: string;
  updated_at: string;
};

export type ConversationResponse = {
  state: ConversationState;
  latency_budget: {
    language_detection_ms: number;
    deterministic_safety_ms: number;
    orchestration_ms: number;
    provider_first_token_ms: number;
    response_overhead_ms: number;
    first_useful_response_ms: number;
  };
  mock_provider: boolean;
};
