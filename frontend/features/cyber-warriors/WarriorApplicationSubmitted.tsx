"use client";

import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ArrowLeft, CheckCircle2, Clock3, FileCheck2, Mail, RefreshCw, ShieldCheck} from "lucide-react";

import {Button} from "@/components/ui/Button";
import {warriorApplicationsApi, type WarriorApplication} from "@/lib/api/cyber-warriors";
import {getWarriorApplication, getWarriorIdentity, getWarriorToken, setWarriorApplication} from "@/lib/auth/warrior-session";
import {ApplicationError} from "./WarriorApplicationShell";

export function WarriorApplicationSubmitted() {
  const t = useTranslations("warriorApplication");
  const locale = useLocale();
  const router = useRouter();
  const [application, setApplication] = useState<WarriorApplication | null>(null);
  const [identityEmail, setIdentityEmail] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const refresh = useCallback(async () => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    setLoading(true);
    const result = await warriorApplicationsApi.listMine({accessToken: token});
    if (!result.ok || !result.data.length) {
      setError(t("statusLoadError"));
      setLoading(false);
      return;
    }
    const latest = [...result.data].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
    setApplication(latest);
    setWarriorApplication(latest);
    setError("");
    setLoading(false);
  }, [locale, router, t]);

  useEffect(() => {
    const cachedApplication = getWarriorApplication();
    if (cachedApplication) setApplication(cachedApplication);
    setIdentityEmail(getWarriorIdentity()?.accountEmail ?? "");
    void refresh();
  }, [refresh]);

  if (loading && !application) return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loadingStatus")}</div></main>;

  const submittedAt = application?.submitted_at ? new Intl.DateTimeFormat(locale, {dateStyle: "medium", timeStyle: "short"}).format(new Date(application.submitted_at)) : t("notAvailable");
  return (
    <main className="warrior-page warrior-submitted-page">
      <div className="shell-container warrior-submitted-layout">
        <section className="warrior-submitted-hero">
          <span className="warrior-success-icon"><CheckCircle2 aria-hidden="true" size={52} /></span>
          <h1>{t("submittedTitle")}</h1>
          <p>{t("submittedCopy")}</p>
          <div className="warrior-confirmation-mail"><Mail aria-hidden="true" size={24} /><span>{t("confirmationCopy", {email: identityEmail || t("registeredEmail")})}</span></div>
          <div className="warrior-submitted-actions">
            <Button onClick={() => router.push("/" + locale + "/cyber-warrior")} variant="outline"><ArrowLeft size={17} />{t("backWarrior")}</Button>
            <Button onClick={refresh} isLoading={loading}><RefreshCw size={17} />{t("refreshStatus")}</Button>
          </div>
        </section>
        <aside className="warrior-status-card">
          <h2>{t("statusTitle")}</h2>
          <span className="warrior-status-pill"><Clock3 aria-hidden="true" size={17} />{t("underReview")}</span>
          <p>{t("underReviewCopy")}</p>
          <dl>
            <div><dt><FileCheck2 size={17} />{t("applicationId")}</dt><dd>{application?.application_number ?? t("notAvailable")}</dd></div>
            <div><dt><Clock3 size={17} />{t("submittedOn")}</dt><dd>{submittedAt}</dd></div>
            <div><dt><ShieldCheck size={17} />{t("reviewTime")}</dt><dd>{t("reviewWindow")}</dd></div>
            <div><dt><Mail size={17} />{t("nextUpdate")}</dt><dd>{t("nextUpdateCopy")}</dd></div>
          </dl>
          <div className="warrior-status-note">{t("dashboardHandoff")}</div>
          <ApplicationError message={error} />
        </aside>
      </div>
      <div className="shell-container warrior-help-strip"><ShieldCheck aria-hidden="true" size={20} /><strong>{t("helpTitle")}</strong><span>{t("helpCopy")}</span><a href="tel:1930">{t("helpline")}</a></div>
    </main>
  );
}
