"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowRight, FileText, PencilLine, Plus, Trash2} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {warriorReportsApi, type WarriorReport} from "@/lib/api/cyber-warriors";
import {getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {reportCategoryLabelKey, reportStatusToneClass} from "./warriorReportMeta";

export function WarriorMyReports() {
  const t = useTranslations("warriorReport");
  const locale = useLocale();
  const router = useRouter();
  const [reports, setReports] = useState<WarriorReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const load = useCallback(async () => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    const result = await warriorReportsApi.listMine({accessToken: token});
    if (result.ok) {
      setReports([...result.data].sort((a, b) => b.created_at.localeCompare(a.created_at)));
    }
    setLoading(false);
  }, [locale, router]);

  useEffect(() => {
    void load();
  }, [load]);

  async function deleteDraft(id: string) {
    const token = getWarriorToken();
    if (!token) return;
    setDeletingId(id);
    const result = await warriorReportsApi.remove(id, {accessToken: token});
    setDeletingId(null);
    if (result.ok) setReports((current) => current.filter((item) => item.id !== id));
  }

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loadingReports")}</div></main>;
  }

  const dateFormatter = new Intl.DateTimeFormat(locale, {dateStyle: "medium"});

  return (
    <WarriorShellPage active="myReports">
      <div className="warrior-dashboard-content warrior-full-width">
        <div className="warrior-dashboard-header-row">
          <div>
            <h1>{t("myReportsTitle")}</h1>
            <p>{t("myReportsCopy")}</p>
          </div>
          <Button onClick={() => router.push("/" + locale + "/cyber-warrior/reports/new")}><Plus aria-hidden="true" size={17} />{t("newReportAction")}</Button>
        </div>
        {reports.length === 0 ? (
          <div className="warrior-coming-soon">
            <span aria-hidden="true"><FileText size={30} /></span>
            <h2>{t("noReportsTitle")}</h2>
            <p>{t("noReportsCopy")}</p>
          </div>
        ) : (
          <div className="warrior-report-list">
            {reports.map((report) => {
              if (report.status === "DRAFT") {
                return (
                  <div className="warrior-report-list-row is-draft" key={report.id}>
                    <span aria-hidden="true"><FileText size={20} /></span>
                    <div>
                      <strong>{t(reportCategoryLabelKey(report.report_type))}</strong>
                      <small>{t("draftSavedNote")}</small>
                    </div>
                    <span className={"warrior-status-pill-inline " + reportStatusToneClass(report.status)}>{t("status." + report.status)}</span>
                    <div className="warrior-report-row-actions">
                      <button onClick={() => router.push("/" + locale + "/cyber-warrior/reports/new?draftId=" + report.id)} type="button"><PencilLine aria-hidden="true" size={15} />{t("continueDraftAction")}</button>
                      <button disabled={deletingId === report.id} onClick={() => void deleteDraft(report.id)} type="button"><Trash2 aria-hidden="true" size={15} />{t("deleteDraftAction")}</button>
                    </div>
                  </div>
                );
              }
              return (
                <Link className="warrior-report-list-row" href={"/" + locale + "/cyber-warrior/reports/" + report.id} key={report.id}>
                  <span aria-hidden="true"><FileText size={20} /></span>
                  <div>
                    <strong>{t(reportCategoryLabelKey(report.report_type))}</strong>
                    <small>{t("summarySubmittedOn")}: {report.submitted_at ? dateFormatter.format(new Date(report.submitted_at)) : t("notAvailable")}</small>
                  </div>
                  <span className={"warrior-status-pill-inline " + reportStatusToneClass(report.status)}>{t("status." + report.status)}</span>
                  <ArrowRight aria-hidden="true" size={16} />
                </Link>
              );
            })}
          </div>
        )}
      </div>
    </WarriorShellPage>
  );
}
