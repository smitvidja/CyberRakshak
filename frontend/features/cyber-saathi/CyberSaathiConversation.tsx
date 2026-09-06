"use client";

import Link from "next/link";
import {useLocale, useTranslations} from "next-intl";
import {AlertTriangle, ArrowRight, Bot, Check, Languages, LoaderCircle, LockKeyhole, Mic, RefreshCw, Send, ShieldCheck, UserRound} from "lucide-react";
import {useEffect, useRef, useState, type FormEvent} from "react";

import {cyberSaathiApi} from "@/lib/api/cyber-saathi";
import type {ConversationState, ReportingMode, SaathiLanguage} from "@/types/cyber-saathi";

const STORAGE_KEY = "cyberrakshak.cyber-saathi.conversation.v1";

export function CyberSaathiConversation() {
  const t = useTranslations("cyberSaathi");
  const locale = useLocale();
  const [state, setState] = useState<ConversationState | null>(null);
  const [language, setLanguage] = useState<SaathiLanguage>(locale === "hi" ? "HI" : "EN");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [voiceNotice, setVoiceNotice] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const initializedRef = useRef(false);

  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as ConversationState;
        if (parsed.id && Array.isArray(parsed.turns)) {
          setState(parsed);
          setLanguage(parsed.language);
          setLoading(false);
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

  async function sendMessage(text: string, reportingMode?: ReportingMode) {
    const trimmed = text.trim();
    if (!state || !trimmed || sending) return;
    setSending(true);
    setError(null);
    const result = await cyberSaathiApi.send(state, trimmed, reportingMode);
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
    void startConversation(language);
  }

  const pendingEntity = state?.incident.entities.find((entity) =>
    state.pending_confirmation_entity_ids.includes(entity.id)
  );
  const pendingValue = pendingEntity?.normalized_value && !Number.isNaN(Number(pendingEntity.normalized_value))
    ? new Intl.NumberFormat(locale === "hi" ? "hi-IN" : "en-IN").format(Number(pendingEntity.normalized_value))
    : pendingEntity?.value;
  const handoff = state?.handoff;
  const anonymousAllowed = state?.incident.crime_domain === "child_safety";
  const canHandoff = Boolean(
    handoff
    && !state?.pending_confirmation_entity_ids.length
    && (handoff.target !== "report_crime" || state?.reporting_mode !== "undecided")
  );
  const handoffPath = handoff?.target === "report_crime"
    ? `/${locale}${handoff.route}?mode=${handoff.reporting_mode === "undecided" ? "identified" : handoff.reporting_mode}${handoff.prefill.crime_domain === "financial_fraud" ? "&category=financial" : ""}`
    : handoff ? `/${locale}${handoff.route}` : `/${locale}/report-crime`;

  return (
    <main className="bg-[#f5f8fc] pb-8">
      <div className="shell-container grid gap-5 pb-7 lg:grid-cols-[minmax(0,1fr)_300px]">
        <section className="overflow-hidden rounded-[8px] border border-[#d7e2ef] bg-white shadow-[0_5px_20px_rgb(15_42_74_/_0.08)]" aria-labelledby="saathi-title">
          <header className="flex flex-col gap-4 border-b border-[#dbe5f0] bg-[#f8fbff] px-5 py-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-3">
              <span aria-hidden="true" className="grid h-11 w-11 shrink-0 place-items-center rounded-full bg-[#0b58c7] text-white"><Bot size={23} /></span>
              <div className="min-w-0"><div className="flex items-center gap-2"><h1 id="saathi-title" className="text-xl font-bold text-[#08245c]">{t("title")}</h1><span className="rounded-full bg-[#e2f5e8] px-2 py-0.5 text-[11px] font-bold text-[#15803d]">{t("available")}</span></div><p className="mt-0.5 text-sm text-slate-600">{t("subtitle")}</p></div>
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
                  <p className="whitespace-pre-wrap break-words">{turn.content}</p>
                </div>
                {turn.role === "user" ? <span aria-hidden="true" className="mt-1 grid h-8 w-8 shrink-0 place-items-center rounded-full bg-[#dfe9f7] text-[#173c71]"><UserRound size={16} /></span> : null}
              </article>
            ))}
            {pendingEntity ? (
              <section className="mb-4 ml-10 max-w-xl rounded-[8px] border border-[#b8cceb] bg-white p-4" aria-label={t("confirmationTitle")}>
                <p className="text-xs font-bold uppercase text-[#315274]">{t("confirmationTitle")}</p>
                <p className="mt-1 text-lg font-bold text-[#08245c]">₹{pendingValue}</p>
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
              <textarea className="max-h-32 min-h-11 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm text-slate-800 outline-none placeholder:text-slate-500" disabled={loading || sending} id="saathi-message" maxLength={4000} onChange={(event) => setMessage(event.target.value)} placeholder={t("placeholder")} ref={inputRef} rows={1} value={message} />
              <button aria-label={t("voiceButton")} className="grid h-10 w-10 shrink-0 place-items-center rounded-[6px] border border-[#c6d4e4] text-[#0b58c7] hover:bg-blue-50" onClick={() => setVoiceNotice(true)} title={t("voiceButton")} type="button"><Mic size={18} /></button>
              <button aria-label={t("send")} className="grid h-10 w-10 shrink-0 place-items-center rounded-[6px] bg-[#0b4fb3] text-white disabled:cursor-not-allowed disabled:opacity-50" disabled={!message.trim() || loading || sending} title={t("send")} type="submit"><Send size={18} /></button>
            </div>
            <div className="mt-2 flex items-center justify-between gap-3 text-[11px] text-slate-500"><span className="flex items-center gap-1"><LockKeyhole size={12} />{t("privacyNote")}</span><span>{message.length}/4000</span></div>
          </form>
        </section>

        <aside className="space-y-4">
          <section className="rounded-[8px] border border-[#d7e2ef] bg-white p-5" aria-labelledby="saathi-next-step">
            <div className="flex items-center gap-2 text-[#08245c]"><ShieldCheck size={20} /><h2 className="font-bold" id="saathi-next-step">{t("safeNextStepTitle")}</h2></div>
            <p className="mt-3 text-sm leading-6 text-slate-600">{t("safeNextStepCopy")}</p>
            {handoff?.target === "report_crime" ? (
              <div className="mt-4 border-t border-slate-200 pt-4">
                <p className="text-xs font-bold text-[#315274]">{t("reportingModeTitle")}</p>
                <div className="mt-2 grid grid-cols-2 gap-2"><button className={`rounded-[6px] border px-2 py-2 text-xs font-bold ${state?.reporting_mode === "anonymous" ? "border-[#0b58c7] bg-blue-50 text-[#0b58c7]" : "border-slate-200 text-slate-600 disabled:cursor-not-allowed disabled:bg-slate-100 disabled:text-slate-400"}`} disabled={!anonymousAllowed} onClick={() => void sendMessage(t("modeAnonymousMessage"), "anonymous")} title={!anonymousAllowed ? t("anonymousUnavailable") : undefined} type="button">{t("anonymous")}</button><button className={`rounded-[6px] border px-2 py-2 text-xs font-bold ${state?.reporting_mode === "identified" ? "border-[#0b58c7] bg-blue-50 text-[#0b58c7]" : "border-slate-200 text-slate-600"}`} onClick={() => void sendMessage(t("modeIdentifiedMessage"), "identified")} type="button">{t("identified")}</button></div>
                {!anonymousAllowed ? <p className="mt-2 text-[11px] leading-4 text-slate-500">{t("anonymousUnavailable")}</p> : null}
              </div>
            ) : null}
            {canHandoff && handoff ? <Link className="mt-4 flex min-h-10 items-center justify-between rounded-[6px] bg-[#0b4fb3] px-4 py-2 text-sm font-bold text-white" href={handoffPath}>{handoff.target === "track_complaint" ? t("trackAction") : t("reportAction")}<ArrowRight size={17} /></Link> : <p className="mt-4 rounded-[6px] bg-[#edf4ff] px-3 py-2.5 text-xs leading-5 text-[#174574]">{pendingEntity ? t("confirmBeforeHandoff") : handoff?.target === "report_crime" ? t("chooseModeBeforeHandoff") : t("describePrompt")}</p>}
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
