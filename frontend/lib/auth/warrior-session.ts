import type {MockIdentityProfile} from "@/lib/api/auth";
import type {WarriorApplication} from "@/lib/api/cyber-warriors";

const warriorAccessTokenKey = "cyberrakshak.warrior-access-token";
const warriorIdentityKey = "cyberrakshak.warrior-identity";
const warriorProfileSetupKey = "cyberrakshak.warrior-profile-setup";
const warriorResumeKey = "cyberrakshak.warrior-resume";
const warriorApplicationKey = "cyberrakshak.warrior-application";
const warriorReportDraftKey = "cyberrakshak.warrior-report-draft";

export type WarriorIdentitySession = {
  accountEmail: string;
  demoIdentityId: string;
  profile: MockIdentityProfile;
};

export type WarriorProfileSetup = {
  city: string;
  preferredLanguage: string;
  profileId: string;
  state: string;
};

// Session data lives in localStorage, not sessionStorage: sessionStorage is wiped the moment
// the tab/browser closes, which was silently logging warriors out on every restart even though
// they never clicked Logout. localStorage persists until clearWarriorSession() runs (the
// explicit Logout button) or the user clears site data - that's the only thing that should end it.
export function setWarriorToken(accessToken: string) {
  localStorage.setItem(warriorAccessTokenKey, accessToken);
}

export function getWarriorToken() {
  return localStorage.getItem(warriorAccessTokenKey);
}

export function setWarriorIdentity(identity: WarriorIdentitySession) {
  localStorage.setItem(warriorIdentityKey, JSON.stringify(identity));
}

export function getWarriorIdentity(): WarriorIdentitySession | null {
  const value = localStorage.getItem(warriorIdentityKey);
  if (!value) return null;
  try {
    const identity = JSON.parse(value) as WarriorIdentitySession;
    return typeof identity.accountEmail === "string" &&
      typeof identity.demoIdentityId === "string" &&
      typeof identity.profile?.full_name === "string"
      ? identity
      : null;
  } catch {
    return null;
  }
}

export function setWarriorProfileSetup(profile: WarriorProfileSetup) {
  localStorage.setItem(warriorProfileSetupKey, JSON.stringify(profile));
}

export function getWarriorProfileSetup(): WarriorProfileSetup | null {
  const value = localStorage.getItem(warriorProfileSetupKey);
  if (!value) return null;
  try {
    const profile = JSON.parse(value) as WarriorProfileSetup;
    return typeof profile.city === "string" && typeof profile.state === "string"
      ? profile
      : null;
  } catch {
    return null;
  }
}
export type WarriorResumeSession = {
  fileName: string;
  resultId: string;
};

export function setWarriorResume(resume: WarriorResumeSession) {
  localStorage.setItem(warriorResumeKey, JSON.stringify(resume));
}

export function getWarriorResume(): WarriorResumeSession | null {
  const value = localStorage.getItem(warriorResumeKey);
  if (!value) return null;
  try {
    const resume = JSON.parse(value) as WarriorResumeSession;
    return typeof resume.fileName === "string" && typeof resume.resultId === "string" ? resume : null;
  } catch {
    return null;
  }
}

export function setWarriorApplication(application: WarriorApplication) {
  localStorage.setItem(warriorApplicationKey, JSON.stringify(application));
}

export function getWarriorApplication(): WarriorApplication | null {
  const value = localStorage.getItem(warriorApplicationKey);
  if (!value) return null;
  try {
    const application = JSON.parse(value) as WarriorApplication;
    return typeof application.id === "string" && typeof application.application_number === "string" ? application : null;
  } catch {
    return null;
  }
}

export type WarriorReportDraftSession = {
  accountRef: string;
  category: string;
  description: string;
  evidenceDetails: string;
  evidenceItems: Array<{fileName: string; fileSize: number; id: string}>;
  incidentDate: string;
  incidentTime: string;
  otherInfo: string;
  platform: string;
  reportId: string | null;
  step: number;
  websiteUrl: string;
};

export function setWarriorReportDraft(draft: WarriorReportDraftSession) {
  localStorage.setItem(warriorReportDraftKey, JSON.stringify(draft));
}

export function getWarriorReportDraft(): WarriorReportDraftSession | null {
  const value = localStorage.getItem(warriorReportDraftKey);
  if (!value) return null;
  try {
    const draft = JSON.parse(value) as WarriorReportDraftSession;
    return typeof draft.step === "number" ? draft : null;
  } catch {
    return null;
  }
}

export function clearWarriorReportDraft() {
  localStorage.removeItem(warriorReportDraftKey);
}

export function clearWarriorSession() {
  localStorage.removeItem(warriorAccessTokenKey);
  localStorage.removeItem(warriorIdentityKey);
  localStorage.removeItem(warriorProfileSetupKey);
  localStorage.removeItem(warriorResumeKey);
  localStorage.removeItem(warriorApplicationKey);
  localStorage.removeItem(warriorReportDraftKey);
}
