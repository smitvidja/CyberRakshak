import {
  Bug,
  Fingerprint,
  IndianRupee,
  Megaphone,
  ShieldAlert,
  ShieldQuestion,
  Sparkles,
  type LucideIcon
} from "lucide-react";

import type {WarriorReportStatus, WarriorReportType} from "@/lib/api/cyber-warriors";

export type ReportCategoryMeta = {icon: LucideIcon; labelKey: string; noteKey: string; value: WarriorReportType};

// The design reference (Step 6) shows 9 category tiles (Financial Fraud, Identity Theft, Online
// Harassment, Phishing/Scam, Malware/Virus, Fake News/Misinformation, Child Exploitation, Cyber
// Terrorism, Other). The backend's WarriorReportType enum only has 7 values and does not include
// Identity Theft, Child Exploitation, or Cyber Terrorism specifically. Rather than silently mapping
// a sensitive category (e.g. Child Exploitation) onto an unrelated enum value, this list uses the
// 7 real enum values with honest labels that cover the same ground where possible.
export const reportCategories: ReportCategoryMeta[] = [
  {icon: IndianRupee, labelKey: "categoryScam", noteKey: "categoryScamNote", value: "SCAM"},
  {icon: Fingerprint, labelKey: "categoryPhishing", noteKey: "categoryPhishingNote", value: "PHISHING"},
  {icon: Bug, labelKey: "categoryMalware", noteKey: "categoryMalwareNote", value: "MALWARE"},
  {icon: ShieldAlert, labelKey: "categoryThreat", noteKey: "categoryThreatNote", value: "THREAT"},
  {icon: ShieldQuestion, labelKey: "categoryVulnerability", noteKey: "categoryVulnerabilityNote", value: "VULNERABILITY"},
  {icon: Megaphone, labelKey: "categoryOsint", noteKey: "categoryOsintNote", value: "OSINT"},
  {icon: Sparkles, labelKey: "categoryOther", noteKey: "categoryOtherNote", value: "OTHER"}
];

export function reportCategoryLabelKey(type: WarriorReportType): string {
  return reportCategories.find((item) => item.value === type)?.labelKey ?? "categoryOther";
}

export type TimelineStepState = "complete" | "current" | "pending";
export type TimelineStep = {key: string; state: TimelineStepState};

// The backend has no admin/reviewer flow yet to move a report past SUBMITTED, so in practice a
// submitted report stays at "under review" indefinitely in this prototype - matching the design's
// own perpetual "Under Review" state. Investigation/Action & Resolution/Closed only ever complete
// if a future admin path sets ACCEPTED or REJECTED.
export function computeReportTimeline(status: WarriorReportStatus): TimelineStep[] {
  const resolved = status === "ACCEPTED" || status === "REJECTED";
  const submitted = status !== "DRAFT";
  return [
    {key: "timelineSubmitted", state: submitted ? "complete" : "pending"},
    {key: "timelineAcknowledged", state: submitted ? "complete" : "pending"},
    {key: "timelineUnderReview", state: resolved ? "complete" : submitted ? "current" : "pending"},
    {key: "timelineInvestigation", state: resolved ? "complete" : "pending"},
    {key: "timelineAction", state: resolved ? "complete" : "pending"},
    {key: "timelineClosed", state: resolved ? "complete" : "pending"}
  ];
}

// Mirrors the point rules shown on the Badges & Rewards / Leaderboard screens (Report Submitted
// +5, Report Under Review +1, Report Resolved +10). Applied consistently everywhere a "points"
// figure is shown (dashboard-adjacent widgets, profile, leaderboard, badges) so the number means
// the same thing in every place it appears, computed only from real report data - never a fixed
// mock constant.
export function computeWarriorPoints(reports: {status: string}[]): number {
  return reports.reduce((total, report) => {
    if (report.status === "DRAFT") return total;
    if (report.status === "ACCEPTED") return total + 15;
    if (report.status === "REJECTED") return total + 5;
    return total + 6; // SUBMITTED or UNDER_REVIEW: submitted (+5) plus under-review (+1)
  }, 0);
}

export function reportStatusToneClass(status: WarriorReportStatus): string {
  switch (status) {
    case "ACCEPTED": return "tone-green";
    case "REJECTED": return "tone-red";
    case "UNDER_REVIEW": return "tone-blue";
    case "SUBMITTED": return "tone-blue";
    default: return "tone-muted";
  }
}

// Rank tiers share the same thresholds used to color the leaderboard podium/table and the
// "Current Level" progress widget on Badges & Rewards, so a warrior's tier always means the same
// thing everywhere it's shown.
export type RankTier = "BRONZE" | "GOLD" | "SILVER";
export const RANK_SILVER_THRESHOLD = 60;
export const RANK_GOLD_THRESHOLD = 150;

export function rankTier(points: number): RankTier {
  if (points >= RANK_GOLD_THRESHOLD) return "GOLD";
  if (points >= RANK_SILVER_THRESHOLD) return "SILVER";
  return "BRONZE";
}

// Which of the 5 Badges & Rewards badges are earned, given only fields that are actually tracked
// (report counts and computed points). Shared by the Badges page and the Leaderboard's "Badges"
// column so both surfaces agree on who has earned what. resolvedCount is only known for the real
// signed-in warrior - demo/mock leaderboard rows pass 0, so they never claim the "Case Closer"
// badge without real evidence for it.
export type BadgeFlags = {active: boolean; elite: boolean; resolved: boolean; rising: boolean; starter: boolean};

export function computeBadgeFlags(input: {points: number; resolvedCount: number; submittedCount: number}): BadgeFlags {
  return {
    active: input.submittedCount >= 5,
    elite: input.points >= RANK_GOLD_THRESHOLD,
    resolved: input.resolvedCount >= 1,
    rising: input.points >= RANK_SILVER_THRESHOLD,
    starter: input.submittedCount >= 1
  };
}

// Demo/sample leaderboard rows so the leaderboard and rank comparisons read as a populated
// prototype screen. Clearly synthetic - disclosed to the user; no other real accounts exist to
// compare against in this build. Shared between the Leaderboard and Badges pages so "your rank"
// means the same position in both places.
export type MockWarriorRow = {name: string; points: number; reportsSubmitted: number; warriorId: string};
export const mockWarriors: MockWarriorRow[] = [
  {name: "CW3K8F4D7", points: 185, reportsSubmitted: 12, warriorId: "CW2405180000078"},
  {name: "CW9M2R6P3", points: 98, reportsSubmitted: 7, warriorId: "CW2405190000112"},
  {name: "CW1L5V8H2", points: 76, reportsSubmitted: 6, warriorId: "CW2405180000356"},
  {name: "CW6P3N7Q4", points: 65, reportsSubmitted: 5, warriorId: "CW2405180000421"},
  {name: "CW2J9T5U6", points: 53, reportsSubmitted: 4, warriorId: "CW2405190000189"},
  {name: "CW4B7G1W8", points: 41, reportsSubmitted: 3, warriorId: "CW2405180000512"},
  {name: "CW8D6Y2Z9", points: 39, reportsSubmitted: 3, warriorId: "CW2405190000305"}
];

export function computeRank(points: number): {rank: number; total: number} {
  const allPoints = [...mockWarriors.map((row) => row.points), points].sort((a, b) => b - a);
  return {rank: allPoints.indexOf(points) + 1, total: allPoints.length};
}
