"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowRight, CheckCircle2, Clock3, FileSearch, ShieldCheck} from "lucide-react";

import {warriorReportsApi, type WarriorReport} from "@/lib/api/cyber-warriors";
import {getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {computeReportTimeline, reportCategoryLabelKey, reportStatusToneClass} from "./warriorReportMeta";

export function WarriorTrackReport() {
  const t = useTranslations("warriorReport");
  const locale = useLocale();
  const router = useRouter();
  const [report, setReport] = useState<WarriorReport | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    let active = true;
    warriorReportsApi.listMine({accessToken: token}).then((result) => {
      if (!active) return;
      if (result.ok && result.data.length) {
        const submitted = result.data.filter((item) => item.status !== "DRAFT");
        const latest = [...submitted].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
        setReport(latest ?? null);
      }
      setLoading(false);
    });
    return () => { active = false; };
  }, [locale, router]);

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loadingReports")}</div></main>;
  }

  if (!report) {
    return (
      <WarriorShellPage active="trackReports">
        <div className="warrior-dashboard-content warrior-full-width">
          <div className="warrior-coming-soon">
            <span aria-hidden="true"><FileSearch size={30} /></span>
            <h2>{t("noReportsTitle")}</h2>
            <p>{t("noReportsCopy")}</p>
          </div>
        </div>
      </WarriorShellPage>
    );
  }

  const dateFormatter = new Intl.DateTimeFormat(locale, {dateStyle: "medium", timeStyle: "short"});
  const timeline = computeReportTimeline(report.status);
  const timelineIcons = [CheckCircle2, CheckCircle2, Clock3, ShieldCheck, FileSearch, CheckCircle2];

  return (
    <WarriorShellPage active="trackReports">
      <div className="warrior-dashboard-content warrior-full-width">
        <h1>{t("trackTitle")}</h1>
        <p>{t("trackCopy")}</p>

        <section className="warrior-track-card">
          <div className="warrior-track-summary">
            <div><dt>{t("reportReference")}</dt><dd>{report.id.slice(0, 8).toUpperCase()}</dd></div>
            <div><dt>{t("incidentTypeTitle")}</dt><dd>{t(reportCategoryLabelKey(report.report_type))}</dd></div>
            <div><dt>{t("currentStatus")}</dt><dd><span className={"warrior-status-pill-inline " + reportStatusToneClass(report.status)}>{t("status." + report.status)}</span></dd></div>
            <div><dt>{t("summarySubmittedOn")}</dt><dd>{report.submitted_at ? dateFormatter.format(new Date(report.submitted_at)) : t("notAvailable")}</dd></div>
          </div>
        </section>

        <section className="warrior-journey">
          <h2>{t("investigationProgressTitle")}</h2>
          <ol className="warrior-journey-track warrior-track-timeline">
            {timeline.map((step, index) => {
              const Icon = timelineIcons[index];
              return (
                <li className={step.state === "complete" ? "is-complete" : step.state === "current" ? "is-current" : ""} key={step.key}>
                  <span aria-hidden="true"><Icon size={18} /></span>
                  <strong>{t(step.key)}</strong>
                  <small>{step.state === "pending" ? t("timelinePending") : report.submitted_at ? dateFormatter.format(new Date(report.submitted_at)) : ""}</small>
                </li>
              );
            })}
          </ol>
          <div className="warrior-status-note">{t("trackingHint")}</div>
        </section>

        <Link className="warrior-text-link" href={"/" + locale + "/cyber-warrior/reports/" + report.id}>{t("viewFullDetails")}<ArrowRight aria-hidden="true" size={15} /></Link>
      </div>
    </WarriorShellPage>
  );
}
