export type SuspectIdentifierHandoff = {identifierType: string; identifierValue: string};

const HANDOFF_KEY = "cyberrakshak.suspect-identifier-handoff";
const ALLOWED_TYPES = new Set(["PHONE", "EMAIL", "UPI", "BANK_ACCOUNT", "WEBSITE", "SOCIAL_MEDIA", "OTHER"]);

export function saveSuspectHandoff(value: SuspectIdentifierHandoff) {
  if (typeof window === "undefined" || !ALLOWED_TYPES.has(value.identifierType) || !value.identifierValue.trim()) return;
  window.sessionStorage.setItem(HANDOFF_KEY, JSON.stringify({identifierType: value.identifierType, identifierValue: value.identifierValue.trim()}));
}

export function takeSuspectHandoff(): SuspectIdentifierHandoff | null {
  if (typeof window === "undefined") return null;
  const stored = window.sessionStorage.getItem(HANDOFF_KEY);
  window.sessionStorage.removeItem(HANDOFF_KEY);
  if (!stored) return null;
  try {
    const value = JSON.parse(stored) as SuspectIdentifierHandoff;
    return ALLOWED_TYPES.has(value.identifierType) && typeof value.identifierValue === "string" && value.identifierValue.trim() ? value : null;
  } catch {
    return null;
  }
}
