"use client";

import {useEffect, useRef, useState, type FormEvent} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowLeft, ArrowRight, CheckCircle2, FileText, Info, Send, ShieldCheck, Trash2} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {UploadDropzone} from "@/components/evidence/UploadDropzone";
import {CheckboxField, SelectField, TextArea, TextInput} from "@/components/ui/FormFields";
import {evidenceApi} from "@/lib/api/complaints";
import {warriorReportsApi, type WarriorReportType} from "@/lib/api/cyber-warriors";
import {getWarriorToken} from "@/lib/auth/warrior-session";
import {ReportError, ReportHeading, WarriorReportFrame, type ReportStep} from "./WarriorReportFrame";
import {reportCategories} from "./warriorReportMeta";

type EvidenceItem = {fileName: string; fileSize: number; id: string};

const maxEvidenceFiles = 10;
const maxEvidenceBytes = 10 * 1024 * 1024;
const allowedEvidenceExtensions = [".jpg", ".jpeg", ".png", ".pdf", ".doc", ".docx", ".txt"];

function extensionOf(name: string) {
  const index = name.lastIndexOf(".");
  return index === -1 ? "" : name.slice(index).toLowerCase();
}

export function WarriorReportWizard() {
  const t = useTranslations("warriorReport");
  const locale = useLocale();
  const router = useRouter();
  const [step, setStep] = useState<ReportStep>(1);
  const [category, setCategory] = useState<WarriorReportType | "">("");
  const [incidentDate, setIncidentDate] = useState("");
  const [incidentTime, setIncidentTime] = useState("");
  const [platform, setPlatform] = useState("");
  const [description, setDescription] = useState("");
  const [websiteUrl, setWebsiteUrl] = useState("");
  const [accountRef, setAccountRef] = useState("");
  const [otherInfo, setOtherInfo] = useState("");
  const [evidenceDetails, setEvidenceDetails] = useState("");
  const [evidenceItems, setEvidenceItems] = useState<EvidenceItem[]>([]);
  const [reportId, setReportId] = useState<string | null>(null);
  const [declared, setDeclared] = useState(false);
  const [error, setError] = useState("");
  const [evidenceError, setEvidenceError] = useState("");
  const [savingStep, setSavingStep] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const tokenRef = useRef<string | null>(null);

  useEffect(() => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    tokenRef.current = token;
  }, [locale, router]);

  const platformOptions = [
    {label: t("platformSelect"), value: ""},
    {label: t("platformWhatsApp"), value: "WhatsApp"},
    {label: t("platformEmail"), value: "Email"},
    {label: t("platformSms"), value: "SMS"},
    {label: t("platformWebsite"), value: "Website"},
    {label: t("platformSocial"), value: "Social Media"},
    {label: t("platformCall"), value: "Phone Call"},
    {label: t("platformOther"), value: "Other"}
  ];

  function composeDescription() {
    const lines = [description.trim()];
    const extras: string[] = [];
    if (incidentDate) extras.push(t("summaryDate") + ": " + incidentDate + (incidentTime ? " " + incidentTime : ""));
    if (platform) extras.push(t("summaryPlatform") + ": " + platform);
    if (websiteUrl.trim()) extras.push(t("summaryUrl") + ": " + websiteUrl.trim());
    if (accountRef.trim()) extras.push(t("summaryAccount") + ": " + accountRef.trim());
    if (otherInfo.trim()) extras.push(t("summaryOther") + ": " + otherInfo.trim());
    if (extras.length) lines.push("", extras.join("\n"));
    return lines.join("\n");
  }

  async function saveDraft(): Promise<boolean> {
    const token = tokenRef.current;
    if (!token || !category) return false;
    if (description.trim().length < 10) {
      setError(t("descriptionTooShort"));
      return false;
    }
    setSavingStep(true);
    setError("");
    const categoryLabel = reportCategories.find((item) => item.value === category)?.labelKey ?? "categoryOther";
    const payload = {description: composeDescription(), report_type: category, title: t(categoryLabel) + " " + t("reportTitleSuffix")};
    const result = reportId
      ? await warriorReportsApi.update(reportId, payload, {accessToken: token})
      : await warriorReportsApi.create(payload, {accessToken: token});
    setSavingStep(false);
    if (!result.ok) {
      setError(t("saveDraftError"));
      return false;
    }
    setReportId(result.data.id);
    return true;
  }

  function goToIdentify() {
    if (!category) {
      setError(t("categoryRequiredError"));
      return;
    }
    setError("");
    setStep(2);
  }

  async function goToEvidence(event: FormEvent) {
    event.preventDefault();
    const saved = await saveDraft();
    if (saved) setStep(3);
  }

  function goToReview() {
    setStep(4);
  }

  async function uploadEvidenceFile(file: File) {
    const token = tokenRef.current;
    if (!token || !reportId) return;
    if (evidenceItems.length >= maxEvidenceFiles) {
      setEvidenceError(t("evidenceMaxFilesError"));
      return;
    }
    if (!allowedEvidenceExtensions.includes(extensionOf(file.name))) {
      setEvidenceError(t("evidenceTypeError"));
      return;
    }
    if (file.size > maxEvidenceBytes) {
      setEvidenceError(t("evidenceSizeError"));
      return;
    }
    setUploading(true);
    setEvidenceError("");
    const payload = new FormData();
    payload.set("warrior_report_id", reportId);
    if (evidenceDetails.trim()) payload.set("description", evidenceDetails.trim());
    payload.set("file", file);
    const result = await evidenceApi.upload(payload, {accessToken: token});
    setUploading(false);
    if (!result.ok) {
      setEvidenceError(t("evidenceUploadError"));
      return;
    }
    setEvidenceItems((current) => [...current, {
      fileName: typeof result.data.file_name === "string" ? result.data.file_name : file.name,
      fileSize: typeof result.data.file_size === "number" ? result.data.file_size : file.size,
      id: String(result.data.id)
    }]);
  }

  async function removeEvidence(id: string) {
    const token = tokenRef.current;
    if (!token) return;
    await evidenceApi.remove(id, {accessToken: token});
    setEvidenceItems((current) => current.filter((item) => item.id !== id));
  }

  async function submitReport() {
    const token = tokenRef.current;
    if (!token || !reportId || !declared) return;
    setSubmitting(true);
    setError("");
    const result = await warriorReportsApi.submit(reportId, {accessToken: token});
    setSubmitting(false);
    if (!result.ok) {
      setError(t("submitError"));
      return;
    }
    router.push("/" + locale + "/cyber-warrior/reports/" + reportId + "/submitted");
  }

  const selectedCategory = reportCategories.find((item) => item.value === category);
  const descriptionCount = description.length;

  if (step === 1) {
    return (
      <WarriorReportFrame activeStep={1}>
        <ReportHeading copy={t("identifyCopy")} eyebrow={t("stepOfFour", {step: 1})} title={t("identifyTitle")} />
        <p className="warrior-report-field-label">{t("categoryLabel")} <span aria-hidden="true">*</span></p>
        <div className="warrior-category-grid">
          {reportCategories.map((item) => (
            <button
              className={"warrior-category-tile " + (category === item.value ? "is-selected" : "")}
              key={item.value}
              onClick={() => setCategory(item.value)}
              type="button"
            >
              <span aria-hidden="true"><item.icon size={22} /></span>
              <strong>{t(item.labelKey)}</strong>
              <small>{t(item.noteKey)}</small>
            </button>
          ))}
        </div>
        <ReportError message={error} />
        <footer className="warrior-application-actions">
          <Button onClick={() => router.push("/" + locale + "/cyber-warrior/dashboard")} type="button" variant="outline">{t("cancelAction")}</Button>
          <Button onClick={goToIdentify} type="button">{t("nextDescribe")}<ArrowRight aria-hidden="true" size={17} /></Button>
        </footer>
      </WarriorReportFrame>
    );
  }

  if (step === 2) {
    return (
      <WarriorReportFrame activeStep={2}>
        <ReportHeading copy={t("describeCopy")} eyebrow={t("stepOfFour", {step: 2})} title={t("describeTitle")} />
        <form onSubmit={goToEvidence}>
          <div className="warrior-application-form-grid">
            <TextInput id="report-date" label={t("incidentDateLabel")} onChange={(event) => setIncidentDate(event.target.value)} required type="date" value={incidentDate} />
            <TextInput id="report-time" label={t("incidentTimeLabel")} onChange={(event) => setIncidentTime(event.target.value)} type="time" value={incidentTime} />
            <SelectField id="report-platform" label={t("platformLabel")} onChange={(event) => setPlatform(event.target.value)} options={platformOptions} value={platform} />
          </div>
          <TextArea
            description={t("descriptionCounter", {count: descriptionCount})}
            id="report-description"
            label={t("descriptionLabel")}
            maxLength={2000}
            onChange={(event) => setDescription(event.target.value)}
            required
            value={description}
          />
          <fieldset className="warrior-application-fieldset">
            <legend>{t("additionalDetailsTitle")}</legend>
            <div className="warrior-application-form-grid">
              <TextInput id="report-url" label={t("websiteUrlLabel")} onChange={(event) => setWebsiteUrl(event.target.value)} type="url" value={websiteUrl} />
              <TextInput id="report-account" label={t("accountRefLabel")} onChange={(event) => setAccountRef(event.target.value)} value={accountRef} />
              <TextInput id="report-other" label={t("otherInfoLabel")} onChange={(event) => setOtherInfo(event.target.value)} value={otherInfo} />
            </div>
          </fieldset>
          <ReportError message={error} />
          <footer className="warrior-application-actions">
            <Button onClick={() => setStep(1)} type="button" variant="outline"><ArrowLeft aria-hidden="true" size={17} />{t("previousIdentify")}</Button>
            <Button isLoading={savingStep} type="submit">{t("nextEvidence")}<ArrowRight aria-hidden="true" size={17} /></Button>
          </footer>
        </form>
      </WarriorReportFrame>
    );
  }

  if (step === 3) {
    return (
      <WarriorReportFrame activeStep={3}>
        <ReportHeading copy={t("evidenceCopy")} eyebrow={t("stepOfFour", {step: 3})} title={t("evidenceTitle")} />
        <UploadDropzone
          accept={allowedEvidenceExtensions.join(",")}
          browseLabel={t("chooseFiles")}
          description={t("dropDescription")}
          disabled={uploading || evidenceItems.length >= maxEvidenceFiles}
          error={evidenceError}
          id="report-evidence-input"
          maxSizeLabel={t("evidenceRules")}
          multiple
          onFilesSelected={(files) => { files.forEach((file) => void uploadEvidenceFile(file)); }}
          title={t("dropTitle")}
        />
        {evidenceItems.length > 0 ? (
          <div className="warrior-evidence-list">
            <p className="warrior-report-field-label">{t("uploadedFiles", {count: evidenceItems.length, max: maxEvidenceFiles})}</p>
            {evidenceItems.map((item) => (
              <div className="warrior-evidence-row" key={item.id}>
                <span aria-hidden="true"><FileText size={20} /></span>
                <div><strong>{item.fileName}</strong><small>{(item.fileSize / 1024 / 1024).toFixed(2)} MB</small></div>
                <button aria-label={t("removeEvidenceAction")} onClick={() => void removeEvidence(item.id)} type="button"><Trash2 aria-hidden="true" size={16} /></button>
              </div>
            ))}
          </div>
        ) : null}
        <TextArea id="report-evidence-details" label={t("evidenceDetailsLabel")} maxLength={1000} onChange={(event) => setEvidenceDetails(event.target.value)} value={evidenceDetails} />
        <ReportError message={error} />
        <footer className="warrior-application-actions">
          <Button onClick={() => setStep(2)} type="button" variant="outline"><ArrowLeft aria-hidden="true" size={17} />{t("previousDescribe")}</Button>
          <Button onClick={goToReview} type="button">{t("nextReview")}<ArrowRight aria-hidden="true" size={17} /></Button>
        </footer>
      </WarriorReportFrame>
    );
  }

  return (
    <WarriorReportFrame activeStep={4}>
      <div className="warrior-review-toolbar">
        <span><CheckCircle2 aria-hidden="true" size={18} />{t("reviewReady")}</span>
        <Button onClick={() => setStep(1)} size="sm" variant="outline">{t("editAllAction")}</Button>
      </div>
      <ReportHeading copy={t("reviewCopy")} eyebrow={t("stepOfFour", {step: 4})} title={t("reviewTitle")} />
      <div className="warrior-review-sections">
        <section>
          <h3>{t("incidentTypeTitle")}</h3>
          <dl><div className="wide"><dt>{selectedCategory ? t(selectedCategory.labelKey) : ""}</dt><dd>{selectedCategory ? t(selectedCategory.noteKey) : ""}</dd></div></dl>
        </section>
        <section>
          <h3>{t("incidentDetailsTitle")}</h3>
          <dl>
            <div><dt>{t("summaryDate")}</dt><dd>{incidentDate || t("notProvided")} {incidentTime}</dd></div>
            <div><dt>{t("summaryPlatform")}</dt><dd>{platform || t("notProvided")}</dd></div>
            <div className="wide"><dt>{t("descriptionLabel")}</dt><dd>{description}</dd></div>
          </dl>
        </section>
        <section>
          <h3>{t("evidenceUploadedTitle", {count: evidenceItems.length})}</h3>
          {evidenceItems.length ? (
            <ul className="warrior-review-evidence-list">
              {evidenceItems.map((item) => <li key={item.id}><FileText aria-hidden="true" size={15} />{item.fileName}</li>)}
            </ul>
          ) : <p className="warrior-report-field-label">{t("notProvided")}</p>}
        </section>
        <section>
          <h3>{t("additionalDetailsTitle")}</h3>
          <dl>
            <div><dt>{t("websiteUrlLabel")}</dt><dd>{websiteUrl || t("notProvided")}</dd></div>
            <div><dt>{t("accountRefLabel")}</dt><dd>{accountRef || t("notProvided")}</dd></div>
            <div className="wide"><dt>{t("otherInfoLabel")}</dt><dd>{otherInfo || t("notProvided")}</dd></div>
          </dl>
        </section>
      </div>
      <div className="warrior-declaration">
        <div className="warrior-tips-before-submit">
          <p><Info aria-hidden="true" size={16} />{t("declarationHintReview")}</p>
          <p><ShieldCheck aria-hidden="true" size={16} />{t("declarationHintReferenceId")}</p>
        </div>
        <CheckboxField checked={declared} id="report-declaration" label={t("declaration")} onCheckedChange={(event) => setDeclared(event.target.checked)} required />
      </div>
      <ReportError message={error} />
      <footer className="warrior-application-actions">
        <Button onClick={() => setStep(3)} type="button" variant="outline"><ArrowLeft aria-hidden="true" size={17} />{t("previousEvidence")}</Button>
        <Button disabled={!declared} isLoading={submitting} onClick={submitReport} type="button"><Send aria-hidden="true" size={16} />{t("submitReportAction")}</Button>
      </footer>
    </WarriorReportFrame>
  );
}
