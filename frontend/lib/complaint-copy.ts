import {complaintsApi} from "@/lib/api/complaints";

export type ComplaintCopyAccess = {complaintId: string; accessToken: string | null};

const STORE_KEY = "cyberrakshak.complaint-copy-access";

type Store = Record<string, ComplaintCopyAccess>;

function readStore(): Store {
  if (typeof window === "undefined") return {};
  try {
    const raw = window.sessionStorage.getItem(STORE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw) as Store;
    return parsed && typeof parsed === "object" && !Array.isArray(parsed) ? parsed : {};
  } catch {
    return {};
  }
}

/**
 * Remember how to fetch a submitted complaint's copy, keyed by complaint number.
 *
 * For an anonymous complaint this holds the one-time capability returned at
 * submission. It lives in sessionStorage, never the URL, so it cannot leak
 * through browser history, referrers or server access logs. Losing it means the
 * full copy cannot be recovered - that is deliberate, and the UI says so.
 */
export function rememberComplaintCopyAccess(complaintNumber: string, access: ComplaintCopyAccess) {
  if (typeof window === "undefined" || !complaintNumber || !access.complaintId) return;
  const store = readStore();
  store[complaintNumber] = access;
  try {
    window.sessionStorage.setItem(STORE_KEY, JSON.stringify(store));
  } catch {
    // A full or unavailable sessionStorage must not break submission.
  }
}

export function getComplaintCopyAccess(complaintNumber: string): ComplaintCopyAccess | null {
  return readStore()[complaintNumber] ?? null;
}

function saveBlob(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  // Release the object URL on the next tick so the download has started.
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
}

export type CopyDownloadOutcome = "ok" | "unauthorized" | "error";

/**
 * Fetch the complaint copy as a blob and hand it to the browser.
 *
 * Authorization travels in headers - a session bearer token for an identified
 * complaint, or the scoped capability for an anonymous one - never in the URL.
 */
export async function downloadComplaintCopy(options: {
  accessToken?: string | null;
  complaintId: string;
  complaintNumber: string;
  sessionToken?: string | null;
}): Promise<CopyDownloadOutcome> {
  const headers: Record<string, string> = {};
  if (options.accessToken) headers["X-Complaint-Access-Token"] = options.accessToken;

  const result = await complaintsApi.downloadCopy(options.complaintId, {
    accessToken: options.sessionToken ?? undefined,
    headers
  });

  if (!result.ok) {
    const code = result.error.code;
    return code === "UNAUTHORIZED" || code === "COMPLAINT_ACCESS_DENIED" || code === "COMPLAINT_ACCESS_TOKEN_REQUIRED"
      ? "unauthorized"
      : "error";
  }

  saveBlob(result.data, `CyberRakshak-Complaint-${options.complaintNumber}.pdf`);
  return "ok";
}

// useSyncExternalStore needs a referentially stable snapshot, so the parsed
// record is cached per complaint number. Reading through a store rather than an
// effect keeps the server snapshot (null) and the first client render in
// agreement, so there is no hydration mismatch and no cascading render.
let snapshotKey: string | null = null;
let snapshotValue: ComplaintCopyAccess | null = null;

export function subscribeToComplaintCopyAccess() {
  // The record is written on the previous screen and never changes while this
  // screen is mounted, so there is nothing to subscribe to.
  return () => undefined;
}

export function getComplaintCopyAccessSnapshot(complaintNumber: string): ComplaintCopyAccess | null {
  if (snapshotKey !== complaintNumber) {
    snapshotKey = complaintNumber;
    snapshotValue = getComplaintCopyAccess(complaintNumber);
  }
  return snapshotValue;
}

export function getServerComplaintCopyAccessSnapshot(): ComplaintCopyAccess | null {
  return null;
}
