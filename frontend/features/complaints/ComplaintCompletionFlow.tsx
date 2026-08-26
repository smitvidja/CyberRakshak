"use client";

import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";

import {DeclarationBox, ReviewSection, StatusTimeline, StepIndicator} from "@/components/common/Workflow";
import {Button} from "@/components/ui/Button";
import {TextInput} from "@/components/ui/FormFields";
import {ResponsiveDataList, type DataListRow} from "@/components/ui/ResponsiveDataList";
import {StatePanel, StatusChip, SurfaceCard} from "@/components/ui/Surface";
import {complaintsApi} from "@/lib/api/complaints";
import type {ApiRecord} from "@/lib/api/auth";
import {getAccessToken, getComplaintDraft, getComplaintEvidence, getReportMode, setComplaintDraft} from "@/lib/auth/citizen-session";

type TrackingRecord = ApiRecord & {history?: ApiRecord[]};

function asRecord(value: unknown): ApiRecord | null {
  return value && typeof value === "object" && !Array.isArray(value) ? value as ApiRecord : null;
}

function asString(value: unknown) {
  return typeof value === "string" ? value : "";
}

function requestOptions() {
  return getReportMode() === "identified" ? {accessToken: getAccessToken() ?? undefined} : undefined;
}

function reviewPath(locale: string, draftId: string) {
  return "/" + locale + "/report-crime/" + draftId + "/review";
}

function statusTone(status: string) {
  if (status === "SUBMITTED" || status === "RESOLVED") return "success" as const;
  if (status === "IN_REVIEW" || status === "UNDER_REVIEW") return "info" as const;
  if (status === "ACTION_REQUIRED") return "warning" as const;
  return "neutral" as const;
}

function displayDate(value: unknown, locale: string) {
  const date = new Date(asString(value));
  return Number.isNaN(date.valueOf()) ? "-" : new Intl.DateTimeFormat(locale === "hi" ? "hi-IN" : "en-IN", {dateStyle: "medium", timeStyle: "short"}).format(date);
}

function displayAmount(value: unknown, locale: string) {
  const amount = Number(value);
  return Number.isFinite(amount) ? new Intl.NumberFormat(locale === "hi" ? "hi-IN" : "en-IN", {currency: "INR", style: "currency"}).format(amount) : "-";
}

function statusLabel(t: ReturnType<typeof useTranslations>, status: unknown) {
  const normalized = asString(status).toLowerCase();
  return normalized ? t("status." + normalized) : t("status.unknown");
}

