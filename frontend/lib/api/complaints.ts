import {apiClient, type ApiRequestOptions} from "@/lib/api/client";
import type {ApiRecord} from "@/lib/api/auth";

export const complaintCategoriesApi = {
  list: () => apiClient.get<ApiRecord[]>("/complaint-categories")
};

export const complaintsApi = {
  createDraft: (payload: ApiRecord, options?: ApiRequestOptions) => apiClient.post<ApiRecord>("/complaints/drafts", payload, options),
  downloadCopy: (id: string, options?: ApiRequestOptions) => apiClient.download("/complaints/" + id + "/copy", options),
  getById: (id: string, options?: ApiRequestOptions) => apiClient.get<ApiRecord>("/complaints/" + id, options),
  listMine: (options?: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/complaints/my", options),
  statusHistory: (id: string, options?: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/complaints/" + id + "/status-history", options),
  submit: (id: string, options?: ApiRequestOptions) => apiClient.post<ApiRecord>("/complaints/" + id + "/submit", undefined, options),
  track: (complaintNumber: string) => apiClient.get<ApiRecord>("/complaints/track/" + encodeURIComponent(complaintNumber)),
  updateDraft: (id: string, payload: ApiRecord, options?: ApiRequestOptions) => apiClient.patch<ApiRecord>("/complaints/" + id, payload, options)
};

export const evidenceApi = {
  getById: (id: string, options?: ApiRequestOptions) => apiClient.get<ApiRecord>("/evidence/" + id, options),
  listByComplaint: (complaintId: string, options?: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/evidence/by-complaint/" + complaintId, options),
  listByWarriorReport: (reportId: string, options?: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/evidence/by-warrior-report/" + reportId, options),
  remove: (id: string, options?: ApiRequestOptions) => apiClient.delete<ApiRecord>("/evidence/" + id, options),
  upload: (payload: FormData, options?: ApiRequestOptions) => apiClient.upload<ApiRecord>("/evidence", payload, options)
};

export const suspectsApi = {
  createCorrection: (payload: ApiRecord, options?: ApiRequestOptions) => apiClient.post<ApiRecord>("/suspects/corrections", payload, options),
  createReport: (payload: ApiRecord, options?: ApiRequestOptions) => apiClient.post<ApiRecord>("/suspects/reports", payload, options),
  getById: (id: string, options?: ApiRequestOptions) => apiClient.get<ApiRecord>("/suspects/reports/" + id, options),
  listMine: (options?: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/suspects/reports/my", options),
  search: (payload: ApiRecord, options?: ApiRequestOptions) => apiClient.post<ApiRecord>("/suspects/search", payload, options)
};
