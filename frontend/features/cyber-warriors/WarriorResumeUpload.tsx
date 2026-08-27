"use client";

import {useEffect, useRef, useState, type DragEvent} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowRight, CheckCircle2, FileText, RefreshCw, UploadCloud} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {resumeApi} from "@/lib/api/cyber-warriors";
import {getWarriorToken, setWarriorResume} from "@/lib/auth/warrior-session";
import {ApplicationError, ApplicationHeading, WarriorApplicationFrame} from "./WarriorApplicationShell";

const allowedExtensions = [".pdf", ".doc", ".docx"];
const maximumBytes = 10 * 1024 * 1024;

function extensionOf(name: string) {
  return name.slice(name.lastIndexOf(".")).toLowerCase();
}

export function WarriorResumeUpload() {
  const t = useTranslations("warriorApplication");
  const locale = useLocale();
  const router = useRouter();
  const fileInput = useRef<HTMLInputElement>(null);
  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<"idle" | "uploading" | "complete" | "failed">("idle");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!getWarriorToken()) router.replace("/" + locale + "/cyber-warrior/verify");
  }, [locale, router]);

  function chooseFile(candidate?: File) {
    if (!candidate) return;
    if (!allowedExtensions.includes(extensionOf(candidate.name))) {
      setError(t("resumeTypeError"));
      setFile(null);
      return;
    }
    if (candidate.size > maximumBytes) {
      setError(t("resumeSizeError"));
      setFile(null);
      return;
    }
    setFile(candidate);
    setError("");
    setPhase("idle");
  }

  function drop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    chooseFile(event.dataTransfer.files[0]);
  }

  async function upload() {
    const token = getWarriorToken();
    if (!file || !token) return;
    setError("");
    setPhase("uploading");
    const body = new FormData();
    body.append("file", file);
    const result = await resumeApi.upload(body, {accessToken: token});
    if (!result.ok || result.data.status === "FAILED") {
      setError(result.ok ? result.data.error_message ?? t("resumeUploadError") : t("resumeUploadError"));
      setPhase("failed");
      return;
    }
    setWarriorResume({fileName: result.data.resume_file_name, resultId: result.data.id});
    setPhase("complete");
  }

  return (
    <WarriorApplicationFrame activeStep={1}>
      <ApplicationHeading eyebrow={t("uploadEyebrow")} title={t("uploadTitle")} copy={t("uploadCopy")} />
      <div className="warrior-upload-grid">
        <div>
          <div
            className={"warrior-resume-dropzone " + (file ? "has-file" : "")}
            onDragOver={(event) => event.preventDefault()}
            onDrop={drop}
          >
            <UploadCloud aria-hidden="true" size={34} />
            <strong>{t("dropTitle")}</strong>
            <span>{t("dropOr")}</span>
            <Button onClick={() => fileInput.current?.click()} type="button" variant="outline">{t("browseAction")}</Button>
            <small>{t("fileRules")}</small>
            <input
              accept=".pdf,.doc,.docx"
              className="sr-only"
              onChange={(event) => chooseFile(event.target.files?.[0])}
              ref={fileInput}
              style={{caretColor: "transparent"}}
              type="file"
            />
          </div>
          {file ? (
            <div className="warrior-uploaded-file">
              <span><FileText aria-hidden="true" size={22} /></span>
              <div><strong>{file.name}</strong><small>{(file.size / 1024 / 1024).toFixed(2)} MB</small></div>
              {phase === "complete" ? <CheckCircle2 aria-label={t("uploadComplete")} className="text-[#16835d]" size={22} /> : null}
            </div>
          ) : null}
          {phase === "uploading" ? (
            <div className="warrior-processing" aria-live="polite">
              <div><strong>{t("processingTitle")}</strong><span>{t("processingCopy")}</span></div>
              <span className="warrior-processing-track"><i /></span>
            </div>
          ) : null}
          <ApplicationError message={error} />
        </div>
        <aside className="warrior-extraction-summary">
          <h3>{t("extractTitle")}</h3>
          <p>{t("extractCopy")}</p>
          <ul>
            <li>{t("extractPersonal")}</li>
            <li>{t("extractEducation")}</li>
            <li>{t("extractExperience")}</li>
            <li>{t("extractSkills")}</li>
            <li>{t("extractCertifications")}</li>
          </ul>
        </aside>
      </div>
      <footer className="warrior-application-actions">
        <Button disabled={!file || phase === "uploading" || phase === "complete"} isLoading={phase === "uploading"} onClick={upload}>
          {phase === "failed" ? <RefreshCw aria-hidden="true" size={17} /> : <UploadCloud aria-hidden="true" size={17} />}
          {phase === "failed" ? t("retryAction") : t("uploadAction")}
        </Button>
        <Button disabled={phase !== "complete"} onClick={() => router.push("/" + locale + "/cyber-warrior/apply/review")}>
          {t("continueDetails")}<ArrowRight aria-hidden="true" size={17} />
        </Button>
      </footer>
    </WarriorApplicationFrame>
  );
}
