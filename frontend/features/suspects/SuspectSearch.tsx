"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {AlertTriangle, ArrowRight, CheckCircle2, FileWarning, Info, RotateCcw, Search, ShieldQuestion} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {SelectField, TextArea, TextInput} from "@/components/ui/FormFields";
import {suspectsApi} from "@/lib/api/complaints";
import {saveSuspectHandoff, takeSuspectHandoff} from "@/lib/suspect-handoff";

const identifierTypes = ["PHONE", "EMAIL", "UPI", "BANK_ACCOUNT", "WEBSITE", "SOCIAL_MEDIA", "OTHER"] as const;
type SearchResult = {countCapped: boolean; count: number; masked: string; state: string};

function stringValue(value: unknown) { return typeof value === "string" ? value : ""; }
function numberValue(value: unknown) { return typeof value === "number" ? value : 0; }

export function SuspectSearch() {
  const t = useTranslations("suspectSearch");
  const locale = useLocale();
  const router = useRouter();
  const [identifierType, setIdentifierType] = useState("PHONE");
  const [identifierValue, setIdentifierValue] = useState("");
  const [fieldError, setFieldError] = useState("");
  const [serviceError, setServiceError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [showCorrection, setShowCorrection] = useState(false);
  const [correctionReason, setCorrectionReason] = useState("");
  const [correctionError, setCorrectionError] = useState("");
  const [correctionReference, setCorrectionReference] = useState("");

  useEffect(() => {
    const handoff = takeSuspectHandoff();
    // A handoff is consumed once and cleared, so it must run as a mount effect:
    // reading it during render would drop the value on a double render, and a
    // lazy initializer would disagree with the server snapshot on a hard reload.
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot browser handoff
    if (handoff) { setIdentifierType(handoff.identifierType); setIdentifierValue(handoff.identifierValue); }
  }, []);

  async function search(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (identifierValue.trim().length < 2) { setFieldError(t("validation.required")); return; }
    setSubmitting(true); setServiceError(""); setFieldError(""); setResult(null); setShowCorrection(false); setCorrectionReference("");
    const response = await suspectsApi.search({identifier_type: identifierType, identifier_value: identifierValue.trim()});
    if (!response.ok) {
      if (response.error.code === "RATE_LIMITED") setServiceError(t("rateLimited"));
      else if (response.error.code === "INVALID_IDENTIFIER" || response.error.code === "VALIDATION_ERROR") setFieldError(t("validation.invalid"));
      else setServiceError(t("searchError"));
      setSubmitting(false); return;
    }
    setResult({countCapped: response.data.count_capped === true, count: numberValue(response.data.eligible_report_count), masked: stringValue(response.data.masked_identifier), state: stringValue(response.data.match_state)});
    setSubmitting(false);
  }

  function continueToReport() {
    saveSuspectHandoff({identifierType, identifierValue});
    router.push(`/${locale}/suspects/report`);
  }

  async function submitCorrection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (correctionReason.trim().length < 10) { setCorrectionError(t("correctionReasonError")); return; }
    setSubmitting(true); setCorrectionError("");
    const response = await suspectsApi.createCorrection({identifier_type: identifierType, identifier_value: identifierValue.trim(), reason: correctionReason.trim()});
    if (!response.ok) { setCorrectionError(t("correctionError")); setSubmitting(false); return; }
    setCorrectionReference(stringValue(response.data.id)); setSubmitting(false);
  }

  return <main className="suspect-search-page">
    <header className="suspect-search-hero"><div className="shell-container"><p><ShieldQuestion aria-hidden="true" size={16}/>{t("eyebrow")}</p><h1>{t("title")}</h1><span>{t("intro")}</span></div></header>
    <div className="shell-container suspect-search-layout">
      <section className="suspect-search-panel" aria-labelledby="suspect-search-form-title">
        <div className="suspect-search-panel-head"><span><Search aria-hidden="true" size={22}/></span><div><h2 id="suspect-search-form-title">{t("formTitle")}</h2><p>{t("formCopy")}</p></div></div>
        <form noValidate onSubmit={search}><div className="suspect-search-fields"><SelectField id="search-identifier-type" label={t("identifierTypeLabel")} onChange={(event) => {setIdentifierType(event.target.value); setResult(null);}} options={identifierTypes.map((type) => ({label: t("identifierTypes." + type), value: type}))} value={identifierType}/><TextInput autoComplete="off" description={t("identifierHelp")} error={fieldError} id="search-identifier-value" label={t("identifierValueLabel")} onChange={(event) => {setIdentifierValue(event.target.value); setFieldError(""); setResult(null);}} required value={identifierValue}/></div><Button isLoading={submitting} type="submit">{t("searchAction")}</Button></form>
        <p className="suspect-search-privacy"><Info aria-hidden="true" size={16}/>{t("privacyNote")}</p>
      </section>

      <aside className="suspect-search-guidance" aria-labelledby="suspect-guidance-title"><h2 id="suspect-guidance-title">{t("guidanceTitle")}</h2><ul><li><CheckCircle2 aria-hidden="true"/>{t("guidanceExact")}</li><li><ShieldQuestion aria-hidden="true"/>{t("guidanceNoProof")}</li><li><FileWarning aria-hidden="true"/>{t("guidanceEligible")}</li></ul><Link href={`/${locale}/secure-india`}>{t("backToMap")} <ArrowRight aria-hidden="true" size={14}/></Link></aside>

      {serviceError ? <section className="suspect-result is-error" role="alert"><AlertTriangle aria-hidden="true"/><div><h2>{t("errorTitle")}</h2><p>{serviceError}</p></div></section> : null}
      {result ? <section aria-live="polite" className={"suspect-result " + (result.state === "REPORTED_SIGNAL_FOUND" ? "is-match" : "is-clear")}><span>{result.state === "REPORTED_SIGNAL_FOUND" ? <AlertTriangle aria-hidden="true"/> : <ShieldQuestion aria-hidden="true"/>}</span><div><p className="suspect-result-kicker">{result.masked}</p><h2>{result.state === "REPORTED_SIGNAL_FOUND" ? t("matchTitle") : t("noMatchTitle")}</h2><p>{result.state === "REPORTED_SIGNAL_FOUND" ? t("matchCopy", {count: result.count, suffix: result.countCapped ? "+" : ""}) : t("noMatchCopy")}</p><strong>{t("resultDisclaimer")}</strong><div className="suspect-result-actions"><Button onClick={continueToReport}>{t("reportAction")}</Button><button onClick={() => setShowCorrection((current) => !current)} type="button">{t("correctionAction")}</button><button onClick={() => {setResult(null); setIdentifierValue("");}} type="button"><RotateCcw aria-hidden="true" size={14}/>{t("searchAgain")}</button></div></div></section> : null}

      {showCorrection && result ? <section className="suspect-correction-panel" aria-labelledby="correction-title"><div><h2 id="correction-title">{t("correctionTitle")}</h2><p>{t("correctionCopy")}</p></div>{correctionReference ? <div className="suspect-correction-success"><CheckCircle2 aria-hidden="true"/><span><strong>{t("correctionSubmitted")}</strong>{t("correctionReference", {reference: correctionReference})}</span></div> : <form onSubmit={submitCorrection}><TextArea description={t("correctionReasonHelp")} error={correctionError} id="correction-reason" label={t("correctionReasonLabel")} onChange={(event) => {setCorrectionReason(event.target.value); setCorrectionError("");}} required value={correctionReason}/><Button isLoading={submitting} type="submit" variant="outline">{t("correctionSubmit")}</Button></form>}</section> : null}
    </div>
  </main>;
}
