"use client";

import {useCallback, useEffect, useState} from "react";
import {useLocale, useTranslations} from "next-intl";
import {useRouter} from "next/navigation";
import {Award, Medal, Shield, Trophy} from "lucide-react";

import {warriorReportsApi} from "@/lib/api/cyber-warriors";
import {getWarriorIdentity, getWarriorToken} from "@/lib/auth/warrior-session";
import {WarriorShellPage} from "./WarriorAppShell";
import {computeWarriorPoints} from "./warriorReportMeta";

type LeaderboardRow = {name: string; points: number; reportsSubmitted: number; you: boolean; warriorId: string};

// Demo/sample rows so the leaderboard reads as a populated prototype screen. Clearly synthetic -
// this is disclosed to the user; no other real accounts exist to compare against in this build.
const mockWarriors: Array<{name: string; points: number; reportsSubmitted: number; warriorId: string}> = [
  {name: "CW3K8F4D7", points: 1850, reportsSubmitted: 12, warriorId: "CW2405180000078"},
  {name: "CW9M2R6P3", points: 980, reportsSubmitted: 7, warriorId: "CW2405190000112"},
  {name: "CW1L5V8H2", points: 760, reportsSubmitted: 6, warriorId: "CW2405180000356"},
  {name: "CW6P3N7Q4", points: 645, reportsSubmitted: 5, warriorId: "CW2405180000421"},
  {name: "CW2J9T5U6", points: 530, reportsSubmitted: 4, warriorId: "CW2405190000189"},
  {name: "CW4B7G1W8", points: 410, reportsSubmitted: 3, warriorId: "CW2405180000512"},
  {name: "CW8D6Y2Z9", points: 390, reportsSubmitted: 3, warriorId: "CW2405190000305"}
];

function rankTitle(points: number, t: (key: string) => string) {
  if (points >= 1500) return t("rankGold");
  if (points >= 600) return t("rankSilver");
  return t("rankBronze");
}

export function WarriorLeaderboard() {
  const t = useTranslations("warriorLeaderboard");
  const locale = useLocale();
  const router = useRouter();
  const [points, setPoints] = useState(0);
  const [reportsSubmitted, setReportsSubmitted] = useState(0);
  const [loading, setLoading] = useState(true);

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
    ...mockWarriors.map((row) => ({...row, you: false})),
    {name: yourName, points, reportsSubmitted, warriorId: t("yourWarriorId"), you: true}
  ].sort((a, b) => b.points - a.points);
  const yourRank = rows.findIndex((row) => row.you) + 1;
  const podium = rows.slice(0, 3);

  return (
    <WarriorShellPage active="leaderboard">
      <div className="warrior-dashboard-content">
        <h1>{t("title")}</h1>
        <p>{t("copy")}</p>

        <div className="warrior-podium-grid">
          {podium.map((row, index) => (
            <div className={"warrior-podium-tile " + (row.you ? "is-you" : "") + " rank-" + (index + 1)} key={row.warriorId}>
              <span className="warrior-podium-rank">{index + 1}</span>
              <span className="warrior-podium-badge" aria-hidden="true"><Shield size={26} /></span>
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
              <span>{t("colRank")}</span><span>{t("colName")}</span><span>{t("colPoints")}</span><span>{t("colReports")}</span><span>{t("colRankTitle")}</span>
            </div>
            {rows.map((row, index) => (
              <div className={"warrior-leaderboard-row " + (row.you ? "is-you" : "")} key={row.warriorId}>
                <span>{index + 1}</span>
                <span>{row.you ? t("you") : row.name}</span>
                <span>{row.points}</span>
                <span>{row.reportsSubmitted}</span>
                <span>{rankTitle(row.points, t)}</span>
              </div>
            ))}
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
          </dl>
        </div>
        <div className="warrior-status-widget">
          <h2>{t("howPointsWorkTitle")}</h2>
          <dl className="warrior-mini-stats">
            <div><dt><Trophy aria-hidden="true" size={14} /> {t("pointsSubmitted")}</dt><dd>+50</dd></div>
            <div><dt><Medal aria-hidden="true" size={14} /> {t("pointsUnderReview")}</dt><dd>+10</dd></div>
            <div><dt><Award aria-hidden="true" size={14} /> {t("pointsResolved")}</dt><dd>+100</dd></div>
          </dl>
        </div>
      </aside>
    </WarriorShellPage>
  );
}
