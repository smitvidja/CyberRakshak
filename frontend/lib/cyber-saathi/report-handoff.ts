import type {SaathiHandoff} from "@/types/cyber-saathi";

export type CyberSaathiRuntimeHandoff = {
  conversationId: string;
  files: File[];
  prefill: SaathiHandoff["prefill"];
};

let runtimeHandoff: CyberSaathiRuntimeHandoff | null = null;

export function prepareCyberSaathiReportHandoff(value: CyberSaathiRuntimeHandoff) {
  runtimeHandoff = value;
}

export function getCyberSaathiReportHandoff() {
  return runtimeHandoff;
}

export function updateCyberSaathiReportHandoffFiles(files: File[]) {
  if (runtimeHandoff) runtimeHandoff = {...runtimeHandoff, files};
}

export function clearCyberSaathiReportHandoff() {
  runtimeHandoff = null;
}
