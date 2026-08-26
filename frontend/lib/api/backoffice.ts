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
  updateWarriorApplicationStatus: (id: string, payload: ApiRecord, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/admin/warrior-applications/" + id + "/status", payload, options)
};
