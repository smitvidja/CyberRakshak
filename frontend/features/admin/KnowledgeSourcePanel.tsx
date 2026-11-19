"use client";

import {useCallback, useEffect, useMemo, useRef, useState} from "react";
import {useTranslations} from "next-intl";

import {Button} from "@/components/ui/Button";
import {CheckboxField, SelectField, TextArea, TextInput} from "@/components/ui/FormFields";
import {ResponsiveDataList, type DataListRow} from "@/components/ui/ResponsiveDataList";
import {StatePanel, StatusChip, SurfaceCard} from "@/components/ui/Surface";
import {authApi} from "@/lib/api/auth";
import {
  adminApi,
  type KnowledgeGap,
  type KnowledgeSourceProposal,
  type KnowledgeSourceStatus
} from "@/lib/api/backoffice";

// Codes the backend validates (app/schemas/cyber_saathi.py). Shown as codes, like the
// gap statuses: they must match the authoritative corpus exactly.
const SOURCE_TYPES = [
  "official_public_guidance",
  "official_public_service",
  "official_regulatory_guidance",
  "official_consumer_guidance",
  "official_legal_instrument"
];
const LANGUAGES = ["EN", "HI", "HINGLISH", "MIXED"];
const DOMAINS = [
  "financial_fraud", "upi_payment_fraud", "phishing", "account_compromise", "impersonation",
  "harassment_abuse", "women_child_online_safety", "cyberstalking", "malware_device_compromise",
  "identity_theft", "suspicious_identifiers", "general_cyber_safety", "ecommerce_consumer_grievance"
];
const FILTERS: Array<KnowledgeSourceStatus | "ALL"> = ["PENDING", "APPROVED", "PUBLISHED", "REJECTED", "ALL"];

function toneFor(status: KnowledgeSourceStatus) {
  if (status === "PUBLISHED") return "success" as const;
  if (status === "APPROVED") return "info" as const;
  if (status === "REJECTED") return "neutral" as const;
  return "warning" as const;
}

const emptyForm = {
  domains: [] as string[],
  language: "EN",
  publishedOn: "",
  sectionTitle: "",
  sourceTitle: "",
  sourceType: SOURCE_TYPES[0],
  sourceUrl: "",
  terms: "",
  text: ""
};

type ApiIssue = {field?: string; message?: string};

