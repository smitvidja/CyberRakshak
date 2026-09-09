import {apiClient} from "@/lib/api/client";
import type {ConversationResponse, ConversationState, ReportingMode, SaathiLanguage, UnderstandingResult} from "@/types/cyber-saathi";

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
    })
};
