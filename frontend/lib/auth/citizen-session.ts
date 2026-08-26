import type {ApiRecord} from "@/lib/api/auth";

const reportModeKey = "cyberrakshak.report-mode";
const accessTokenKey = "cyberrakshak.access-token";
const complaintDraftKey = "cyberrakshak.complaint-draft";

export type CitizenComplaintDraft = {
  data: ApiRecord;
  id: string;
};

export function setReportMode(mode: "anonymous" | "identified") {
  sessionStorage.setItem(reportModeKey, mode);
}

export function getReportMode() {
  const value = sessionStorage.getItem(reportModeKey);
  return value === "anonymous" || value === "identified" ? value : null;
}

export function setAccessToken(accessToken: string) {
  sessionStorage.setItem(accessTokenKey, accessToken);
}

export function getAccessToken() {
  return sessionStorage.getItem(accessTokenKey);
}

export function setComplaintDraft(draft: CitizenComplaintDraft) {
  sessionStorage.setItem(complaintDraftKey, JSON.stringify(draft));
}

export function getComplaintDraft() {
  const value = sessionStorage.getItem(complaintDraftKey);
  if (!value) {
    return null;
  }

  try {
    const draft = JSON.parse(value) as CitizenComplaintDraft;
    return typeof draft.id === "string" && draft.data && typeof draft.data === "object" ? draft : null;
  } catch {
    return null;
  }
}