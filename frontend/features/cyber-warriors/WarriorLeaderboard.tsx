"use client";

import Link from "next/link";
import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {ChevronLeft, ChevronRight} from "lucide-react";

import {warriorReportsApi} from "@/lib/api/cyber-warriors";
import {getWarriorIdentity, getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {computeBadgeFlags, computeWarriorPoints, mockWarriors, rankTier, type BadgeFlags} from "./warriorReportMeta";

type LeaderboardRow = {name: string; points: number; reportsSubmitted: number; resolvedCount: number; you: boolean; warriorId: string};

function rankTitle(points: number, t: (key: string) => string) {
  const tier = rankTier(points);
  if (tier === "GOLD") return t("rankGold");
  if (tier === "SILVER") return t("rankSilver");
  return t("rankBronze");
}

// Real colorful emoji glyphs instead of monochrome line icons - no icon assets to source, and
// these read as far more "medal-like" at a glance than a flat SVG outline.
const podiumEmoji = ["🥇", "🥈", "🥉"];

// Same 5 badges shown on the Badges & Rewards page, rendered here as small icons only (no
// title/description needed at this size) so a row's real earned badges are visible at a glance.
const badgeIcons: Array<{emoji: string; flag: keyof BadgeFlags; tone: string}> = [
  {emoji: "📝", flag: "starter", tone: "tone-blue"},
  {emoji: "🏆", flag: "active", tone: "tone-green"},
  {emoji: "🛡️", flag: "resolved", tone: "tone-amber"},
  {emoji: "🚀", flag: "rising", tone: "tone-purple"},
  {emoji: "🌟", flag: "elite", tone: "tone-gold"}
];

export function WarriorLeaderboard() {
  const t = useTranslations("warriorLeaderboard");
  const locale = useLocale();
  const router = useRouter();
  const [points, setPoints] = useState(0);
  const [reportsSubmitted, setReportsSubmitted] = useState(0);
  const [resolvedCount, setResolvedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = 5;

  const load = useCallback(async () => {
    const token = getWarriorToken();
    if (!token) {
      router.replace("/" + locale + "/cyber-warrior/verify");
      return;
    }
    const result = await warriorReportsApi.listMine({accessToken: token});
    if (result.ok) {
      setPoints(computeWarriorPoints(result.data));
      setReportsSubmitted(result.data.filter((item) => item.status !== "DRAFT").length);
      setResolvedCount(result.data.filter((item) => item.status === "ACCEPTED").length);
    }
    setLoading(false);
  }, [locale, router]);

  useEffect(() => {
    void load();
  }, [load]);

  if (loading) {
    return <main className="warrior-page"><div className="shell-container warrior-application-loading">{t("loading")}</div></main>;
  }

  const identity = getWarriorIdentity();
  const yourName = identity?.profile.full_name ?? t("you");
  const rows: LeaderboardRow[] = [
    ...mockWarriors.map((row) => ({...row, resolvedCount: 0, you: false})),
    {name: yourName, points, reportsSubmitted, resolvedCount, warriorId: t("yourWarriorId"), you: true}
  ].sort((a, b) => b.points - a.points);
  const yourRank = rows.findIndex((row) => row.you) + 1;
  const yourBadgeFlags = computeBadgeFlags({points, resolvedCount, submittedCount: reportsSubmitted});
  const yourBadgeCount = Object.values(yourBadgeFlags).filter(Boolean).length;
  const podium = rows.slice(0, 3);
  const totalPages = Math.max(1, Math.ceil(rows.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageStart = (currentPage - 1) * pageSize;
  const pageRows = rows.slice(pageStart, pageStart + pageSize);

  return (
    <WarriorShellPage active="leaderboard">
      <div className="warrior-dashboard-content">
        <h1>{t("title")}</h1>
        <p>{t("copy")}</p>

        <div className="warrior-podium-grid">
          {podium.map((row, index) => (
            <div className={"warrior-podium-tile " + (row.you ? "is-you" : "") + " rank-" + (index + 1)} key={row.warriorId}>
              <span className="warrior-podium-rank warrior-podium-ribbon">{index + 1}</span>
              <span className="warrior-podium-badge warrior-emoji-badge" aria-hidden="true">{podiumEmoji[index] ?? "🏅"}</span>
              <strong>{row.you ? t("you") : row.name}</strong>
              <small>{t("points", {count: row.points})}</small>
              <span className="warrior-podium-rank-title">{rankTitle(row.points, t)}</span>
            </div>
          ))}
        </div>

        <section className="warrior-profile-section">
          <h2>{t("topWarriorsTitle")}</h2>
          <div className="warrior-leaderboard-table">
            <div className="warrior-leaderboard-row warrior-leaderboard-head">
              <span>{t("colRank")}</span><span>{t("colName")}</span><span>{t("colPoints")}</span><span>{t("colReports")}</span><span>{t("colBadges")}</span><span>{t("colRankTitle")}</span>
            </div>
            {pageRows.map((row, index) => {
              const flags = computeBadgeFlags({points: row.points, resolvedCount: row.resolvedCount, submittedCount: row.reportsSubmitted});
              const earned = badgeIcons.filter((item) => flags[item.flag]);
              return (
              <div className={"warrior-leaderboard-row " + (row.you ? "is-you" : "")} key={row.warriorId}>
                <span>{pageStart + index + 1}</span>
                <span>{row.you ? t("you") : row.name}</span>
                <span>{row.points}</span>
                <span>{row.reportsSubmitted}</span>
                <span className="warrior-leaderboard-badge-icons">
                  {earned.length ? earned.map(({emoji, flag, tone}) => (
                    <span className={"warrior-mini-badge warrior-emoji-badge " + tone} key={flag}>{emoji}</span>
                  )) : <span className="warrior-status-note-inline">—</span>}
                </span>
                <span>{rankTitle(row.points, t)}</span>
              </div>
              );
            })}
          </div>
          <div className="warrior-leaderboard-pagination">
            <span>{t("showingEntries", {end: Math.min(pageStart + pageSize, rows.length), start: pageStart + 1, total: rows.length})}</span>
            <div className="warrior-pagination-controls">
              <button aria-label={t("previousPage")} disabled={currentPage <= 1} onClick={() => setPage((current) => Math.max(1, current - 1))} type="button"><ChevronLeft aria-hidden="true" size={16} /></button>
              <span>{currentPage} / {totalPages}</span>
              <button aria-label={t("nextPage")} disabled={currentPage >= totalPages} onClick={() => setPage((current) => Math.min(totalPages, current + 1))} type="button"><ChevronRight aria-hidden="true" size={16} /></button>
            </div>
          </div>
          <p className="warrior-status-note">{t("demoDataNote")}</p>
        </section>
      </div>

      <aside className="warrior-dashboard-rail">
        <div className="warrior-status-widget">
          <h2>{t("yourStatsTitle")}</h2>
          <dl className="warrior-mini-stats">
            <div><dt>{t("yourRank")}</dt><dd>{yourRank} / {rows.length}</dd></div>
            <div><dt>{t("totalPoints")}</dt><dd>{points}</dd></div>
            <div><dt>{t("colReports")}</dt><dd>{reportsSubmitted}</dd></div>
            <div><dt>{t("badgesEarned")}</dt><dd>{yourBadgeCount}</dd></div>
          </dl>
        </div>
        <div className="warrior-status-widget">
          <h2>{t("howPointsWorkTitle")}</h2>
          <dl className="warrior-mini-stats">
            <div><dt><span aria-hidden="true">📝</span> {t("pointsSubmitted")}</dt><dd>+5</dd></div>
            <div><dt><span aria-hidden="true">⏳</span> {t("pointsUnderReview")}</dt><dd>+1</dd></div>
            <div><dt><span aria-hidden="true">✅</span> {t("pointsResolved")}</dt><dd>+10</dd></div>
          </dl>
          <Link className="warrior-text-link" href={"/" + locale + "/cyber-warrior/badges"}>{t("viewAllRules")}</Link>
        </div>
      </aside>
    </WarriorShellPage>
  );
}
