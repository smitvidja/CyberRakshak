import type {SaathiHandoff} from "@/types/cyber-saathi";

export type CyberSaathiRuntimeHandoff = {
  conversationId: string;
  files: File[];
  prefill: SaathiHandoff["prefill"];
};

const storageKey = "cyberrakshak.cyber-saathi.report-handoff.v1";
let runtimeHandoff: CyberSaathiRuntimeHandoff | null = null;

export function prepareCyberSaathiReportHandoff(value: CyberSaathiRuntimeHandoff) {
  runtimeHandoff = value;
  localStorage.setItem(storageKey, JSON.stringify({
    conversationId: value.conversationId,
    prefill: value.prefill
  }));
}

export function getCyberSaathiReportHandoff() {
  if (runtimeHandoff) return runtimeHandoff;
  const stored = localStorage.getItem(storageKey);
  if (!stored) return null;
  try {
    const value = JSON.parse(stored) as Omit<CyberSaathiRuntimeHandoff, "files">;
    if (!value.conversationId || !value.prefill || typeof value.prefill !== "object") return null;
    runtimeHandoff = {...value, files: []};
    return runtimeHandoff;
  } catch {
    localStorage.removeItem(storageKey);
    return null;
  }
}

export function updateCyberSaathiReportHandoffFiles(files: File[]) {
  if (runtimeHandoff) runtimeHandoff = {...runtimeHandoff, files};
}

export function clearCyberSaathiReportHandoff() {
  runtimeHandoff = null;
  localStorage.removeItem(storageKey);
}
