import {apiClient, buildApiUrl} from "@/lib/api/client";
import type {ConversationResponse, ConversationState, ReportingMode, SaathiLanguage, UnderstandingResult, VoiceCapabilities, VoiceTranscription} from "@/types/cyber-saathi";

function voiceSocketUrl(conversationId: string, language: SaathiLanguage) {
  const url = new URL(buildApiUrl(`/cyber-saathi/conversations/${conversationId}/voice/transcriptions/stream`));
  url.protocol = url.protocol === "https:" ? "wss:" : "ws:";
  url.searchParams.set("language", language);
  return url.toString();
}

export const cyberSaathiApi = {
  start: (language: SaathiLanguage, reportingMode: ReportingMode = "undecided", storageConsent = false) =>
    apiClient.post<ConversationResponse>("/cyber-saathi/conversations", {
      language,
      reporting_mode: reportingMode,
      storage_consent: storageConsent
    }),
  resume: (conversationId: string) => apiClient.get<ConversationResponse>(`/cyber-saathi/conversations/${conversationId}`),
  send: (state: ConversationState, message: string, reportingMode?: ReportingMode, prepareReportDraft = false) =>
    apiClient.post<ConversationResponse>(`/cyber-saathi/conversations/${state.id}/messages`, {
      message,
      state,
      reporting_mode: reportingMode,
      prepare_report_draft: prepareReportDraft
    }),
  analyzeAttachment: (state: ConversationState, file: File) => {
    const payload = new FormData();
    payload.set("state_json", JSON.stringify(state));
    payload.set("file", file);
    return apiClient.upload<ConversationResponse>(`/cyber-saathi/conversations/${state.id}/attachments`, payload);
  },
  feedback: (conversationId: string, rating: number, comment?: string) =>
    apiClient.post<void>(`/cyber-saathi/conversations/${conversationId}/feedback`, {rating, comment}),
  understand: (message: string, preferredLanguage?: SaathiLanguage) =>
    apiClient.post<UnderstandingResult>("/cyber-saathi/understand", {
      message,
      preferred_language: preferredLanguage
    }),
  voiceCapabilities: () => apiClient.get<VoiceCapabilities>("/cyber-saathi/voice/capabilities"),
  voiceSocketUrl,
  transcribeRecording: (recording: Blob, language: SaathiLanguage) => {
    const payload = new FormData();
    payload.set("language", language);
    payload.set("file", recording, "cyber-saathi-recording.webm");
    return apiClient.upload<VoiceTranscription>("/cyber-saathi/voice/transcriptions", payload);
  },
  synthesizeSpeech: (text: string, language: SaathiLanguage, signal?: AbortSignal) =>
    fetch(buildApiUrl("/cyber-saathi/voice/speech"), {
      body: JSON.stringify({text: text.slice(0, 3500), language}),
      credentials: "include",
      headers: {"Content-Type": "application/json"},
      method: "POST",
      signal
    })
};
