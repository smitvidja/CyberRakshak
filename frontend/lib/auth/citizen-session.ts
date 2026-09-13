import type {ApiRecord, MockIdentityProfile} from "@/lib/api/auth";

const reportModeKey = "cyberrakshak.report-mode";
const reportCategoryHintKey = "cyberrakshak.report-category-hint";
const accessTokenKey = "cyberrakshak.access-token";
const mockIdentityProfileKey = "cyberrakshak.mock-identity-profile";
const complaintDraftKey = "cyberrakshak.complaint-draft";
const complaintEvidenceKey = "cyberrakshak.complaint-evidence";
// Owned by other modules, listed here because this file is what logout calls and
// logout has to be able to reach every trace of a citizen's case.
const cyberSaathiConversationKey = "cyberrakshak.cyber-saathi.conversation.v2";
const cyberSaathiHandoffKey = "cyberrakshak.cyber-saathi.report-handoff.v1";

/** Every localStorage key that holds something about a citizen or their case. */
const citizenScopedKeys = [
  accessTokenKey,
  mockIdentityProfileKey,
  complaintDraftKey,
  complaintEvidenceKey,
  reportModeKey,
  reportCategoryHintKey,
  cyberSaathiConversationKey,
  cyberSaathiHandoffKey,
];

export const CYBER_SAATHI_CONVERSATION_KEY = cyberSaathiConversationKey;

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
/**
 * Log out, and leave nothing about the case behind.
 *
 * This used to remove the access token and the identity profile only. Everything
 * else survived: the whole Cyber Saathi conversation, the draft complaint, the
 * names of the evidence files, the reporting mode. So a citizen could log out on
 * a shared computer - a cyber cafe, a library, a family PC - and the next person
 * would open the page and read their sextortion or fraud conversation in full.
 * On a service people come to at the worst moment of their year, that is the one
 * kind of leak that must not exist.
 *
 * Driven by a list rather than by whichever removeItem calls someone remembered:
 * anything citizen-scoped is added to citizenScopedKeys and is cleared here for
 * free, which is why the Cyber Saathi keys are named in this file even though
 * other modules own them.
 */
export function clearCitizenSession() {
  for (const key of citizenScopedKeys) localStorage.removeItem(key);
}

/**
 * The report is filed: forget the conversation that produced it.
 *
 * Submitting used to leave the whole Cyber Saathi thread in localStorage, so a
 * citizen who had finished - and even logged out - could reopen the page and find
 * their case still on screen. This clears the conversation and its handoff while
 * deliberately leaving the access token and the stored complaint alone: they are
 * still logged in, and the confirmation page reads that complaint to show them
 * their reference number.
 */
export function clearCyberSaathiCase() {
  localStorage.removeItem(cyberSaathiConversationKey);
  localStorage.removeItem(cyberSaathiHandoffKey);
}

/** The keys a logout is responsible for. Exported so a test can hold it to that. */
export function citizenScopedStorageKeys() {
  return [...citizenScopedKeys];
}
