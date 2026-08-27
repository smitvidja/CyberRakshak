import {apiClient, type ApiRequestOptions} from "@/lib/api/client";
import type {ApiRecord} from "@/lib/api/auth";

export type ResumeParsingStatus = "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";

export type ResumeParsingResult = {
  confirmed_at: string | null;
  created_at: string;
  error_message: string | null;
  extracted_data: {
    certifications?: Array<Record<string, unknown>>;
    education?: Array<Record<string, unknown>>;
    experience?: Array<Record<string, unknown>>;
    file_name?: string;
    profile?: Record<string, unknown>;
    review_required?: boolean;
    skills?: string[];
    source?: string;
  } | null;
  id: string;
  processed_at: string | null;
  resume_file_name: string;
  status: ResumeParsingStatus;
};

export type SkillCatalogItem = {
  category: string | null;
  description: string | null;
  id: string;
  name: string;
};

export type WarriorApplication = {
  application_number: string;
  created_at: string;
  id: string;
  review_note: string | null;
  reviewed_at: string | null;
  statement: string | null;
  status: "DRAFT" | "SUBMITTED" | "UNDER_REVIEW" | "APPROVED" | "REJECTED";
  submitted_at: string | null;
  updated_at: string;
};

export const cyberWarriorsApi = {
  createProfile: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/cyber-warriors/profile", payload, options),
  getMine: (options: ApiRequestOptions) => apiClient.get<ApiRecord>("/cyber-warriors/me", options),
  listSkills: (options: ApiRequestOptions) => apiClient.get<SkillCatalogItem[]>("/cyber-warriors/skills", options),
  updateMine: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/cyber-warriors/me", payload, options)
};

export const resumeApi = {
  confirmParsing: (resultId: string, payload: ApiRecord, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/resume/parsing-results/" + resultId + "/confirm", payload, options),
  getParsingResult: (resultId: string, options: ApiRequestOptions) => apiClient.get<ResumeParsingResult>("/resume/parsing-results/" + resultId, options),
  upload: (payload: FormData, options: ApiRequestOptions) => apiClient.upload<ResumeParsingResult>("/resume/upload", payload, options)
};

export const warriorApplicationsApi = {
  create: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.post<WarriorApplication>("/warrior-applications", payload, options),
  listMine: (options: ApiRequestOptions) => apiClient.get<WarriorApplication[]>("/warrior-applications/my", options),
  submit: (id: string, options: ApiRequestOptions) => apiClient.post<WarriorApplication>("/warrior-applications/" + id + "/submit", undefined, options)
};

export const warriorReportsApi = {
  create: (payload: ApiRecord, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/warrior-reports", payload, options),
  getById: (id: string, options: ApiRequestOptions) => apiClient.get<ApiRecord>("/warrior-reports/" + id, options),
  listMine: (options: ApiRequestOptions) => apiClient.get<ApiRecord[]>("/warrior-reports/my", options),
  submit: (id: string, options: ApiRequestOptions) => apiClient.post<ApiRecord>("/warrior-reports/" + id + "/submit", undefined, options),
  update: (id: string, payload: ApiRecord, options: ApiRequestOptions) => apiClient.patch<ApiRecord>("/warrior-reports/" + id, payload, options)
};
