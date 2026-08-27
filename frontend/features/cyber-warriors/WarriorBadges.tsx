"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {warriorReportsApi} from "@/lib/api/cyber-warriors";
import {getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {
  computeRank,
  computeWarriorPoints,
  RANK_GOLD_THRESHOLD,
  RANK_SILVER_THRESHOLD,
  rankTier
} from "./warriorReportMeta";

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

  const badges: Array<{desc: string; earned: boolean; emoji: string; title: string; tone: string}> = [
    {desc: t("badgeStarterCopy"), earned: submittedCount >= 1, emoji: "📝", title: t("badgeStarterTitle"), tone: "tone-blue"},
    {desc: t("badgeActiveCopy"), earned: submittedCount >= 5, emoji: "🏆", title: t("badgeActiveTitle"), tone: "tone-green"},
    {desc: t("badgeResolvedCopy"), earned: resolvedCount >= 1, emoji: "🛡️", title: t("badgeResolvedTitle"), tone: "tone-amber"},
    {desc: t("badgeRisingCopy"), earned: points >= RANK_SILVER_THRESHOLD, emoji: "🚀", title: t("badgeRisingTitle"), tone: "tone-purple"},
    {desc: t("badgeEliteCopy"), earned: points >= RANK_GOLD_THRESHOLD, emoji: "🌟", title: t("badgeEliteTitle"), tone: "tone-gold"}
  ];
  const earnedCount = badges.filter((badge) => badge.earned).length;

  const tier = rankTier(points);
  const {rank, total} = computeRank(points);
  const previousThreshold = tier === "GOLD" ? RANK_GOLD_THRESHOLD : tier === "SILVER" ? RANK_SILVER_THRESHOLD : 0;
  const nextThreshold = tier === "GOLD" ? null : tier === "SILVER" ? RANK_GOLD_THRESHOLD : RANK_SILVER_THRESHOLD;
  const progressPercent = nextThreshold ? Math.min(100, Math.round(((points - previousThreshold) / (nextThreshold - previousThreshold)) * 100)) : 100;
  const tierLabel = tier === "GOLD" ? t("rankGold") : tier === "SILVER" ? t("rankSilver") : t("rankBronze");
  const nextTierLabel = tier === "BRONZE" ? t("rankSilver") : t("rankGold");

  return (
    <WarriorShellPage active="badges">
      <div className="warrior-dashboard-content">
        <h1>{t("title")}</h1>
        <p>{t("copy")}</p>

        <div className="warrior-stat-grid">
          <div className="warrior-stat-tile tone-blue"><span aria-hidden="true" className="warrior-emoji-badge">🎖️</span><strong>{earnedCount}</strong><p>{t("badgesEarnedLabel")}</p></div>
          <div className="warrior-stat-tile tone-purple"><span aria-hidden="true" className="warrior-emoji-badge">⭐</span><strong>{points}</strong><p>{t("totalPointsLabel")}</p></div>
          <div className="warrior-stat-tile tone-gold warrior-stat-tile-level">
            <span aria-hidden="true" className="warrior-emoji-badge">🏅</span>
            <strong>{tierLabel}</strong>
            <p>{t("currentLevelLabel")}</p>
            {nextThreshold ? (
              <>
                <span className="warrior-level-track"><i style={{width: progressPercent + "%"}} /></span>
                <small>{t("nextLevelLabel", {tier: nextTierLabel})} · {points} / {nextThreshold} {t("ptsShort")}</small>
              </>
            ) : <small>{t("maxTierLabel")}</small>}
          </div>
          <div className="warrior-stat-tile tone-green"><span aria-hidden="true" className="warrior-emoji-badge">📈</span><strong>{rank} / {total}</strong><p>{t("rankLabel")}</p></div>
        </div>

        <section className="warrior-profile-section">
          <h2>{t("earnedBadgesTitle")}</h2>
          <div className="warrior-badge-grid">
            {badges.map((badge) => (
              <div className={"warrior-badge-tile " + (badge.earned ? "is-earned " + badge.tone : "is-locked")} key={badge.title}>
                <span className="warrior-badge-icon-wrap warrior-emoji-badge" aria-hidden="true">
                  {badge.emoji}
                  {!badge.earned ? <i className="warrior-badge-lock">🔒</i> : null}
                </span>
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
            <div><dt>{t("pointsSubmitted")}</dt><dd>+5</dd></div>
            <div><dt>{t("pointsUnderReview")}</dt><dd>+1</dd></div>
            <div><dt>{t("pointsResolved")}</dt><dd>+10</dd></div>
          </dl>
        </section>

        <section className="warrior-profile-section">
          <h2>{t("rewardsTitle")}</h2>
          <div className="warrior-reward-grid">
            <div className="warrior-reward-tile">
              <span className="tone-purple warrior-emoji-badge" aria-hidden="true">🎁</span>
              <strong>{t("rewardRecognitionTitle")}</strong>
              <p>{t("rewardRecognitionCopy")}</p>
            </div>
            <div className="warrior-reward-tile">
              <span className="tone-blue warrior-emoji-badge" aria-hidden="true">📜</span>
              <strong>{t("rewardCertificatesTitle")}</strong>
              <p>{t("rewardCertificatesCopy")}</p>
            </div>
            <div className="warrior-reward-tile">
              <span className="tone-green warrior-emoji-badge" aria-hidden="true">✨</span>
              <strong>{t("rewardExclusiveTitle")}</strong>
              <p>{t("rewardExclusiveCopy")}</p>
            </div>
          </div>
          <p className="warrior-status-note">{t("rewardsNote")}</p>
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
