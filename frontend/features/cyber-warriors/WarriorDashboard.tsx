"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {
  AlarmClock,
  ArrowRight,
  Award,
  Bug,
  CheckCircle2,
  Clock3,
  FileText,
  Globe2,
  Lock,
  Mail,
  ShieldAlert,
  Star,
  Trophy,
  User,
  UserRound
} from "lucide-react";

import {cyberWarriorsApi, warriorApplicationsApi, warriorReportsApi, type WarriorApplication} from "@/lib/api/cyber-warriors";
import {notificationsApi} from "@/lib/api/notifications";
import {getWarriorIdentity, getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage, WarriorTopBar} from "./WarriorAppShell";

type WarriorReportSummary = {status: string};

type DashboardData = {
  application: WarriorApplication | null;
  identityName: string;
  notificationCount: number;
  profileCreatedAt: string | null;
  reports: WarriorReportSummary[];
};

const emptyData: DashboardData = {application: null, identityName: "", notificationCount: 0, profileCreatedAt: null, reports: []};

export function WarriorDashboard() {
  const t = useTranslations("warriorDashboard");
  const locale = useLocale();
  const router = useRouter();
  const [data, setData] = useState<DashboardData>(emptyData);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    const identity = getWarriorIdentity();
    const [profileResult, applicationsResult, reportsResult, notificationsResult] = await Promise.all([
      cyberWarriorsApi.getMine({accessToken: token}),
      warriorApplicationsApi.listMine({accessToken: token}),
      warriorReportsApi.listMine({accessToken: token}),
      notificationsApi.listMine({accessToken: token})
    ]);
    const latestApplication = applicationsResult.ok && applicationsResult.data.length
      ? [...applicationsResult.data].sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
      : null;
    setData({
      application: latestApplication,
      identityName: identity?.profile.full_name ?? "",
      notificationCount: notificationsResult.ok ? notificationsResult.data.filter((item) => !item.is_read).length : 0,
      profileCreatedAt: profileResult.ok ? String(profileResult.data.created_at ?? "") : null,
      reports: reportsResult.ok ? reportsResult.data.map((item) => ({status: String((item as {status?: unknown}).status ?? "")})) : []
    });
    setLoading(false);
  }, [locale, router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loadingDashboard")}</div></main>;
  }

  const {application, identityName, notificationCount, profileCreatedAt, reports} = data;
  const dateFormatter = new Intl.DateTimeFormat(locale, {dateStyle: "medium"});
  const formatDate = (value: string | null) => (value ? dateFormatter.format(new Date(value)) : "");

  const submittedCount = reports.filter((r) => r.status !== "DRAFT").length;
  const underReviewCount = reports.filter((r) => r.status === "SUBMITTED" || r.status === "UNDER_REVIEW").length;
  const resolvedCount = reports.filter((r) => r.status === "ACCEPTED").length;

  const applicationStatus = application?.status ?? null;
  const journey = [
    {
      complete: Boolean(profileCreatedAt),
      copy: profileCreatedAt ? formatDate(profileCreatedAt) : t("journeyPending"),
      current: false,
      icon: CheckCircle2,
      title: t("journeyProfileCreated")
    },
    {
      complete: Boolean(application?.submitted_at),
      copy: application?.submitted_at ? formatDate(application.submitted_at) : t("journeyPending"),
      current: false,
      icon: CheckCircle2,
      title: t("journeyApplicationSubmitted")
    },
    {
      complete: applicationStatus === "APPROVED" || applicationStatus === "REJECTED",
      copy: applicationStatus === "UNDER_REVIEW" || applicationStatus === "SUBMITTED" ? t("journeyInProgress") : applicationStatus ? t("journeyDone") : t("journeyPending"),
      current: applicationStatus === "UNDER_REVIEW" || applicationStatus === "SUBMITTED",
      icon: Clock3,
      title: t("journeyUnderReview")
    },
    {
      complete: reports.length > 0,
      copy: reports.length > 0 ? t("journeyDone") : t("journeyPending"),
      current: false,
      icon: Star,
      title: t("journeyFirstReport")
    },
    {
      complete: false,
      copy: t("journeyKeepGoing"),
      current: false,
      icon: Trophy,
      title: t("journeyLevelUp")
    }
  ];

  const stats = [
    {icon: FileText, label: t("statSubmitted"), note: t("statSubmittedNote"), tone: "blue", value: submittedCount},
    {icon: AlarmClock, label: t("statUnderReview"), note: t("statUnderReviewNote"), tone: "amber", value: underReviewCount},
    {icon: CheckCircle2, label: t("statResolved"), note: t("statResolvedNote"), tone: "green", value: resolvedCount},
    {icon: Star, label: t("statRewards"), note: t("statRewardsNote"), tone: "purple", value: 0}
  ];

  const quickActions = [
    {href: "/" + locale + "/cyber-warrior/reports/new", icon: ShieldAlert, key: "report", label: t("quickReport"), note: t("quickReportNote")},
    {href: "/" + locale + "/cyber-warrior/reports/track", icon: FileText, key: "track", label: t("quickTrack"), note: t("quickTrackNote")},
    {href: "/" + locale + "/cyber-warrior/profile", icon: User, key: "profile", label: t("quickProfile"), note: t("quickProfileNote")},
    {href: "/" + locale + "/cyber-warrior/resources", icon: Globe2, key: "learn", label: t("quickLearn"), note: t("quickLearnNote")}
  ];

  return (
    <WarriorShellPage active="dashboard">
      <div className="warrior-dashboard-content">
        <div className="warrior-dashboard-header-row">
          <div>
            <h1>{t("welcomeTitle", {name: identityName || t("fallbackName")})}</h1>
            <p>{t("welcomeCopy")}</p>
          </div>
          <div className="warrior-dashboard-header-right">
            <WarriorTopBar name={identityName || t("fallbackName")} notificationCount={notificationCount} roleLabel={t("roleLabel")} />
            <div className="warrior-dashboard-meta">
              <span><strong>{t("warriorId")}:</strong> {application?.application_number ?? t("notAvailable")}</span>
              <span>{t("memberSince", {date: profileCreatedAt ? formatDate(profileCreatedAt) : t("notAvailable")})}</span>
            </div>
          </div>
        </div>

        <div className="warrior-stat-grid">
          {stats.map((stat) => (
            <div className={"warrior-stat-tile tone-" + stat.tone} key={stat.label}>
              <span aria-hidden="true"><stat.icon size={20} /></span>
              <strong>{stat.value}</strong>
              <p>{stat.label}</p>
              <small>{stat.note}</small>
            </div>
          ))}
        </div>

        <section className="warrior-cta-banner">
          <div>
            <p className="eyebrow">{t("ctaEyebrow")}</p>
            <h2>{t("ctaTitle")}</h2>
            <p>{t("ctaCopy")}</p>
            <Link className="portal-primary-link" href={"/" + locale + "/cyber-warrior/reports/new"}>{t("ctaAction")}<ArrowRight aria-hidden="true" size={17} /></Link>
          </div>
          <div className="warrior-cta-visual" aria-hidden="true">
            <span className="warrior-cta-figure"><UserRound size={54} /></span>
            <span className="warrior-cta-orbit warrior-cta-orbit-1"><Mail size={18} /></span>
            <span className="warrior-cta-orbit warrior-cta-orbit-2"><Lock size={18} /></span>
            <span className="warrior-cta-orbit warrior-cta-orbit-3"><Bug size={18} /></span>
            <span className="warrior-cta-orbit warrior-cta-orbit-4"><Globe2 size={18} /></span>
          </div>
        </section>

        <section className="warrior-journey">
          <h2>{t("journeyTitle")}</h2>
          <p>{t("journeyCopy")}</p>
          <ol className="warrior-journey-track">
            {journey.map((step) => (
              <li className={step.complete ? "is-complete" : step.current ? "is-current" : ""} key={step.title}>
                <span aria-hidden="true"><step.icon size={20} /></span>
                <strong>{step.title}</strong>
                <small>{step.copy}</small>
              </li>
            ))}
          </ol>
        </section>
      </div>

      <aside className="warrior-dashboard-rail">
        <div className="warrior-status-widget">
          <h2>{t("statusTitle")}</h2>
          <div className="warrior-status-badge"><Award aria-hidden="true" size={22} /><div><strong>{t("rankRookie")}</strong><span>{t("levelLabel", {level: 1})}</span></div></div>
          <div className="warrior-xp-track"><i style={{width: "0%"}} /></div>
          <p>{t("xpCopy", {current: 0, total: 100})}</p>
          <p className="warrior-status-hint">{t("xpHint")}</p>
          <Link className="warrior-text-link" href={"/" + locale + "/cyber-warrior/leaderboard"}>{t("viewLeaderboard")}<ArrowRight aria-hidden="true" size={15} /></Link>
        </div>
        <div className="warrior-quick-actions">
          <h2>{t("quickActionsTitle")}</h2>
          <ul>
            {quickActions.map((action) => (
              <li key={action.key}>
                <Link href={action.href}>
                  <span aria-hidden="true"><action.icon size={18} /></span>
                  <span><strong>{action.label}</strong><small>{action.note}</small></span>
                  <ArrowRight aria-hidden="true" size={15} />
                </Link>
              </li>
            ))}
          </ul>
        </div>
      </aside>
    </WarriorShellPage>
  );
}