export function ComplaintReviewStep({draftId}: {draftId: string}) {
  const t = useTranslations("complaintCompletion");
  const locale = useLocale();
  const router = useRouter();
  const [draft, setDraft] = useState<ApiRecord | null>(null);
  const [accepted, setAccepted] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    async function load() {
      const cached = getComplaintDraft();
      if (cached?.id === draftId && active) setDraft(cached.data);
      if (getReportMode() === "identified" && getAccessToken()) {
        const result = await complaintsApi.getById(draftId, requestOptions());
        if (active && result.ok) {
          setDraft(result.data);
          setComplaintDraft({data: result.data, id: draftId});
        } else if (active && !cached) {
          setError(t("draftUnavailable"));
        }
      } else if (!cached || cached.id !== draftId) {
        setError(t("draftUnavailable"));
      }
      if (active) setLoading(false);
    }
    void load();
    return () => { active = false; };
  }, [draftId, t]);

  async function submit() {
    if (!accepted) {
      setError(t("declarationRequired"));
      return;
    }
    setSubmitting(true);
    setError("");
    const result = await complaintsApi.submit(draftId, requestOptions());
    if (!result.ok) {
      setError(t("submitError"));
      setSubmitting(false);
      return;
    }
    setComplaintDraft({data: result.data, id: draftId});
    const complaintNumber = asString(result.data.complaint_number);
    router.push("/" + locale + "/complaints/submitted/" + encodeURIComponent(complaintNumber));
  }

  if (loading) return <main className="shell-container py-8 sm:py-12"><StatePanel title={t("loadingTitle")} tone="loading">{t("loadingCopy")}</StatePanel></main>;
  if (!draft) return <main className="shell-container py-8 sm:py-12"><StatePanel action={<Button onClick={() => router.push("/" + locale + "/report-crime")}>{t("startAgain")}</Button>} title={t("errorTitle")} tone="error">{error || t("draftUnavailable")}</StatePanel></main>;

  const category = asRecord(draft.category);
  const location = asRecord(draft.location);
  const suspects = Array.isArray(draft.suspects) ? draft.suspects.map((item) => asRecord(item)).filter((item): item is ApiRecord => item !== null) : [];
  const evidence = getComplaintEvidence(draftId);
  const locationValue = [asString(location?.city), asString(location?.district), asString(location?.state)].filter(Boolean).join(", ") || "-";

  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-5xl space-y-6">
    <p className="eyebrow">{t("eyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("title")}</h1><p className="max-w-3xl text-base leading-7 text-[var(--muted)]">{t("intro")}</p>
    <StepIndicator label={t("stepsLabel")} steps={[{label: t("steps.incident"), status: "completed"}, {label: t("steps.people"), status: "completed"}, {label: t("steps.review"), status: "current"}]} />
    {error ? <StatePanel title={t("errorTitle")} tone="error">{error}</StatePanel> : null}
    <ReviewSection action={<Button onClick={() => router.push("/" + locale + "/report-crime/" + draftId + "/incident")} size="sm" variant="outline">{t("editIncident")}</Button>} title={t("incidentSection")} items={[
      {label: t("categoryLabel"), value: asString(category?.name) || "-"},
      {label: t("titleLabel"), value: asString(draft.title)},
      {label: t("descriptionLabel"), value: asString(draft.description)},
      {label: t("incidentAtLabel"), value: displayDate(draft.incident_at, locale)},
      {label: t("amountLabel"), value: displayAmount(draft.financial_loss_amount, locale)},
      {label: t("locationLabel"), value: locationValue}
    ]} />
    <ReviewSection action={<Button onClick={() => router.push("/" + locale + "/report-crime/" + draftId + "/people")} size="sm" variant="outline">{t("editPeople")}</Button>} title={t("peopleSection")} items={[{label: t("peopleLabel"), value: suspects.length ? <ul className="space-y-2">{suspects.map((person, index) => <li key={index}>{[asString(person.name), asString(person.alias), asString(person.contact_details), asString(person.description)].filter(Boolean).join(" - ")}</li>)}</ul> : t("noneProvided")}]} />
    <ReviewSection action={<Button onClick={() => router.push("/" + locale + "/report-crime/" + draftId + "/incident")} size="sm" variant="outline">{t("editEvidence")}</Button>} title={t("evidenceSection")} items={[{label: t("evidenceLabel"), value: evidence.length ? <ul className="space-y-2">{evidence.map((item) => <li key={item.id}>{item.fileName} ({item.fileSize} {t("bytes")})</li>)}</ul> : t("noneProvided") }]} />
    <SurfaceCard heading={t("submitSection")}><div className="space-y-4"><DeclarationBox checked={accepted} description={t("declarationCopy")} id="complaint-declaration" label={t("declarationLabel")} onCheckedChange={(event) => { setAccepted(event.target.checked); setError(""); }} /><Button isLoading={submitting} onClick={submit}>{t("submitAction")}</Button></div></SurfaceCard>
  </div></main>;
}

export function ComplaintSubmitted({complaintNumber}: {complaintNumber: string}) {
  const t = useTranslations("complaintCompletion");
  const locale = useLocale();
  const router = useRouter();
  const [identified, setIdentified] = useState(false);

  useEffect(() => { setIdentified(getReportMode() === "identified"); }, []);

  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-3xl space-y-6"><p className="eyebrow">{t("submittedEyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("submittedTitle")}</h1><StatePanel title={t("referenceTitle")} tone="success"><strong className="block text-lg">{complaintNumber}</strong><span>{t("referenceCopy")}</span></StatePanel><SurfaceCard heading={t("whatNextTitle")}><p className="text-sm leading-6 text-[var(--muted)]">{t("whatNextCopy")}</p><div className="mt-5 flex flex-wrap gap-3"><Button onClick={() => router.push("/" + locale + "/complaints/track/" + encodeURIComponent(complaintNumber))}>{t("trackAction")}</Button>{identified ? <Button onClick={() => router.push("/" + locale + "/complaints")} variant="outline">{t("myReportsAction")}</Button> : null}</div></SurfaceCard></div></main>;
}
export function ComplaintTrackingLookup() {
  const t = useTranslations("complaintCompletion");
  const locale = useLocale();
  const router = useRouter();
  const [number, setNumber] = useState("");
  const [error, setError] = useState("");
  function track(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!number.trim()) { setError(t("referenceRequired")); return; }
    router.push("/" + locale + "/complaints/track/" + encodeURIComponent(number.trim().toUpperCase()));
  }
  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-3xl space-y-6"><p className="eyebrow">{t("trackEyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("trackTitle")}</h1><p className="text-base leading-7 text-[var(--muted)]">{t("trackIntro")}</p><SurfaceCard heading={t("trackFormTitle")}><form className="space-y-4" noValidate onSubmit={track}><TextInput error={error} id="complaint-number" label={t("referenceLabel")} onChange={(event) => { setNumber(event.target.value); setError(""); }} placeholder="CR-2026-XXXXXXXXXX" value={number} /><Button type="submit">{t("trackAction")}</Button></form></SurfaceCard></div></main>;
}

