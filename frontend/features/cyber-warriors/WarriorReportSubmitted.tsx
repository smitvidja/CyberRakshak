"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowRight, CheckCircle2, Clock3, Headphones, Lock, Mail, Search} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {warriorReportsApi, type WarriorReport} from "@/lib/api/cyber-warriors";
import {getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {reportCategoryLabelKey} from "./warriorReportMeta";

export function WarriorReportSubmitted({reportId}: {reportId: string}) {
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
    warriorReportsApi.getById(reportId, {accessToken: token}).then((result) => {
      if (!active) return;
      if (result.ok) setReport(result.data);
      setLoading(false);
    });
    return () => { active = false; };
  }, [locale, reportId, router]);

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loadingReport")}</div></main>;
  }

  const dateFormatter = new Intl.DateTimeFormat(locale, {dateStyle: "medium", timeStyle: "short"});
  const submittedAt = report?.submitted_at ? dateFormatter.format(new Date(report.submitted_at)) : t("notAvailable");
  const referenceId = report ? report.id.slice(0, 8).toUpperCase() : t("notAvailable");

  return (
    <WarriorShellPage active="myReports">
      <div className="warrior-dashboard-content">
        <section className="warrior-report-success">
          <span className="warrior-success-icon" aria-hidden="true"><CheckCircle2 size={48} /></span>
          <h1>{t("submittedTitle")}</h1>
          <p>{t("submittedCopy")}</p>
          <div className="warrior-reference-box">
            <span>{t("reportReference")}</span>
            <strong>{referenceId}</strong>
          </div>
          <div className="warrior-submitted-actions">
            <Button onClick={() => router.push("/" + locale + "/cyber-warrior/reports/track")} variant="outline"><Search aria-hidden="true" size={17} />{t("trackReportAction")}</Button>
            <Button onClick={() => router.push("/" + locale + "/cyber-warrior/dashboard")}>{t("goToDashboard")}<ArrowRight aria-hidden="true" size={17} /></Button>
          </div>
        </section>

        <section className="warrior-journey">
          <h2>{t("whatHappensNextTitle")}</h2>
          <div className="warrior-next-steps-grid">
            <div><span aria-hidden="true"><Mail size={20} /></span><strong>{t("nextAckTitle")}</strong><small>{t("nextAckCopy")}</small></div>
            <div><span aria-hidden="true"><Search size={20} /></span><strong>{t("nextReviewTitle")}</strong><small>{t("nextReviewCopy")}</small></div>
            <div><span aria-hidden="true"><Clock3 size={20} /></span><strong>{t("nextActionTitle")}</strong><small>{t("nextActionCopy")}</small></div>
            <div><span aria-hidden="true"><Headphones size={20} /></span><strong>{t("nextHelpTitle")}</strong><small>{t("nextHelpCopy")}</small></div>
          </div>
        </section>
      </div>

      <aside className="warrior-dashboard-rail">
        <div className="warrior-status-widget">
          <div className="warrior-secure-note"><Lock aria-hidden="true" size={20} /><div><strong>{t("secureTitle")}</strong><p>{t("secureCopy")}</p></div></div>
        </div>
        <div className="warrior-status-widget">
          <h2>{t("reportSummaryTitle")}</h2>
          <dl className="warrior-mini-stats">
            <div><dt>{t("incidentTypeTitle")}</dt><dd>{report ? t(reportCategoryLabelKey(report.report_type)) : t("notAvailable")}</dd></div>
            <div><dt>{t("summarySubmittedOn")}</dt><dd>{submittedAt}</dd></div>
          </dl>
          <Link className="warrior-text-link" href={"/" + locale + "/cyber-warrior/reports/" + reportId}>{t("viewFullDetails")}<ArrowRight aria-hidden="true" size={15} /></Link>
        </div>
        <div className="warrior-quick-actions">
          <h2>{t("importantRemindersTitle")}</h2>
          <ul className="warrior-reminder-list">
            <li>{t("reminderNoShare")}</li>
            <li>{t("reminderKeepEvidence")}</li>
            <li>{t("reminderReportMore")}</li>
          </ul>
        </div>
      </aside>
    </WarriorShellPage>
  );
}
