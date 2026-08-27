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
// +50, Report Under Review +10, Report Resolved +100). Applied consistently everywhere a "points"
// figure is shown (dashboard-adjacent widgets, profile, leaderboard, badges) so the number means
// the same thing in every place it appears, computed only from real report data - never a fixed
// mock constant.
export function computeWarriorPoints(reports: {status: string}[]): number {
  return reports.reduce((total, report) => {
    if (report.status === "DRAFT") return total;
    if (report.status === "ACCEPTED") return total + 150;
    if (report.status === "REJECTED") return total + 50;
    return total + 60; // SUBMITTED or UNDER_REVIEW: submitted (+50) plus under-review (+10)
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