export function KnowledgeSourcePanel({
  gaps,
  onClosed,
  onGapsChanged,
  proposeFor,
  token
}: {
  gaps: KnowledgeGap[];
  onClosed: () => void;
  onGapsChanged: () => void;
  proposeFor: KnowledgeGap | null;
  token: string;
}) {
  const t = useTranslations("adminKnowledgeGaps.sources");
  const tConsole = useTranslations("adminKnowledgeGaps");
  const [proposals, setProposals] = useState<KnowledgeSourceProposal[]>([]);
  const [filter, setFilter] = useState<KnowledgeSourceStatus | "ALL">("PENDING");
  const [myUserId, setMyUserId] = useState<string | null>(null);
  const [loadError, setLoadError] = useState("");
  const [loading, setLoading] = useState(true);
  const [notice, setNotice] = useState("");

  const [form, setForm] = useState(emptyForm);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [formIssues, setFormIssues] = useState<string[]>([]);

  const [reviewingId, setReviewingId] = useState<string | null>(null);
  const [reviewNote, setReviewNote] = useState("");
  const [reviewing, setReviewing] = useState(false);
  const latestLoad = useRef(0);

  const load = useCallback(async () => {
    const requestId = ++latestLoad.current;
    setLoadError("");
    setLoading(true);
    const result = await adminApi.listKnowledgeSources(filter === "ALL" ? undefined : filter, {accessToken: token});
    if (requestId !== latestLoad.current) return; // a newer filter's response wins
    setLoading(false);
    if (!result.ok) {
      setLoadError(t("loadFailed"));
      return;
    }
    setProposals(result.data);
  }, [filter, t, token]);

  useEffect(() => {
    let cancelled = false;
    void Promise.resolve().then(async () => {
      const me = await authApi.current({accessToken: token});
      if (!cancelled && me.ok) setMyUserId(String((me.data as {id?: unknown}).id ?? ""));
      if (!cancelled) await load();
    });
    return () => { cancelled = true; };
  }, [load, token]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!proposeFor) return;
    setSubmitting(true);
    setFormError("");
    setFormIssues([]);
    const result = await adminApi.proposeKnowledgeSource(
      {
        domains: form.domains,
        gap_id: proposeFor.id,
        language: form.language,
        published_on: form.publishedOn,
        retrieval_terms: form.terms.split(",").map((term) => term.trim()).filter(Boolean),
        section_title: form.sectionTitle,
        source_title: form.sourceTitle,
        source_type: form.sourceType,
        source_url: form.sourceUrl.trim(),
        text: form.text
      },
      {accessToken: token}
    );
    setSubmitting(false);
    if (!result.ok) {
      setFormError(t("proposeFailed"));
      const issues = (result.error.details?.issues as ApiIssue[] | undefined) ?? [];
      setFormIssues(issues.map((issue) => [issue.field, issue.message].filter(Boolean).join(": ")).filter(Boolean));
      return;
    }
    setForm(emptyForm);
    setNotice(t("proposed"));
    setFilter("PENDING");
    onClosed();
    void load();
  }

  const review = useCallback(async (proposal: KnowledgeSourceProposal, decision: "APPROVED" | "REJECTED") => {
    setReviewing(true);
    setNotice("");
    const result = await adminApi.reviewKnowledgeSource(
      proposal.id,
      {decision, review_note: reviewNote.trim() || null},
      {accessToken: token}
    );
    setReviewing(false);
    if (!result.ok) {
      setLoadError(result.error.code === "SECOND_REVIEWER_REQUIRED" ? t("ownProposal") : t("reviewFailed"));
      return;
    }
    setReviewingId(null);
    setReviewNote("");
    setNotice(t("reviewed", {decision}));
    void load();
    onGapsChanged();
  }, [load, onGapsChanged, reviewNote, t, token]);

  const gapQuestion = useCallback(
    (gapId: string | null) => (gapId ? gaps.find((gap) => gap.id === gapId)?.sample_question ?? t("linkedGap") : null),
    [gaps, t]
  );

  const rows = useMemo<DataListRow[]>(() => proposals.map((proposal) => {
    const mine = myUserId !== null && proposal.proposed_by_id === myUserId;
    let action: React.ReactNode = null;
    if (proposal.status === "PENDING" && mine) {
      action = <p className="text-xs text-[var(--muted)]">{t("ownProposal")}</p>;
    } else if (proposal.status === "PENDING" && reviewingId === proposal.id) {
      action = (
        <div className="space-y-2">
          <TextArea
            id={"source-review-note-" + proposal.id}
            label={t("reviewNote")}
            maxLength={2000}
            onChange={(event) => setReviewNote(event.target.value)}
            rows={2}
            value={reviewNote}
          />
          <div className="flex flex-wrap gap-2">
            <Button isLoading={reviewing} onClick={() => void review(proposal, "APPROVED")}>{t("approve")}</Button>
            <Button isLoading={reviewing} onClick={() => void review(proposal, "REJECTED")} variant="outline">{t("reject")}</Button>
          </div>
        </div>
      );
    } else if (proposal.status === "PENDING") {
      action = <Button onClick={() => { setReviewingId(proposal.id); setReviewNote(""); }} variant="outline">{t("approve")} / {t("reject")}</Button>;
    } else if (proposal.status === "APPROVED") {
      action = <p className="text-xs text-[var(--muted)]"><code>{t("publishHint")}</code></p>;
    } else if (proposal.status === "PUBLISHED" && proposal.published_source_id) {
      action = <p className="text-xs text-[var(--muted)]">{t("publishedAs", {sourceId: proposal.published_source_id})}</p>;
    }
    return {
      id: proposal.id,
      values: {
        source: (
          <div className="space-y-1">
            <p className="font-semibold text-[var(--navy)]">{proposal.source_title}</p>
            <a className="break-all text-xs text-[var(--blue)] underline" href={proposal.source_url} rel="noopener noreferrer" target="_blank">{proposal.source_url}</a>
            <p className="text-xs text-[var(--muted)]">{proposal.section_title} · {proposal.domains.join(", ")} · {proposal.language}</p>
            <p className="text-xs text-[var(--muted)]">{t("proposedOn", {date: new Date(proposal.created_at).toLocaleDateString()})}</p>
          </div>
        ),
        gap: <p className="text-sm">{gapQuestion(proposal.gap_id) ?? t("noGap")}</p>,
        status: (
          <div className="space-y-2">
            <StatusChip label={proposal.status} tone={toneFor(proposal.status)} />
            {proposal.review_note ? <p className="text-xs text-[var(--muted)]">{proposal.review_note}</p> : null}
          </div>
        ),
        action
      }
    };
  }), [gapQuestion, myUserId, proposals, review, reviewNote, reviewing, reviewingId, t]);

  return (
    <section aria-labelledby="knowledge-sources-heading" className="mt-10">
      <h2 className="text-2xl font-bold text-[var(--navy)]" id="knowledge-sources-heading">{t("heading")}</h2>
      <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--muted)]">{t("intro")}</p>

      {proposeFor ? (
        <SurfaceCard className="mt-5" heading={t("formHeading")}>
          <p className="text-sm font-semibold text-[var(--navy)]">{t("formFor", {question: proposeFor.sample_question})}</p>
          <p className="mt-1 text-sm leading-6 text-[var(--muted)]">{t("formIntro")}</p>
          <form className="mt-5 space-y-5" onSubmit={submit}>
            <div className="grid gap-5 sm:grid-cols-2">
              <TextInput id="source-title" label={t("sourceTitle")} maxLength={300} minLength={3} onChange={(e) => setForm((f) => ({...f, sourceTitle: e.target.value}))} required value={form.sourceTitle} />
              <TextInput id="source-url" label={t("sourceUrl")} maxLength={1000} onChange={(e) => setForm((f) => ({...f, sourceUrl: e.target.value}))} placeholder="https://www.cert-in.org.in/..." required type="url" value={form.sourceUrl} />
              <SelectField id="source-type" label={t("sourceType")} onChange={(e) => setForm((f) => ({...f, sourceType: e.target.value}))} options={SOURCE_TYPES.map((value) => ({label: value, value}))} value={form.sourceType} />
              <SelectField id="source-language" label={t("language")} onChange={(e) => setForm((f) => ({...f, language: e.target.value}))} options={LANGUAGES.map((value) => ({label: value, value}))} value={form.language} />
              <TextInput id="source-published-on" label={t("publishedOn")} onChange={(e) => setForm((f) => ({...f, publishedOn: e.target.value}))} required type="date" value={form.publishedOn} />
              <TextInput id="source-section-title" label={t("sectionTitle")} maxLength={300} minLength={3} onChange={(e) => setForm((f) => ({...f, sectionTitle: e.target.value}))} required value={form.sectionTitle} />
            </div>
            <fieldset className="rounded-[7px] border border-[var(--border)] px-4 pb-4 pt-2">
              <legend className="px-1 text-sm font-bold">{t("domains")}</legend>
              <div className="grid gap-2 sm:grid-cols-3">
                {DOMAINS.map((domain) => (
                  <CheckboxField
                    checked={form.domains.includes(domain)}
                    disabled={!form.domains.includes(domain) && form.domains.length >= 6}
                    id={"source-domain-" + domain}
                    key={domain}
                    label={domain}
                    onCheckedChange={(e) => setForm((f) => ({...f, domains: e.target.checked ? [...f.domains, domain] : f.domains.filter((d) => d !== domain)}))}
                  />
                ))}
              </div>
            </fieldset>
            <TextArea description={t("textHelp")} id="source-text" label={t("text")} maxLength={5000} minLength={40} onChange={(e) => setForm((f) => ({...f, text: e.target.value}))} required rows={6} value={form.text} />
            <TextInput id="source-terms" label={t("terms")} onChange={(e) => setForm((f) => ({...f, terms: e.target.value}))} value={form.terms} />
            {formError ? (
              <div className="text-sm font-bold text-[var(--danger)]" role="alert">
                <p>{formError}</p>
                {formIssues.length ? <ul className="mt-1 list-disc pl-5 font-medium">{formIssues.map((issue) => <li key={issue}>{issue}</li>)}</ul> : null}
              </div>
            ) : null}
            <div className="flex flex-wrap gap-2">
              <Button disabled={form.domains.length === 0} isLoading={submitting} type="submit">{t("submit")}</Button>
              <Button onClick={() => { setForm(emptyForm); setFormError(""); setFormIssues([]); onClosed(); }} type="button" variant="outline">{tConsole("cancel")}</Button>
            </div>
          </form>
        </SurfaceCard>
      ) : null}

      {notice ? <div className="mt-5"><StatePanel title={t("heading")} tone="success">{notice}</StatePanel></div> : null}
      {loadError ? <p className="mt-4 text-sm font-bold text-[var(--danger)]" role="alert">{loadError}</p> : null}

      <div className="mt-5 max-w-xs">
        <SelectField
          id="source-status-filter"
          label={t("filterLabel")}
          onChange={(event) => setFilter(event.target.value as KnowledgeSourceStatus | "ALL")}
          options={FILTERS.map((value) => ({label: value === "ALL" ? t("statusAll") : value, value}))}
          value={filter}
        />
      </div>
      <div className="mt-4">
        <ResponsiveDataList
          caption={t("heading")}
          columns={[
            {key: "source", label: t("columnSource")},
            {key: "gap", label: t("columnGap")},
            {key: "status", label: t("columnStatus")},
            {key: "action", label: t("columnAction")}
          ]}
          // "Loading" while a request is in flight, so an admin never reads "no proposals"
          // for a list that simply has not arrived yet.
          emptyMessage={loading ? tConsole("loading") : t("empty")}
          rows={rows}
        />
      </div>
    </section>
  );
}