export function ComplaintTrackingDetail({complaintNumber}: {complaintNumber: string}) {
  const t = useTranslations("complaintCompletion");
  const locale = useLocale();
  const [complaint, setComplaint] = useState<TrackingRecord | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  useEffect(() => {
    let active = true;
    async function load() {
      const result = await complaintsApi.track(complaintNumber);
      if (!active) return;
      if (result.ok) setComplaint(result.data as TrackingRecord); else setError(true);
      setLoading(false);
    }
    void load();
    return () => { active = false; };
  }, [complaintNumber]);
  if (loading) return <main className="shell-container py-8 sm:py-12"><StatePanel title={t("trackingLoadingTitle")} tone="loading">{t("trackingLoadingCopy")}</StatePanel></main>;
  if (!complaint || error) return <main className="shell-container py-8 sm:py-12"><StatePanel action={<Button onClick={() => window.location.assign("/" + locale + "/complaints/track")} variant="outline">{t("tryAnother")}</Button>} title={t("trackingErrorTitle")} tone="error">{t("trackingErrorCopy")}</StatePanel></main>;
  const history = Array.isArray(complaint.history) ? complaint.history : [];
  const events = history.length ? history.map((item) => ({label: statusLabel(t, item.status), timestamp: displayDate(item.created_at, locale), tone: statusTone(asString(item.status))})) : [{label: statusLabel(t, complaint.status), timestamp: displayDate(complaint.submitted_at || complaint.created_at, locale), tone: statusTone(asString(complaint.status))}];
  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-4xl space-y-6"><p className="eyebrow">{t("trackEyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("trackingTitle")}</h1><SurfaceCard heading={t("trackingSummaryTitle")}><dl className="grid gap-4 sm:grid-cols-3"><div><dt className="text-sm font-bold text-[var(--muted)]">{t("referenceLabel")}</dt><dd className="mt-1 font-bold text-[var(--navy)]">{asString(complaint.complaint_number)}</dd></div><div><dt className="text-sm font-bold text-[var(--muted)]">{t("statusLabel")}</dt><dd className="mt-1"><StatusChip label={statusLabel(t, complaint.status)} tone={statusTone(asString(complaint.status))} /></dd></div><div><dt className="text-sm font-bold text-[var(--muted)]">{t("priorityLabel")}</dt><dd className="mt-1 text-sm text-[var(--ink)]">{asString(complaint.priority) || "-"}</dd></div></dl></SurfaceCard><SurfaceCard heading={t("timelineTitle")}><StatusTimeline events={events} label={t("timelineLabel")} /></SurfaceCard><StatePanel title={t("prototypeUpdateTitle")} tone="info">{t("prototypeUpdateCopy")}</StatePanel></div></main>;
}

