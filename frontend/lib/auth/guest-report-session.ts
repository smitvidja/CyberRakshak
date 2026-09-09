let pendingEvidenceFiles: File[] = [];

const pendingSubmitKey = "cyberrakshak.pending-guest-submit";

export function setGuestEvidenceFiles(files: File[]) {
  pendingEvidenceFiles = [...files];
}

export function getGuestEvidenceFiles() {
  return [...pendingEvidenceFiles];
}

export function clearGuestEvidenceFiles() {
  pendingEvidenceFiles = [];
}

export function markGuestDraftForFinalSubmit() {
  sessionStorage.setItem(pendingSubmitKey, "true");
}

export function consumeGuestDraftFinalSubmit() {
  const pending = sessionStorage.getItem(pendingSubmitKey) === "true";
  sessionStorage.removeItem(pendingSubmitKey);
  return pending;
}
