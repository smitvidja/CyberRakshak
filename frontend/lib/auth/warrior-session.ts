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

export function setWarriorToken(accessToken: string) {
  sessionStorage.setItem(warriorAccessTokenKey, accessToken);
}

export function getWarriorToken() {
  return sessionStorage.getItem(warriorAccessTokenKey);
}

export function setWarriorIdentity(identity: WarriorIdentitySession) {
  sessionStorage.setItem(warriorIdentityKey, JSON.stringify(identity));
}

export function getWarriorIdentity(): WarriorIdentitySession | null {
  const value = sessionStorage.getItem(warriorIdentityKey);
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
  sessionStorage.setItem(warriorProfileSetupKey, JSON.stringify(profile));
}

export function getWarriorProfileSetup(): WarriorProfileSetup | null {
  const value = sessionStorage.getItem(warriorProfileSetupKey);
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
  sessionStorage.setItem(warriorResumeKey, JSON.stringify(resume));
}

export function getWarriorResume(): WarriorResumeSession | null {
  const value = sessionStorage.getItem(warriorResumeKey);
  if (!value) return null;
  try {
    const resume = JSON.parse(value) as WarriorResumeSession;
    return typeof resume.fileName === "string" && typeof resume.resultId === "string" ? resume : null;
  } catch {
    return null;
  }
}

export function setWarriorApplication(application: WarriorApplication) {
  sessionStorage.setItem(warriorApplicationKey, JSON.stringify(application));
}

export function getWarriorApplication(): WarriorApplication | null {
  const value = sessionStorage.getItem(warriorApplicationKey);
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
  sessionStorage.setItem(warriorReportDraftKey, JSON.stringify(draft));
}

export function getWarriorReportDraft(): WarriorReportDraftSession | null {
  const value = sessionStorage.getItem(warriorReportDraftKey);
  if (!value) return null;
  try {
    const draft = JSON.parse(value) as WarriorReportDraftSession;
    return typeof draft.step === "number" ? draft : null;
  } catch {
    return null;
  }
}

export function clearWarriorReportDraft() {
  sessionStorage.removeItem(warriorReportDraftKey);
}

export function clearWarriorSession() {
  sessionStorage.removeItem(warriorAccessTokenKey);
  sessionStorage.removeItem(warriorIdentityKey);
  sessionStorage.removeItem(warriorProfileSetupKey);
  sessionStorage.removeItem(warriorResumeKey);
  sessionStorage.removeItem(warriorApplicationKey);
  sessionStorage.removeItem(warriorReportDraftKey);
}