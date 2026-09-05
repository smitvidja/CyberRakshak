import {apiClient} from "@/lib/api/client";
import type {ConversationResponse, ConversationState, ReportingMode, SaathiLanguage} from "@/types/cyber-saathi";

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
    })
};
