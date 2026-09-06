export type SaathiLanguage = "EN" | "HI" | "HINGLISH" | "MIXED";
export type ReportingMode = "undecided" | "anonymous" | "identified";
export type TurnPurpose = "new_incident" | "same_incident_detail" | "duplicate_incident" | "correction" | "confirmation" | "action_completed" | "action_blocked" | "next_step" | "switch_incident" | "report_preparation" | "reporting_mode" | "general_question";
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
  grounding_status: "not_used" | "grounded" | "no_result" | "deterministic_playbook";
  sources: Array<{
    chunk_id: string;
    source_id: string;
    source_title: string;
    source_url: string;
    source_type: string;
    jurisdiction: string;
    version: string;
    section_title: string;
  }>;
  retrieval_latency_ms: number | null;
  llm_provider?: "gemini" | "grok" | "nvidia" | null;
  llm_model?: string | null;
  llm_fallback_used?: boolean;
  llm_latency_ms?: number | null;
  safety_flags?: string[];
  purpose?: TurnPurpose | null;
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

export type QueuedSaathiIncident = {
  id: string;
  sequence: number;
  queue_status: "active" | "queued" | "completed";
  incident: SaathiIncident;
  completed_actions: string[];
  blocked_actions: Record<string, number>;
  message_fingerprints: string[];
  report_preparation: ReportPreparation;
};

export type ReportChecklistItem = {
  key: string;
  label: string;
  status: "missing" | "collected" | "not_available" | "optional";
  required: boolean;
  value_preview: string | null;
};

export type AttachmentAnalysis = {
  id: string;
  file_name: string;
  mime_type: "application/pdf" | "image/png" | "image/jpeg";
  file_size: number;
  checksum: string;
  media_summary: string;
  extracted_text_preview: string | null;
  extracted_entities: SaathiEntity[];
  needs_user_review: boolean;
};

export type ReportPreparation = {
  reporting_for: "SELF" | "CHILD" | "OTHER" | "UNKNOWN";
  affected_person_name: string | null;
  checklist: ReportChecklistItem[];
  attachments: AttachmentAnalysis[];
  missing_required_keys: string[];
  ready_for_review: boolean;
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
    title: string | null;
    crime_domain: string;
    financial_loss_amount: string | null;
    incident_at: string | null;
    suspect_identifiers: string[];
    reporting_for: "SELF" | "CHILD" | "OTHER" | "UNKNOWN";
    affected_person_name: string | null;
    attachment_ids: string[];
  };
};

export type ConversationState = {
  id: string;
  status: "active" | "handed_off" | "completed";
  language: SaathiLanguage;
  reporting_mode: ReportingMode;
  turns: SaathiTurn[];
  incident: SaathiIncident;
  incidents: QueuedSaathiIncident[];
  active_incident_id: string | null;
  pending_confirmation_entity_ids: string[];
  handoff: SaathiHandoff | null;
  last_turn_purpose: TurnPurpose | null;
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
