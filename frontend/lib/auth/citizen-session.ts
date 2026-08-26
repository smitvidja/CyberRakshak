import type {ApiRecord} from "@/lib/api/auth";

const reportModeKey = "cyberrakshak.report-mode";
const accessTokenKey = "cyberrakshak.access-token";
const complaintDraftKey = "cyberrakshak.complaint-draft";
const complaintEvidenceKey = "cyberrakshak.complaint-evidence";

export type CitizenComplaintDraft = {
  data: ApiRecord;
  id: string;
};

export type CitizenEvidence = {
  fileName: string;
  fileSize: number;
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

function readEvidence() {
  const value = sessionStorage.getItem(complaintEvidenceKey);
  if (!value) return {} as Record<string, CitizenEvidence[]>;

  try {
    const parsed = JSON.parse(value) as Record<string, CitizenEvidence[]>;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {} as Record<string, CitizenEvidence[]>;
  }
}

export function addComplaintEvidence(draftId: string, evidence: CitizenEvidence) {
  const evidenceByDraft = readEvidence();
  evidenceByDraft[draftId] = [...(evidenceByDraft[draftId] ?? []), evidence];
  sessionStorage.setItem(complaintEvidenceKey, JSON.stringify(evidenceByDraft));
}

export function getComplaintEvidence(draftId: string) {
  return readEvidence()[draftId] ?? [];
}