export function MyComplaints() {
  const t = useTranslations("complaintCompletion");
  const locale = useLocale();
  const router = useRouter();
  const [complaints, setComplaints] = useState<ApiRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [identified, setIdentified] = useState(false);
  const [sessionReady, setSessionReady] = useState(false);

  useEffect(() => {
    setIdentified(getReportMode() === "identified" && Boolean(getAccessToken()));
    setSessionReady(true);
  }, []);

  useEffect(() => {
    let active = true;
    async function load() {
      if (!sessionReady) return;
      if (!identified) {
        if (active) setLoading(false);
        return;
      }
      setLoading(true);
      const result = await complaintsApi.listMine(requestOptions());
      if (!active) return;
      if (result.ok) setComplaints(result.data); else setError(true);
      setLoading(false);
    }
    void load();
    return () => { active = false; };
  }, [identified, sessionReady]);

  if (!sessionReady || loading) return <main className="shell-container py-8 sm:py-12"><StatePanel title={t("myReportsLoadingTitle")} tone="loading">{t("myReportsLoadingCopy")}</StatePanel></main>;
  if (!identified) return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-3xl"><StatePanel action={<Button onClick={() => router.push("/" + locale + "/complaints/track")} variant="outline">{t("trackAction")}</Button>} title={t("anonymousReportsTitle")} tone="info">{t("anonymousReportsCopy")}</StatePanel></div></main>;
  if (error) return <main className="shell-container py-8 sm:py-12"><StatePanel title={t("myReportsErrorTitle")} tone="error">{t("myReportsErrorCopy")}</StatePanel></main>;

  const rows = (items: ApiRecord[]): DataListRow[] => items.map((item) => ({id: asString(item.id), values: {title: asString(item.title), reference: asString(item.complaint_number), status: <StatusChip label={statusLabel(t, item.status)} tone={statusTone(asString(item.status))} />, action: <Button onClick={() => router.push(asString(item.status) === "DRAFT" ? "/" + locale + "/report-crime/" + asString(item.id) + "/incident" : "/" + locale + "/complaints/track/" + encodeURIComponent(asString(item.complaint_number)))} size="sm" variant="outline">{asString(item.status) === "DRAFT" ? t("continueDraft") : t("viewTracking")}</Button>}}));
  const drafts = complaints.filter((item) => asString(item.status) === "DRAFT");
  const submitted = complaints.filter((item) => asString(item.status) !== "DRAFT");
  const columns = [{key: "title", label: t("tableTitle")}, {key: "reference", label: t("tableReference")}, {key: "status", label: t("tableStatus")}, {key: "action", label: t("tableAction")}];
  return <main className="shell-container py-8 sm:py-12"><div className="mx-auto max-w-5xl space-y-8"><p className="eyebrow">{t("myReportsEyebrow")}</p><h1 className="text-3xl font-bold text-[var(--navy)] sm:text-4xl">{t("myReportsTitle")}</h1><section><h2 className="mb-4 text-xl font-bold text-[var(--navy)]">{t("draftsTitle")}</h2><ResponsiveDataList caption={t("draftsTitle")} columns={columns} emptyMessage={t("noDrafts")} rows={rows(drafts)} /></section><section><h2 className="mb-4 text-xl font-bold text-[var(--navy)]">{t("submittedReportsTitle")}</h2><ResponsiveDataList caption={t("submittedReportsTitle")} columns={columns} emptyMessage={t("noSubmitted")} rows={rows(submitted)} /></section></div></main>;
}
