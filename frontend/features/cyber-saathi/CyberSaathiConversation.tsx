"use client";

import Link from "next/link";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {AlertTriangle, ArrowRight, Bot, Check, ExternalLink, FileText, Languages, LoaderCircle, LockKeyhole, Mic, Paperclip, RefreshCw, Send, ShieldCheck, UserRound} from "lucide-react";
import {useEffect, useLayoutEffect, useRef, useState, type FormEvent} from "react";

import {cyberSaathiApi} from "@/lib/api/cyber-saathi";
import {prepareCyberSaathiReportHandoff} from "@/lib/cyber-saathi/report-handoff";
import {setReportCategoryHint, setReportMode} from "@/lib/auth/citizen-session";
import type {ConversationState, ReportingMode, SaathiLanguage} from "@/types/cyber-saathi";

// v2 adds explicit storage consent and server-backed recovery; keep v1 untouched
// instead of silently treating an older browser-only payload as consented data.
const STORAGE_KEY = "cyberrakshak.cyber-saathi.conversation.v2";
function AssistantTurnContent({content}: {content: string}) {
  const lines = content.split("\n");
  const firstStep = lines.findIndex((line) => /^\s*\d+[.)]\s+/.test(line));
  if (firstStep < 0) return <p className="whitespace-pre-wrap break-words">{content}</p>;

  const intro = lines.slice(0, firstStep).filter(Boolean);
  const steps: string[] = [];
  let cursor = firstStep;
  while (cursor < lines.length && /^\s*\d+[.)]\s+/.test(lines[cursor])) {
    steps.push(lines[cursor].replace(/^\s*\d+[.)]\s+/, ""));
    cursor += 1;
  }
  const outro = lines.slice(cursor).filter(Boolean);
  return <div className="break-words">{intro.map((line, index) => <p className="mb-2" key={`intro-${index}`}>{line}</p>)}<ol className="list-decimal space-y-2 pl-5 marker:font-bold marker:text-[#0b58c7]">{steps.map((step, index) => <li key={`step-${index}`}>{step}</li>)}</ol>{outro.map((line, index) => <p className="mt-2" key={`outro-${index}`}>{line}</p>)}</div>;
}

