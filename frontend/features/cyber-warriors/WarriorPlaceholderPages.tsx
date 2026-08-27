"use client";

import {useTranslations} from "next-intl";

import {WarriorComingSoon, WarriorShellPage, type WarriorNavKey} from "./WarriorAppShell";

function PlaceholderPage({active, descriptionKey, titleKey}: {active: WarriorNavKey; descriptionKey: string; titleKey: string}) {
  const t = useTranslations("warriorDashboard");
  return (
    <WarriorShellPage active={active}>
      <WarriorComingSoon description={t(descriptionKey)} title={t(titleKey)} />
    </WarriorShellPage>
  );
}

export function WarriorMyReportsPlaceholder() {
  return <PlaceholderPage active="myReports" descriptionKey="myReportsComingCopy" titleKey="navMyReports" />;
}

export function WarriorNewReportPlaceholder() {
  return <PlaceholderPage active="myReports" descriptionKey="newReportComingCopy" titleKey="reportCybercrime" />;
}

export function WarriorTrackReportsPlaceholder() {
  return <PlaceholderPage active="trackReports" descriptionKey="trackReportsComingCopy" titleKey="navTrackReports" />;
}

export function WarriorLeaderboardPlaceholder() {
  return <PlaceholderPage active="leaderboard" descriptionKey="leaderboardComingCopy" titleKey="navLeaderboard" />;
}

export function WarriorBadgesPlaceholder() {
  return <PlaceholderPage active="badges" descriptionKey="badgesComingCopy" titleKey="navBadges" />;
}

export function WarriorResourcesPlaceholder() {
  return <PlaceholderPage active="resources" descriptionKey="resourcesComingCopy" titleKey="navResources" />;
}
