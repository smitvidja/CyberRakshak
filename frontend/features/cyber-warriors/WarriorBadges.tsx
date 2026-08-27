"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {Award, FileCheck2, Lock, Rocket, ShieldCheck, Star, Trophy} from "lucide-react";

import {warriorReportsApi} from "@/lib/api/cyber-warriors";
import {getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {computeWarriorPoints} from "./warriorReportMeta";

export function WarriorBadges() {
  const t = useTranslations("warriorBadges");
  const locale = useLocale();
  const router = useRouter();
  const [submittedCount, setSubmittedCount] = useState(0);
  const [resolvedCount, setResolvedCount] = useState(0);
  const [points, setPoints] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    const result = await warriorReportsApi.listMine({accessToken: token});
    if (result.ok) {
      setSubmittedCount(result.data.filter((item) => item.status !== "DRAFT").length);
      setResolvedCount(result.data.filter((item) => item.status === "ACCEPTED").length);
      setPoints(computeWarriorPoints(result.data));
    }
    setLoading(false);
  }, [locale, router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loading")}</div></main>;
  }

  const badges = [
    {desc: t("badgeStarterCopy"), earned: submittedCount >= 1, icon: FileCheck2, title: t("badgeStarterTitle")},
    {desc: t("badgeActiveCopy"), earned: submittedCount >= 5, icon: Trophy, title: t("badgeActiveTitle")},
    {desc: t("badgeResolvedCopy"), earned: resolvedCount >= 1, icon: ShieldCheck, title: t("badgeResolvedTitle")},
    {desc: t("badgeRisingCopy"), earned: points >= 500, icon: Rocket, title: t("badgeRisingTitle")},
    {desc: t("badgeEliteCopy"), earned: points >= 1500, icon: Star, title: t("badgeEliteTitle")}
  ];
  const earnedCount = badges.filter((badge) => badge.earned).length;

  return (
    <WarriorShellPage active="badges">
      <div className="warrior-dashboard-content">
        <h1>{t("title")}</h1>
        <p>{t("copy")}</p>

        <div className="warrior-stat-grid">
          <div className="warrior-stat-tile tone-blue"><span aria-hidden="true"><Award size={20} /></span><strong>{earnedCount}</strong><p>{t("badgesEarnedLabel")}</p></div>
          <div className="warrior-stat-tile tone-purple"><span aria-hidden="true"><Star size={20} /></span><strong>{points}</strong><p>{t("totalPointsLabel")}</p></div>
          <div className="warrior-stat-tile tone-green"><span aria-hidden="true"><Trophy size={20} /></span><strong>{submittedCount}</strong><p>{t("reportsSubmittedLabel")}</p></div>
        </div>

        <section className="warrior-profile-section">
          <h2>{t("earnedBadgesTitle")}</h2>
          <div className="warrior-badge-grid">
            {badges.map((badge) => (
              <div className={"warrior-badge-tile " + (badge.earned ? "is-earned" : "is-locked")} key={badge.title}>
                <span aria-hidden="true">{badge.earned ? <badge.icon size={26} /> : <Lock size={22} />}</span>
                <strong>{badge.title}</strong>
                <small>{badge.desc}</small>
                {!badge.earned ? <span className="warrior-badge-locked-note">{t("notYetEarned")}</span> : null}
              </div>
            ))}
          </div>
        </section>

        <section className="warrior-profile-section">
          <h2>{t("howPointsWorkTitle")}</h2>
          <dl className="warrior-profile-fact-grid">
            <div><dt>{t("pointsSubmitted")}</dt><dd>+50</dd></div>
            <div><dt>{t("pointsUnderReview")}</dt><dd>+10</dd></div>
            <div><dt>{t("pointsResolved")}</dt><dd>+100</dd></div>
          </dl>
        </section>
      </div>

      <aside className="warrior-dashboard-rail">
        <div className="warrior-quick-actions">
          <h2>{t("keepGoingTitle")}</h2>
          <p className="warrior-status-hint">{t("keepGoingCopy")}</p>
          <Link className="warrior-text-link" href={"/" + locale + "/cyber-warrior/leaderboard"}>{t("goToLeaderboard")}</Link>
        </div>
      </aside>
    </WarriorShellPage>
  );
}
