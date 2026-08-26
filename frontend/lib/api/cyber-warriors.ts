import {apiClient, type ApiRequestOptions} from "@/lib/api/client";
import type {ApiRecord} from "@/lib/api/auth";

export const cyberWarriorsApi = {
  createProfile: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/cyber-warriors/profile", payload, options),
  getMine: (options: ApiRequestOptions) => apiClient.get<ApiRecord>("/cyber-warriors/me", options),
  updateMine: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/cyber-warriors/me", payload, options)
};

export const resumeApi = {
  confirmParsing: (resultId: string, payload: ApiRecord, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/resume/parsing-results/" + resultId + "/confirm", payload, options),
  getParsingResult: (resultId: string, options: ApiRequestOptions) => apiClient.get<ApiRecord>("/resume/parsing-results/" + resultId, options),
  upload: (payload: FormData, options: ApiRequestOptions) => apiClient.upload<ApiRecord>("/resume/upload", payload, options)
};

export const warriorApplicationsApi = {
  create: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/warrior-applications", payload, options),
  listMine: (options: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/warrior-applications/my", options),
  submit: (id: string, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/warrior-applications/" + id + "/submit", undefined, options)
};

export const warriorReportsApi = {
  create: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/warrior-reports", payload, options),
  getById: (id: string, options: ApiRequestOptions) => apiClient.get<ApiRecord>("/warrior-reports/" + id, options),
  listMine: (options: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/warrior-reports/my", options),
  submit: (id: string, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/warrior-reports/" + id + "/submit", undefined, options),
  update: (id: string, payload: ApiRecord, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/warrior-reports/" + id, payload, options)
};
