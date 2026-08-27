"use client";

import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {CheckCircle2, Clock3, FileSearch, FileText, ShieldCheck} from "lucide-react";

import type {ApiRecord} from "@/lib/api/auth";
import {evidenceApi} from "@/lib/api/complaints";
import {warriorReportsApi, type WarriorReport} from "@/lib/api/cyber-warriors";
import {getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {computeReportTimeline, reportCategoryLabelKey, reportStatusToneClass} from "./warriorReportMeta";

type EvidenceItem = {fileName: string; fileSize: number; id: string};

export function WarriorReportDetails({reportId}: {reportId: string}) {
  const t = useTranslations("warriorReport");
  const locale = useLocale();
  const router = useRouter();
  const [report, setReport] = useState<WarriorReport | null>(null);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [notFound, setNotFound] = useState(false);

  useEffect(() => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    let active = true;
    Promise.all([
      warriorReportsApi.getById(reportId, {accessToken: token}),
      evidenceApi.listByWarriorReport(reportId, {accessToken: token})
    ]).then(([reportResult, evidenceResult]) => {
      if (!active) return;
      if (!reportResult.ok) {
        setNotFound(true);
        setLoading(false);
        return;
      }
      setReport(reportResult.data);
      if (evidenceResult.ok) {
        setEvidence(evidenceResult.data.map((item: ApiRecord) => ({
          fileName: typeof item.file_name === "string" ? item.file_name : t("notAvailable"),
          fileSize: typeof item.file_size === "number" ? item.file_size : 0,
          id: String(item.id)
        })));
      }
      setLoading(false);
    });
    return () => { active = false; };
  }, [locale, reportId, router, t]);

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loadingReport")}</div></main>;
  }

  if (notFound || !report) {
    return (
      <WarriorShellPage active="myReports">
        <div className="warrior-dashboard-content warrior-full-width">
          <div className="warrior-coming-soon">
            <span aria-hidden="true"><FileSearch size={30} /></span>
            <h2>{t("reportNotFoundTitle")}</h2>
            <p>{t("reportNotFoundCopy")}</p>
          </div>
        </div>
      </WarriorShellPage>
    );
  }

  const dateFormatter = new Intl.DateTimeFormat(locale, {dateStyle: "medium", timeStyle: "short"});
  const timeline = computeReportTimeline(report.status);
  const timelineIcons = [CheckCircle2, CheckCircle2, Clock3, ShieldCheck, FileSearch, CheckCircle2];
  const [descriptionSummary] = report.description.split("\n\n");

  return (
    <WarriorShellPage active="myReports">
      <div className="warrior-dashboard-content">
        <div className="warrior-profile-header-row">
          <div>
            <h1>{t("detailsTitle")}</h1>
            <p>{t("detailsCopy")}</p>
          </div>
        </div>

        <section className="warrior-profile-section">
          <div className="warrior-track-summary">
            <div><dt>{t("reportReference")}</dt><dd>{report.id.slice(0, 8).toUpperCase()}</dd></div>
            <div><dt>{t("incidentTypeTitle")}</dt><dd>{t(reportCategoryLabelKey(report.report_type))}</dd></div>
            <div><dt>{t("summarySubmittedOn")}</dt><dd>{report.submitted_at ? dateFormatter.format(new Date(report.submitted_at)) : t("notAvailable")}</dd></div>
            <div><dt>{t("currentStatus")}</dt><dd><span className={"warrior-status-pill-inline " + reportStatusToneClass(report.status)}>{t("status." + report.status)}</span></dd></div>
          </div>
        </section>

        <section className="warrior-profile-section">
          <h2>{t("incidentDetailsTitle")}</h2>
          <p className="warrior-profile-bio">{descriptionSummary}</p>
        </section>

        <section className="warrior-profile-section">
          <h2>{t("evidenceUploadedTitle", {count: evidence.length})}</h2>
          {evidence.length ? (
            <ul className="warrior-review-evidence-list">
              {evidence.map((item) => <li key={item.id}><FileText aria-hidden="true" size={15} />{item.fileName}</li>)}
            </ul>
          ) : <p className="warrior-report-field-label">{t("notProvided")}</p>}
        </section>
      </div>

      <aside className="warrior-dashboard-rail">
        <div className="warrior-status-widget">
          <h2>{t("authorityUpdatesTitle")}</h2>
          <ol className="warrior-journey-track warrior-track-timeline warrior-timeline-vertical">
            {timeline.map((step, index) => {
              const Icon = timelineIcons[index];
              return (
                <li className={step.state === "complete" ? "is-complete" : step.state === "current" ? "is-current" : ""} key={step.key}>
                  <span aria-hidden="true"><Icon size={16} /></span>
                  <strong>{t(step.key)}</strong>
                  <small>{step.state === "pending" ? t("timelinePending") : t(step.key + "Copy")}</small>
                </li>
              );
            })}
          </ol>
        </div>
        <div className="warrior-status-widget">
          <ShieldCheck aria-hidden="true" size={18} />
          <p className="warrior-status-hint">{t("privacyReminder")}</p>
        </div>
      </aside>
    </WarriorShellPage>
  );
}
