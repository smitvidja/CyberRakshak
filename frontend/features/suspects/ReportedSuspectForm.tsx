"use client";

import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";

import {UploadDropzone} from "@/components/evidence/UploadDropzone";
import {Button} from "@/components/ui/Button";
import {SelectField, TextArea, TextInput} from "@/components/ui/FormFields";
import {StatePanel, StatusChip, SurfaceCard} from "@/components/ui/Surface";
import {evidenceApi, suspectsApi} from "@/lib/api/complaints";
import {getAccessToken, getReportMode} from "@/lib/auth/citizen-session";

type FieldErrors = Record<string, string>;
type SubmittedReport = {id: string; identifierType: string; identifierValue: string};

const identifierTypes = ["PHONE", "EMAIL", "UPI", "BANK_ACCOUNT", "WEBSITE", "SOCIAL_MEDIA", "OTHER"];

function asString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function validateIdentifier(identifierType: string, value: string) {
  const normalized = value.trim();
  if (!normalized) return "required";
  if (identifierType === "PHONE" && !/^\+?[0-9]{8,15}$/.test(normalized)) return "phone";
  if (identifierType === "EMAIL" && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized)) return "email";
  if (identifierType === "UPI" && !/^[a-zA-Z0-9._-]{2,}@[a-zA-Z]{2,}$/.test(normalized)) return "upi";
  if (identifierType === "WEBSITE" && !/^https?:\/\/\S+$/i.test(normalized)) return "website";
  return "";
}

