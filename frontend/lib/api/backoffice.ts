import {apiClient, type ApiRequestOptions} from "@/lib/api/client";
import type {ApiRecord} from "@/lib/api/auth";

export const notificationsApi = {
  list: (options: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/notifications", options),
  markRead: (id: string, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/notifications/" + id + "/read", {}, options)
};

export const adminApi = {
  listAuditLogs: (options: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/admin/audit-logs", options),
  listComplaints: (options: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/admin/complaints", options),
  listSuspectReports: (options: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/admin/suspect-reports", options),
  listWarriorApplications: (options: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/admin/warrior-applications", options),
  updateComplaintStatus: (id: string, payload: ApiRecord, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/admin/complaints/" + id + "/status", payload, options),
  updateSuspectReportStatus: (id: string, payload: ApiRecord, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/admin/suspect-reports/" + id + "/status", payload, options),
  updateWarriorApplicationStatus: (id: string, payload: ApiRecord, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/admin/warrior-applications/" + id + "/status", payload, options),
  // Questions Cyber Saathi could not answer, most-asked first. The endpoints have
  // existed since the gap loop was built; until now nothing could read them.
  listKnowledgeGaps: (query: KnowledgeGapQuery, options: ApiRequestOptions) => {
    const params = new URLSearchParams();
    if (query.status) params.set("status", query.status);
    if (query.crimeDomain) params.set("crime_domain", query.crimeDomain);
    if (query.minOccurrences) params.set("min_occurrences", String(query.minOccurrences));
    const suffix = params.toString();
    return apiClient.get<KnowledgeGap[]>("/admin/knowledge-gaps" + (suffix ? "?" + suffix : ""), options);
  },
  updateKnowledgeGapStatus: (id: string, payload: KnowledgeGapStatusUpdate, options: ApiRequestOptions) =>
    apiClient.patch<KnowledgeGap>("/admin/knowledge-gaps/" + id + "/status", payload, options)
};

export type KnowledgeGapStatus = "OPEN" | "REVIEWED" | "ACTIONED" | "DISMISSED";

export type KnowledgeGap = {
  crime_domain: string;
  first_seen_at: string;
  id: string;
  knowledge_domain: string | null;
  language: string;
  last_seen_at: string;
  occurrences: number;
  resolution_note: string | null;
  reviewed_at: string | null;
  sample_question: string;
  status: KnowledgeGapStatus;
};

export type KnowledgeGapQuery = {
  crimeDomain?: string;
  minOccurrences?: number;
  status?: string;
};

export type KnowledgeGapStatusUpdate = {
  resolution_note?: string | null;
  status: KnowledgeGapStatus;
};