export function CyberSaathiConversation() {
  const t = useTranslations("cyberSaathi");
  const locale = useLocale();
  const router = useRouter();
  const [state, setState] = useState<ConversationState | null>(null);
  const [language, setLanguage] = useState<SaathiLanguage>(locale === "hi" ? "HI" : "EN");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voiceNotice, setVoiceNotice] = useState(false);
  const [attachmentFiles, setAttachmentFiles] = useState<File[]>([]);
  const [attachmentError, setAttachmentError] = useState("");
  const [attaching, setAttaching] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const attachmentInputRef = useRef<HTMLInputElement>(null);
  const initializedRef = useRef(false);

  useLayoutEffect(() => {
    const input = inputRef.current;
    if (!input) return;
    input.style.height = "0px";
    input.style.height = `${Math.min(input.scrollHeight, 240)}px`;
    input.style.overflowY = input.scrollHeight > 240 ? "auto" : "hidden";
  }, [message]);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as ConversationState;
        if (parsed.id && Array.isArray(parsed.turns)) {
          // Browser-only persisted conversation state must hydrate after mount.
          if (parsed.storage_consent) {
            void cyberSaathiApi.resume(parsed.id).then((result) => {
              setState(result.ok ? result.data.state : parsed);
              setLanguage((result.ok ? result.data.state : parsed).language);
              setLoading(false);
            });
          } else {
            queueMicrotask(() => {
              setState(parsed);
              setLanguage(parsed.language);
              setLoading(false);
            });
          }
          return;
        }
      } catch {
        window.localStorage.removeItem(STORAGE_KEY);
      }
    }
    void startConversation(locale === "hi" ? "HI" : "EN");
  // The initial locale is intentionally read once; users switch language inside the conversation.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (state) window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    endRef.current?.scrollIntoView({behavior: "smooth", block: "nearest"});
  }, [state, sending]);

  async function startConversation(nextLanguage: SaathiLanguage) {
    setLoading(true);
    setError(null);
    const result = await cyberSaathiApi.start(nextLanguage);
    if (result.ok) {
      setState(result.data.state);
      setLanguage(nextLanguage);
    } else {
      setError(t("errors.start"));
    }
    setLoading(false);
  }

  async function sendMessage(text: string, reportingMode?: ReportingMode, prepareReportDraft = false) {
    const trimmed = text.trim();
    if (!state || !trimmed || sending) return;
    setSending(true);
    setError(null);
    const requestState = prepareReportDraft ? {...state, storage_consent: true} : state;
    const result = await cyberSaathiApi.send(requestState, trimmed, reportingMode, prepareReportDraft);
    if (result.ok) {
      setState(result.data.state);
      setLanguage(result.data.state.language);
      setMessage("");
    } else {
      setError(t("errors.send"));
    }
    setSending(false);
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(message);
  }

  function changeLanguage(nextLanguage: SaathiLanguage) {
    setLanguage(nextLanguage);
    if (state) {
      const next = {...state, language: nextLanguage};
      setState(next);
    }
  }

  function resetConversation() {
    window.localStorage.removeItem(STORAGE_KEY);
    setState(null);
    setVoiceNotice(false);
    setAttachmentFiles([]);
    setAttachmentError("");
    void startConversation(language);
  }

  async function analyzeAttachment(file: File) {
    if (!state || attaching) return;
    if (!["application/pdf", "image/png", "image/jpeg"].includes(file.type)) {
      setAttachmentError(t("attachmentTypeError"));
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setAttachmentError(t("attachmentSizeError"));
      return;
    }
    setAttaching(true);
    setAttachmentError("");
    const result = await cyberSaathiApi.analyzeAttachment(state, file);
    if (result.ok) {
      setState(result.data.state);
      setAttachmentFiles((current) => current.some((item) => item.name === file.name && item.size === file.size) ? current : [...current, file]);
    } else {
      setAttachmentError(t("attachmentAnalyzeError"));
    }
    setAttaching(false);
    if (attachmentInputRef.current) attachmentInputRef.current.value = "";
  }

  const pendingEntities = state?.incident.entities.filter((entity) =>
    state.pending_confirmation_entity_ids.includes(entity.id)
  ) ?? [];
  const handoff = state?.handoff;
  const incidentCount = state?.incidents?.length ?? 0;
  const queuedCount = state?.incidents?.filter((item) => item.queue_status === "queued").length ?? 0;
  const activeRecord = state?.incidents?.find((item) => item.id === state.active_incident_id);
  const reportPreparation = activeRecord?.report_preparation;
  const reportChecklistGroups = reportPreparation ? [
    {key: "collected", label: t("packetCollected"), items: reportPreparation.checklist.filter((item) => item.status === "collected")},
    {key: "confirm", label: t("packetNeedConfirmation"), items: reportPreparation.checklist.filter((item) => item.status === "missing")},
    {key: "optional", label: t("packetOptional"), items: reportPreparation.checklist.filter((item) => item.status === "optional" || item.status === "not_available")}
  ].filter((group) => group.items.length > 0) : [];
  const showReportPreparation = Boolean(
    reportPreparation
    && reportPreparation.packet_ready
  );
  const anonymousAllowed = ["child_safety", "women_child_online_safety"].includes(
    state?.incident.crime_domain ?? ""
  );
  const canHandoff = Boolean(
    handoff
    && reportPreparation?.draft_prepared
    && !state?.pending_confirmation_entity_ids.length
  );
  const categoryByDomain: Record<string, string> = {
    financial_fraud: "financial",
    ecommerce_fraud: "commerce",
    phishing_scam: "identity",
    account_compromise: "identity",
    identity_theft: "identity",
    impersonation: "identity",
    malware: "other",
    online_harassment: "harassment",
    cyberstalking: "harassment",
    child_safety: "women-child",
    women_child_online_safety: "women-child"
  };
  const categoryHint = handoff ? categoryByDomain[handoff.prefill.crime_domain] ?? "other" : "other";
  const handoffPath = handoff?.target === "report_crime"
    ? `/${locale}${handoff.route}?mode=${handoff.reporting_mode === "undecided" ? "identified" : handoff.reporting_mode}&category=${categoryHint}`
    : handoff ? `/${locale}${handoff.route}` : `/${locale}/report-crime`;

  function openReportWorkflow(nextState: ConversationState, nextHandoff: NonNullable<ConversationState["handoff"]>) {
    prepareCyberSaathiReportHandoff({
      conversationId: nextState.id,
      files: attachmentFiles,
      prefill: nextHandoff.prefill
    });
    const mode = nextHandoff.reporting_mode === "anonymous" ? "anonymous" : "identified";
    setReportMode(mode);
    setReportCategoryHint(categoryByDomain[nextHandoff.prefill.crime_domain] ?? "other");
    router.push(`/${locale}/report-crime/new/incident`);
  }

  function continueToReport() {
    if (!state || !handoff || handoff.target !== "report_crime") return;
    openReportWorkflow(state, handoff);
  }

  return (
    <main className="bg-[#f5f8fc] pb-8">
      <div className="shell-container grid gap-5 pb-7 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="overflow-hidden rounded-[8px] border border-[#d7e2ef] bg-white shadow-[0_5px_20px_rgb(15_42_74_/_0.08)]" aria-labelledby="saathi-title">
          <header className="flex flex-col gap-4 border-b border-[#dbe5f0] bg-[#f8fbff] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <span aria-hidden="true" className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#0b58c7] text-white"><Bot size={23} /></span>
              <div className="min-w-0"><div className="flex items-center gap-2"><h1 id="saathi-title" className="text-xl font-bold text-[#08245c]">{t("title")}</h1><span className="rounded-full bg-[#e2f5e8] px-2 py-0.5 text-[11px] font-bold text-[#15803d]">{t("available")}</span></div><p className="mt-0.5 text-sm text-slate-600">{t("subtitle")}</p>{incidentCount ? <p className="mt-1 text-[11px] font-semibold text-[#315274]">{t("incidentCount", {count: incidentCount})}{queuedCount ? ` · ${t("queuedCount", {count: queuedCount})}` : ""}</p> : null}</div>
            </div>
            <div className="flex items-center gap-2">
              <label className="sr-only" htmlFor="saathi-language">{t("languageLabel")}</label>
              <span className="relative"><Languages aria-hidden="true" className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-[#0b58c7]" size={16} /><select className="h-9 rounded-[6px] border border-[#b9cbe0] bg-white pl-8 pr-7 text-xs font-bold text-[#08245c]" id="saathi-language" onChange={(event) => changeLanguage(event.target.value as SaathiLanguage)} value={language}><option value="EN">English</option><option value="HI">हिन्दी</option><option value="HINGLISH">Hinglish</option></select></span>
              <button aria-label={t("newConversation")} className="grid h-9 w-9 place-items-center rounded-[6px] border border-[#b9cbe0] text-[#0b58c7] hover:bg-blue-50" onClick={resetConversation} title={t("newConversation")} type="button"><RefreshCw size={16} /></button>
            </div>
          </header>

          <div aria-live="polite" className="h-[460px] overflow-y-auto bg-[#fafdff] px-4 py-5 sm:px-6">
            {loading ? <div className="grid h-full place-items-center text-sm text-slate-600"><span className="flex items-center gap-2"><LoaderCircle className="animate-spin" size={18} />{t("loading")}</span></div> : null}
            {!loading && state?.turns.map((turn) => (
              <article className={`mb-4 flex gap-2.5 ${turn.role === "user" ? "justify-end" : "justify-start"}`} key={turn.id}>
                {turn.role === "assistant" ? <span aria-hidden="true" className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#e5efff] text-[#0b58c7]"><Bot size={17} /></span> : null}
                <div className={`max-w-[86%] rounded-[8px] px-4 py-3 text-sm leading-6 sm:max-w-[76%] ${turn.role === "user" ? "bg-[#0b4fb3] text-white" : turn.kind === "safety" ? "border border-[#f2c46d] bg-[#fff8e8] text-[#563b05]" : "border border-[#dce6f1] bg-white text-slate-700"}`}>
                  {turn.kind === "safety" ? <strong className="mb-1 flex items-center gap-2 text-[#8a5400]"><AlertTriangle size={16} />{t("urgentTitle")}</strong> : null}
                  {turn.role === "assistant" ? <AssistantTurnContent content={turn.content} /> : <p className="whitespace-pre-wrap break-words">{turn.content}</p>}
                  {!turn.llm_provider && turn.kind === "safety" ? <p className="mt-2 text-[10px] font-bold uppercase tracking-wide text-[#7a5205]">{t("deterministicSafety")}</p> : null}
                  {turn.sources?.length ? (
                    <details className={`mt-3 border-t pt-3 ${turn.kind === "safety" ? "border-[#ead49e]" : "border-[#dce6f1]"}`}>
                      <summary className="cursor-pointer text-[11px] font-bold uppercase tracking-wide text-[#315274]">{t("sourcesLabel")}</summary>
                      <ul className="mt-2 space-y-2">
                        {(turn.sources ?? []).map((source) => (
                          <li className="rounded-[6px] border border-[#c9d8e8] bg-[#f8fbff] px-3 py-2" key={source.chunk_id}>
                            <p className="text-xs font-bold leading-5 text-[#08245c]">{source.source_title}</p>
                            <p className="text-[11px] leading-4 text-slate-600">{source.section_title} · {source.version}</p>
                            <a aria-label={`${t("learnMore")}: ${source.source_title}`} className="mt-1 inline-flex items-center gap-1 text-xs font-bold text-[#0b58c7] underline-offset-2 hover:underline focus-visible:rounded focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[#0b58c7]" href={source.source_url} rel="noreferrer noopener" target="_blank">{t("learnMore")}<ExternalLink aria-hidden="true" size={12} /></a>
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </div>
                {turn.role === "user" ? <span aria-hidden="true" className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#dfe9f7] text-[#173c71]"><UserRound size={16} /></span> : null}
              </article>
            ))}
            {showReportPreparation && reportPreparation ? (
              <section className="mb-4 ml-10 max-w-2xl rounded-[8px] border border-[#b8cceb] bg-white p-4" aria-labelledby="saathi-report-packet">
                <div className="flex items-center gap-2 text-[#08245c]"><FileText size={17} /><h3 className="text-sm font-bold" id="saathi-report-packet">{t("reportPacketTitle")}</h3></div>
                <p className="mt-1 text-xs leading-5 text-slate-600">{t("reportPacketCopy")}</p>
                <div className="mt-3 space-y-3">
                  {reportChecklistGroups.map((group) => (
                    <section key={group.key}>
                      <h4 className="mb-1 text-[11px] font-bold uppercase tracking-wide text-[#315274]">{group.label}</h4>
                      <ol className="list-decimal divide-y divide-slate-200 rounded-[6px] border border-slate-200 pl-8 marker:font-bold marker:text-[#0b58c7]">
                        {group.items.map((item) => (
                          <li className="px-2 py-2 text-xs" key={item.key}>
                            <strong className="text-slate-700">{item.label}</strong>{item.value_preview ? <span className="mt-0.5 block break-words text-slate-500">{item.value_preview}</span> : null}
                          </li>
                        ))}
                      </ol>
                    </section>
                  ))}
                </div>
                {reportPreparation.attachments.length ? <ul className="mt-3 space-y-1 text-xs text-slate-600">{reportPreparation.attachments.map((item) => <li className="flex items-center gap-2" key={item.id}><Paperclip size={12} />{item.file_name} · {item.media_summary}</li>)}</ul> : null}
                <p className="mt-3 text-[11px] leading-4 text-slate-500">{t("attachmentRuntimeNote")}</p>
                {reportPreparation.draft_prepared ? (
                  canHandoff && handoff?.target === "report_crime" ? <button className="mt-4 flex min-h-10 w-full items-center justify-between rounded-[6px] bg-[#0b4fb3] px-4 py-2 text-sm font-bold text-white" onClick={continueToReport} type="button">{t("reviewEditReport")}<ArrowRight size={17} /></button> : null
                ) : (
                  <div className="mt-4 grid gap-2 sm:grid-cols-3">
                    <button className="min-h-10 rounded-[6px] border border-[#b9cbe0] px-3 text-xs font-bold text-[#0b4fb3]" onClick={() => inputRef.current?.focus()} type="button">{t("addAnotherDetail")}</button>
                    <button className="min-h-10 rounded-[6px] border border-[#b9cbe0] px-3 text-xs font-bold text-[#0b4fb3] disabled:opacity-50" disabled={attaching} onClick={() => attachmentInputRef.current?.click()} type="button">{t("uploadEvidenceAction")}</button>
                    <button className="min-h-10 rounded-[6px] bg-[#0b4fb3] px-3 text-xs font-bold text-white disabled:opacity-50" disabled={sending || pendingEntities.length > 0} onClick={() => void sendMessage(t("prepareReportMessage"), undefined, true)} type="button">{t("prepareReportDraft")}</button>
                  </div>
                )}
              </section>
            ) : null}
            {pendingEntities.length ? (
              <section className="mb-4 ml-10 max-w-xl rounded-[8px] border border-[#b8cceb] bg-white p-4" aria-label={t("confirmationTitle")}>
                <p className="text-xs font-bold uppercase text-[#315274]">{t("confirmationTitle")}</p>
                <ol className="mt-2 list-decimal space-y-1 pl-5 text-base font-bold text-[#08245c]">
                  {pendingEntities.map((entity) => {
                    const value = entity.normalized_value && !Number.isNaN(Number(entity.normalized_value))
                      ? new Intl.NumberFormat(locale === "hi" ? "hi-IN" : "en-IN").format(Number(entity.normalized_value))
                      : entity.value;
                    return <li className="break-words" key={entity.id}>{entity.type === "amount" ? `₹${value}` : value}</li>;
                  })}
                </ol>
                <div className="mt-3 flex flex-wrap gap-2"><button className="inline-flex h-9 items-center gap-2 rounded-[6px] bg-[#12833b] px-4 text-sm font-bold text-white" onClick={() => void sendMessage(language === "HI" ? "हाँ" : language === "HINGLISH" ? "haan" : "yes")} type="button"><Check size={16} />{t("confirm")}</button><button className="h-9 rounded-[6px] border border-[#b9cbe0] px-4 text-sm font-bold text-[#0b4fb3]" onClick={() => inputRef.current?.focus()} type="button">{t("changeValue")}</button></div>
              </section>
            ) : null}
            {sending ? <div className="mb-4 ml-10 flex items-center gap-2 text-sm text-slate-500"><LoaderCircle className="animate-spin" size={16} />{t("thinking")}</div> : null}
            <div ref={endRef} />
          </div>

          {error ? <div className="mx-4 mt-3 flex items-center justify-between gap-3 rounded-[6px] border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-800"><span>{error}</span><button className="font-bold underline" onClick={() => state ? void sendMessage(message || t("retryMessage")) : void startConversation(language)} type="button">{t("retry")}</button></div> : null}
          {voiceNotice ? <div className="mx-4 mt-3 rounded-[6px] border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-[#174574]">{t("voiceUnavailable")}</div> : null}

          <form className="border-t border-[#dbe5f0] bg-white p-4" onSubmit={submit}>
            <label className="sr-only" htmlFor="saathi-message">{t("inputLabel")}</label>
            <div className="flex items-end gap-2 rounded-[8px] border border-[#aebfd3] bg-white p-2 focus-within:border-[#0b58c7] focus-within:ring-2 focus-within:ring-blue-100">
              <input accept=".pdf,.png,.jpg,.jpeg" className="sr-only" disabled={loading || sending || attaching} onChange={(event) => { const file = event.target.files?.[0]; if (file) void analyzeAttachment(file); }} ref={attachmentInputRef} type="file" />
              <textarea className="min-h-11 max-h-60 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-500" disabled={loading || sending} id="saathi-message" maxLength={4000} onChange={(event) => setMessage(event.target.value)} placeholder={t("placeholder")} ref={inputRef} rows={1} value={message} />
              <button aria-label={t("attachEvidence")} className="grid h-10 w-10 shrink-0 place-items-center rounded-[6px] border border-[#c6d4e4] text-[#0b58c7] hover:bg-blue-50 disabled:opacity-50" disabled={loading || sending || attaching || !state?.incident.summary} onClick={() => attachmentInputRef.current?.click()} title={t("attachEvidence")} type="button">{attaching ? <LoaderCircle className="animate-spin" size={18} /> : <Paperclip size={18} />}</button>
              <button aria-label={t("voiceButton")} className="grid h-10 w-10 shrink-0 place-items-center rounded-[6px] border border-[#c6d4e4] text-[#0b58c7] hover:bg-blue-50" onClick={() => setVoiceNotice(true)} title={t("voiceButton")} type="button"><Mic size={18} /></button>
              <button aria-label={t("send")} className="grid h-10 w-10 shrink-0 place-items-center rounded-[6px] bg-[#0b4fb3] text-white disabled:cursor-not-allowed disabled:opacity-50" disabled={!message.trim() || loading || sending} title={t("send")} type="submit"><Send size={18} /></button>
            </div>
            {attachmentError ? <p className="mt-2 text-xs font-semibold text-red-700" role="alert">{attachmentError}</p> : null}
            <div className="mt-2 flex items-center justify-between gap-3 text-[11px] text-slate-500"><span className="flex items-center gap-1"><LockKeyhole size={12} />{t("privacyNote")}</span><span>{message.length}/4000</span></div>
            <label className="mt-3 flex items-start gap-2 text-xs leading-5 text-slate-600">
              <input checked={state?.storage_consent ?? false} className="mt-1" disabled={!state} onChange={(event) => setState((current) => current ? {...current, storage_consent: event.target.checked} : current)} type="checkbox" />
              <span>{t("storageConsent")}</span>
            </label>
          </form>
        </section>

        <aside className="space-y-4">
          <section className="rounded-[8px] border border-[#d7e2ef] bg-white p-5" aria-labelledby="saathi-next-step">
            <div className="flex items-center gap-2 text-[#08245c]"><ShieldCheck size={20} /><h2 className="font-bold" id="saathi-next-step">{t("safeNextStepTitle")}</h2></div>
            <p className="mt-3 text-sm leading-6 text-slate-600">{t("safeNextStepCopy")}</p>
            {reportPreparation?.packet_ready ? (
              <div className="mt-4 border-t border-slate-200 pt-4">
                <p className="text-xs font-bold text-[#315274]">{t("reportingModeTitle")}</p>
                <div className="mt-2 grid grid-cols-2 gap-2"><button className={`rounded-[6px] border px-2 py-2 text-xs font-bold ${state?.reporting_mode === "anonymous" ? "border-[#0b58c7] bg-blue-50 text-[#0b58c7]" : "border-slate-200 text-slate-600 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"}`} disabled={!anonymousAllowed} onClick={() => void sendMessage(t("modeAnonymousMessage"), "anonymous")} title={!anonymousAllowed ? t("anonymousUnavailable") : undefined} type="button">{t("anonymous")}</button><button className={`rounded-[6px] border px-2 py-2 text-xs font-bold ${state?.reporting_mode === "identified" ? "border-[#0b58c7] bg-blue-50 text-[#0b58c7]" : "border-slate-200 text-slate-600"}`} onClick={() => void sendMessage(t("modeIdentifiedMessage"), "identified")} type="button">{t("identified")}</button></div>
                {!anonymousAllowed ? <p className="mt-2 text-[11px] leading-4 text-slate-500">{t("anonymousUnavailable")}</p> : null}
              </div>
            ) : null}
            {canHandoff && handoff ? handoff.target === "report_crime" ? <button className="mt-4 flex min-h-10 w-full items-center justify-between rounded-[6px] bg-[#0b4fb3] px-4 py-2 text-sm font-bold text-white" onClick={continueToReport} type="button">{t("reviewEditReport")}<ArrowRight size={17} /></button> : <Link className="mt-4 flex min-h-10 items-center justify-between rounded-[6px] bg-[#0b4fb3] px-4 py-2 text-sm font-bold text-white" href={handoffPath}>{t("trackAction")}<ArrowRight size={17} /></Link> : <p className="mt-4 rounded-[6px] bg-[#edf4ff] px-3 py-2.5 text-xs leading-5 text-[#174574]">{pendingEntities.length ? t("confirmBeforeHandoff") : reportPreparation?.packet_ready && !reportPreparation?.draft_prepared ? t("prepareDraftPrompt") : handoff?.target === "report_crime" && !reportPreparation?.ready_for_review ? t("completePacketBeforeHandoff") : handoff?.target === "report_crime" ? t("chooseModeBeforeHandoff") : t("describePrompt")}</p>}
          </section>
          <section className="rounded-[8px] border border-[#d7e2ef] bg-white p-5">
            <h2 className="font-bold text-[#08245c]">{t("boundariesTitle")}</h2>
            <ul className="mt-3 space-y-3 text-sm leading-5 text-slate-600"><li className="flex gap-2"><Check className="mt-0.5 shrink-0 text-[#12833b]" size={15} />{t("boundaryOne")}</li><li className="flex gap-2"><Check className="mt-0.5 shrink-0 text-[#12833b]" size={15} />{t("boundaryTwo")}</li><li className="flex gap-2"><Check className="mt-0.5 shrink-0 text-[#12833b]" size={15} />{t("boundaryThree")}</li></ul>
          </section>
          <a className="flex min-h-11 items-center justify-center rounded-[6px] border border-[#0b58c7] bg-white px-4 text-sm font-bold text-[#0b58c7]" href="tel:1930">{t("helplineAction")}</a>
        </aside>
      </div>
    </main>
  );
}