export function ReportedSuspectForm() {
  const t = useTranslations("suspectReport");
  const locale = useLocale();
  const router = useRouter();
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [sessionReady, setSessionReady] = useState(false);
  const [identifierType, setIdentifierType] = useState("PHONE");
  const [identifierValue, setIdentifierValue] = useState("");
  const [description, setDescription] = useState("");
  const [evidenceDescription, setEvidenceDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [serviceError, setServiceError] = useState("");
  const [evidenceError, setEvidenceError] = useState("");
  const [evidenceMetadata, setEvidenceMetadata] = useState<{fileName: string; fileSize: number} | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState<SubmittedReport | null>(null);

  useEffect(() => {
    if (getReportMode() === "identified") setAccessToken(getAccessToken());
    setSessionReady(true);
  }, []);

  function clearFieldError(field: string) {
    setErrors((current) => ({...current, [field]: ""}));
  }

  function validate() {
    const nextErrors: FieldErrors = {};
    const identifierError = validateIdentifier(identifierType, identifierValue);
    if (identifierError) nextErrors.identifierValue = t("validation." + identifierError);
    setErrors(nextErrors);
    return Object.keys(nextErrors).length === 0;
  }

  async function uploadEvidence(reportId: string) {
    if (!file || !accessToken) return true;
    setEvidenceError("");
    const payload = new FormData();
    payload.set("suspect_report_id", reportId);
    payload.set("description", evidenceDescription.trim());
    payload.set("file", file);
    const result = await evidenceApi.upload(payload, {accessToken});
    if (!result.ok) {
      setEvidenceError(t("evidenceError"));
      return false;
    }
    setEvidenceMetadata({fileName: asString(result.data.file_name) || file.name, fileSize: Number(result.data.file_size) || file.size});
    return true;
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!validate() || !accessToken) return;
    setSubmitting(true);
    setServiceError("");
    const result = await suspectsApi.createReport({identifier_type: identifierType, identifier_value: identifierValue.trim(), description: description.trim() || null}, {accessToken});
    if (!result.ok) {
      setServiceError(t("submitError"));
      setSubmitting(false);
      return;
    }
    const report = {id: asString(result.data.id), identifierType: asString(result.data.identifier_type), identifierValue: asString(result.data.identifier_value)};
    setSubmitted(report);
    await uploadEvidence(report.id);
    setSubmitting(false);
  }

  async function retryEvidence() {
    if (!submitted) return;
    setSubmitting(true);
    await uploadEvidence(submitted.id);
    setSubmitting(false);
  }

  if (!sessionReady) return <main className="shell-container py-8 sm:py-12"><StatePanel title={t("loadingTitle")} tone="loading">{t("loadingCopy")}</StatePanel></main>;
  if (!accessToken) return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-3xl space-y-6"><p className="eyebrow">{t("eyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("title")}</h1><StatePanel action={<Button onClick={() => router.push("/" + locale + "/report-crime/verify")}>{t("createProfileAction")}</Button>} title={t("profileRequiredTitle")} tone="info">{t("profileRequiredCopy")}</StatePanel></div></main>;

  if (submitted) return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-3xl space-y-6"><p className="eyebrow">{t("submittedEyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("submittedTitle")}</h1><StatePanel title={t("submittedPanelTitle")} tone="success">{t("submittedCopy")}</StatePanel><SurfaceCard heading={t("submittedDetailsTitle")}><dl className="grid gap-4 sm:grid-cols-3"><div><dt className="text-sm font-bold text-[var(--muted)]">{t("identifierTypeLabel")}</dt><dd className="mt-1 text-sm text-[var(--ink)]">{t("identifierTypes." + submitted.identifierType)}</dd></div><div><dt className="text-sm font-bold text-[var(--muted)]">{t("identifierValueLabel")}</dt><dd className="mt-1 break-words text-sm text-[var(--ink)]">{submitted.identifierValue}</dd></div><div><dt className="text-sm font-bold text-[var(--muted)]">{t("statusLabel")}</dt><dd className="mt-1"><StatusChip label={t("status.submitted")} tone="success" /></dd></div></dl></SurfaceCard>{evidenceMetadata ? <StatePanel title={t("evidenceUploadedTitle")} tone="success">{t("evidenceUploaded", evidenceMetadata)}</StatePanel> : null}{file && evidenceError ? <StatePanel action={<Button isLoading={submitting} onClick={retryEvidence} variant="outline">{t("retryEvidence")}</Button>} title={t("evidencePendingTitle")} tone="warning">{evidenceError}</StatePanel> : null}<StatePanel title={t("checkTitle")} tone="info">{t("checkCopy")}</StatePanel></div></main>;

  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-4xl space-y-6"><p className="eyebrow">{t("eyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("title")}</h1><p className="max-w-3xl text-base leading-7 text-[var(--muted)]">{t("intro")}</p><StatePanel title={t("checkTitle")} tone="info">{t("checkCopy")}</StatePanel>{serviceError ? <StatePanel title={t("errorTitle")} tone="error">{serviceError}</StatePanel> : null}<form className="space-y-6" noValidate onSubmit={submit}><SurfaceCard heading={t("formTitle")}><div className="grid gap-4 sm:grid-cols-2"><SelectField id="suspect-identifier-type" label={t("identifierTypeLabel")} onChange={(event) => { setIdentifierType(event.target.value); clearFieldError("identifierValue"); }} options={identifierTypes.map((type) => ({label: t("identifierTypes." + type), value: type}))} value={identifierType} /><TextInput description={t("identifierValueHelp")} error={errors.identifierValue} id="suspect-identifier-value" label={t("identifierValueLabel")} onChange={(event) => { setIdentifierValue(event.target.value); clearFieldError("identifierValue"); }} required value={identifierValue} /></div><div className="mt-4"><TextArea description={t("descriptionHelp")} id="suspect-description" label={t("descriptionLabel")} onChange={(event) => setDescription(event.target.value)} value={description} /></div></SurfaceCard><SurfaceCard heading={t("evidenceTitle")}><UploadDropzone accept=".pdf,.png,.jpg,.jpeg" browseLabel={t("browseEvidence")} description={t("evidenceHelp")} error={evidenceError} id="suspect-evidence" maxSizeLabel={t("evidenceSize")} onFilesSelected={(files) => { setFile(files[0] ?? null); setEvidenceError(""); }} title={file ? file.name : t("evidenceUploadTitle")} /><div className="mt-4"><TextInput id="suspect-evidence-note" label={t("evidenceNoteLabel")} onChange={(event) => setEvidenceDescription(event.target.value)} value={evidenceDescription} /></div></SurfaceCard><Button isLoading={submitting} type="submit">{t("submitAction")}</Button></form></div></main>;
}
