"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {
  AlarmClock,
  ArrowRight,
  Award,
  CheckCircle2,
  Clock3,
  FileText,
  Globe2,
  RefreshCw,
  ShieldAlert,
  Star,
  Trophy,
  TriangleAlert,
  User
} from "lucide-react";

import {cyberWarriorsApi, warriorApplicationsApi, warriorReportsApi, type WarriorApplication} from "@/lib/api/cyber-warriors";
import {notificationsApi, type NotificationRecord} from "@/lib/api/notifications";
import {getWarriorIdentity, getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage, WarriorTopBar} from "./WarriorAppShell";
import {WarriorCtaIllustration} from "./WarriorCtaIllustration";
import {computeWarriorPoints, levelProgress} from "./warriorReportMeta";

type WarriorReportSummary = {status: string};

type DashboardData = {
  application: WarriorApplication | null;
  identityName: string;
  notifications: NotificationRecord[];
  profileCreatedAt: string | null;
  reports: WarriorReportSummary[];
  warriorCode: string | null;
};

const emptyData: DashboardData = {application: null, identityName: "", notifications: [], profileCreatedAt: null, reports: [], warriorCode: null};

export function WarriorDashboard() {
  const t = useTranslations("warriorDashboard");
  const tBadges = useTranslations("warriorBadges");
  const locale = useLocale();
  const router = useRouter();
  const [data, setData] = useState<DashboardData>(emptyData);
  const [loading, setLoading] = useState(true);
  const [failedSources, setFailedSources] = useState<string[]>([]);

  const load = useCallback(async () => {
    const currentToken = getWarriorToken();
    if (!currentToken) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    const identity = getWarriorIdentity();
    const [profileResult, applicationsResult, reportsResult, notificationsResult] = await Promise.all([
      cyberWarriorsApi.getMine({accessToken: currentToken}),
      warriorApplicationsApi.listMine({accessToken: currentToken}),
      warriorReportsApi.listMine({accessToken: currentToken}),
      notificationsApi.listMine({accessToken: currentToken})
    ]);
    const latestApplication = applicationsResult.ok && applicationsResult.data.length
      ? [...applicationsResult.data].sort((a, b) => b.created_at.localeCompare(a.created_at))[0]
      : null;
    const failed: string[] = [];
    if (!profileResult.ok) failed.push(t("loadErrorProfile"));
    if (!applicationsResult.ok) failed.push(t("loadErrorApplication"));
    if (!reportsResult.ok) failed.push(t("loadErrorReports"));
    if (!notificationsResult.ok) failed.push(t("loadErrorNotifications"));
    setFailedSources(failed);
    setData({
      application: latestApplication,
      identityName: identity?.profile.full_name ?? "",
      notifications: notificationsResult.ok ? notificationsResult.data : [],
      profileCreatedAt: profileResult.ok ? String(profileResult.data.created_at ?? "") : null,
      reports: reportsResult.ok ? reportsResult.data.map((item) => ({status: String((item as {status?: unknown}).status ?? "")})) : [],
      warriorCode: profileResult.ok && profileResult.data.warrior_code ? String(profileResult.data.warrior_code) : null
    });
    setLoading(false);
  }, [locale, router, t]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- load() only sets state after an await
    void load();
  }, [load]);

  async function markNotificationRead(id: string) {
    const token = getWarriorToken();
    if (!token) return;
    setData((current) => ({...current, notifications: current.notifications.map((item) => (item.id === id ? {...item, is_read: true} : item))}));
    await notificationsApi.markRead(id, {accessToken: token});
  }

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loadingDashboard")}</div></main>;
  }

  const {application, identityName, notifications, profileCreatedAt, reports, warriorCode} = data;
  const dateFormatter = new Intl.DateTimeFormat(locale, {dateStyle: "medium"});
  const formatDate = (value: string | null) => (value ? dateFormatter.format(new Date(value)) : "");

  const submittedCount = reports.filter((r) => r.status !== "DRAFT").length;
  // Same rule as the Badges & Rewards page, so one warrior never shows two levels.
  const progress = levelProgress(computeWarriorPoints(reports));
  const tierName = {BRONZE: tBadges("rankBronze"), GOLD: tBadges("rankGold"), SILVER: tBadges("rankSilver")} as const;
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
    {icon: Star, label: t("statRewards"), note: t("statRewardsNote"), tone: "purple", value: computeWarriorPoints(reports)}
  ];

  const quickActions = [
    {href: "/" + locale + "/cyber-warrior/reports/new", icon: ShieldAlert, key: "report", label: t("quickReport"), note: t("quickReportNote")},
    {href: "/" + locale + "/cyber-warrior/reports/track", icon: FileText, key: "track", label: t("quickTrack"), note: t("quickTrackNote")},
    {href: "/" + locale + "/cyber-warrior/profile", icon: User, key: "profile", label: t("quickProfile"), note: t("quickProfileNote")},
    {href: "/" + locale + "/cyber-warrior/resources", icon: Globe2, key: "learn", label: t("quickLearn"), note: t("quickLearnNote")}
  ];

  return (
    <WarriorShellPage active="dashboard">
      {/* Step 5 reference: bell + avatar sit in their own row at the top right, above both
          the content and the Warrior Status rail - not squeezed beside the welcome text. */}
      <div className="warrior-dashboard-topbar-row">
        <WarriorTopBar
          name={identityName || t("fallbackName")}
          notifications={notifications}
          onMarkRead={markNotificationRead}
          profileHref={"/" + locale + "/cyber-warrior/profile"}
          roleLabel={t("roleLabel")}
        />
      </div>
      <div className="warrior-dashboard-content">
        <div className="warrior-dashboard-header-row">
          <div>
            <h1>{t("welcomeTitle", {name: identityName || t("fallbackName")})}</h1>
            <p>{t("welcomeCopy")}</p>
          </div>
          <div className="warrior-dashboard-header-right">
            <div className="warrior-dashboard-meta">
              <span><strong>{t("warriorId")}:</strong> {warriorCode ?? t("notAvailable")}</span>
              <span>{t("memberSince", {date: profileCreatedAt ? formatDate(profileCreatedAt) : t("notAvailable")})}</span>
            </div>
          </div>
        </div>

        {failedSources.length > 0 ? (
          <div className="warrior-load-error-banner" role="alert">
            <TriangleAlert aria-hidden="true" size={18} />
            <span>{t("loadErrorTitle", {sources: failedSources.join(", ")})}</span>
            <button onClick={() => { setLoading(true); void load(); }} type="button"><RefreshCw aria-hidden="true" size={15} />{t("loadErrorRetry")}</button>
          </div>
        ) : null}

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
            <WarriorCtaIllustration className="warrior-cta-illustration" />
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
          <div className="warrior-status-badge"><Award aria-hidden="true" size={22} /><div><strong>{tierName[progress.tier]}</strong><span>{t("levelLabel", {level: progress.level})}</span></div></div>
          <div className="warrior-xp-track" role="progressbar" aria-label={t("statusTitle")} aria-valuemin={0} aria-valuemax={100} aria-valuenow={progress.percent}><i style={{width: progress.percent + "%"}} /></div>
          <p>{progress.next === null ? tBadges("maxTierLabel") : t("xpCopy", {current: progress.points, total: progress.next})}</p>
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
