import type {MockIdentityProfile} from "@/lib/api/auth";

const warriorAccessTokenKey = "cyberrakshak.warrior-access-token";
const warriorIdentityKey = "cyberrakshak.warrior-identity";
const warriorProfileSetupKey = "cyberrakshak.warrior-profile-setup";

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