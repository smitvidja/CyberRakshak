import {apiClient} from "@/lib/api/client";
import type {ConversationResponse, ConversationState, ReportingMode, SaathiLanguage, UnderstandingResult} from "@/types/cyber-saathi";

export const cyberSaathiApi = {
  start: (language: SaathiLanguage, reportingMode: ReportingMode = "undecided") =>
    apiClient.post<ConversationResponse>("/cyber-saathi/conversations", {
      language,
      reporting_mode: reportingMode
    }),
  send: (state: ConversationState, message: string, reportingMode?: ReportingMode) =>
    apiClient.post<ConversationResponse>(`/cyber-saathi/conversations/${state.id}/messages`, {
      message,
      state,
      reporting_mode: reportingMode
    }),
  analyzeAttachment: (state: ConversationState, file: File) => {
    const payload = new FormData();
    payload.set("state_json", JSON.stringify(state));
    payload.set("file", file);
    return apiClient.upload<ConversationResponse>(`/cyber-saathi/conversations/${state.id}/attachments`, payload);
  },
  understand: (message: string, preferredLanguage?: SaathiLanguage) =>
    apiClient.post<UnderstandingResult>("/cyber-saathi/understand", {
      message,
      preferred_language: preferredLanguage
    })
};
