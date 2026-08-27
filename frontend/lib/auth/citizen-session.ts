import type {ApiRecord, MockIdentityProfile} from "@/lib/api/auth";

const reportModeKey = "cyberrakshak.report-mode";
const reportCategoryHintKey = "cyberrakshak.report-category-hint";
const accessTokenKey = "cyberrakshak.access-token";
const mockIdentityProfileKey = "cyberrakshak.mock-identity-profile";
const complaintDraftKey = "cyberrakshak.complaint-draft";
const complaintEvidenceKey = "cyberrakshak.complaint-evidence";

export type CitizenComplaintDraft = {data: ApiRecord; id: string};
export type CitizenEvidence = {fileName: string; fileSize: number; id: string};

// localStorage, not sessionStorage: sessionStorage clears itself the instant the tab/browser
// closes, which was silently logging citizens out even though nothing ever called logout.
// localStorage persists until something explicitly clears these keys.
export function setReportMode(mode: "anonymous" | "identified") { localStorage.setItem(reportModeKey, mode); }
export function getReportMode() { const value = localStorage.getItem(reportModeKey); return value === "anonymous" || value === "identified" ? value : null; }
export function setReportCategoryHint(category: string) { localStorage.setItem(reportCategoryHintKey, category); }
export function getReportCategoryHint() { return localStorage.getItem(reportCategoryHintKey); }
export function clearReportCategoryHint() { localStorage.removeItem(reportCategoryHintKey); }
export function setAccessToken(accessToken: string) { localStorage.setItem(accessTokenKey, accessToken); }
export function getAccessToken() { return localStorage.getItem(accessTokenKey); }
export function setMockIdentityProfile(profile: MockIdentityProfile) { localStorage.setItem(mockIdentityProfileKey, JSON.stringify(profile)); }
export function getMockIdentityProfile() { const value = localStorage.getItem(mockIdentityProfileKey); if (!value) return null; try { const profile = JSON.parse(value) as MockIdentityProfile; return typeof profile.full_name === "string" && typeof profile.registered_mobile === "string" ? profile : null; } catch { return null; } }
export function setComplaintDraft(draft: CitizenComplaintDraft) { localStorage.setItem(complaintDraftKey, JSON.stringify(draft)); }
export function getComplaintDraft() { const value = localStorage.getItem(complaintDraftKey); if (!value) return null; try { const draft = JSON.parse(value) as CitizenComplaintDraft; return typeof draft.id === "string" && draft.data && typeof draft.data === "object" ? draft : null; } catch { return null; } }
function readEvidence() { const value = localStorage.getItem(complaintEvidenceKey); if (!value) return {} as Record<string, CitizenEvidence[]>; try { const parsed = JSON.parse(value) as Record<string, CitizenEvidence[]>; return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {}; } catch { return {}; } }
export function addComplaintEvidence(draftId: string, evidence: CitizenEvidence) { const evidenceByDraft = readEvidence(); evidenceByDraft[draftId] = [...(evidenceByDraft[draftId] ?? []), evidence]; localStorage.setItem(complaintEvidenceKey, JSON.stringify(evidenceByDraft)); }
export function getComplaintEvidence(draftId: string) { return readEvidence()[draftId] ?? []; }
export function clearCitizenSession() {
  localStorage.removeItem(accessTokenKey);
  localStorage.removeItem(mockIdentityProfileKey);
}
