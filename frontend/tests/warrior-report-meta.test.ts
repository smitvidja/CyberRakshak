import assert from "node:assert/strict";
import {test} from "node:test";

import {
  BADGES,
  computeBadgeFlags,
  computeRank,
  computeReportTimeline,
  computeWarriorPoints,
  levelProgress,
  mockWarriors,
  nextTier,
  rankTier,
  RANK_GOLD_THRESHOLD,
  RANK_SILVER_THRESHOLD,
  reportCategories,
  reportCategoryLabelKey,
} from "../features/cyber-warriors/warriorReportMeta";

/**
 * Points, tiers and badges are shown on the dashboard, profile, leaderboard and
 * badges pages. They must agree everywhere, so the rules live in one module and
 * are pinned here.
 */

const states = (status: Parameters<typeof computeReportTimeline>[0]) =>
  computeReportTimeline(status).map((step) => step.state);

test("a draft has not started the tracking timeline", () => {
  assert.deepEqual(states("DRAFT"), ["pending", "pending", "pending", "pending", "pending", "pending"]);
});

test("a submitted report sits at 'under review'", () => {
  for (const status of ["SUBMITTED", "UNDER_REVIEW"] as const) {
    assert.deepEqual(states(status), ["complete", "complete", "current", "pending", "pending", "pending"], status);
  }
});

test("an accepted or rejected report completes every step", () => {
  for (const status of ["ACCEPTED", "REJECTED"] as const) {
    assert.ok(states(status).every((state) => state === "complete"), status);
  }
});

test("points follow the published rules and drafts earn nothing", () => {
  assert.equal(computeWarriorPoints([]), 0);
  assert.equal(computeWarriorPoints([{status: "DRAFT"}]), 0);
  assert.equal(computeWarriorPoints([{status: "SUBMITTED"}]), 6);
  assert.equal(computeWarriorPoints([{status: "UNDER_REVIEW"}]), 6);
  assert.equal(computeWarriorPoints([{status: "ACCEPTED"}]), 15);
  assert.equal(computeWarriorPoints([{status: "REJECTED"}]), 5);
  assert.equal(computeWarriorPoints([{status: "ACCEPTED"}, {status: "SUBMITTED"}, {status: "DRAFT"}]), 21);
});

test("rank tiers switch exactly at their thresholds", () => {
  assert.equal(rankTier(0), "BRONZE");
  assert.equal(rankTier(RANK_SILVER_THRESHOLD - 1), "BRONZE");
  assert.equal(rankTier(RANK_SILVER_THRESHOLD), "SILVER");
  assert.equal(rankTier(RANK_GOLD_THRESHOLD - 1), "SILVER");
  assert.equal(rankTier(RANK_GOLD_THRESHOLD), "GOLD");
});

test("badges are earned only from tracked numbers", () => {
  assert.deepEqual(computeBadgeFlags({points: 0, resolvedCount: 0, submittedCount: 0}), {
    active: false, elite: false, resolved: false, rising: false, starter: false,
  });
  assert.deepEqual(computeBadgeFlags({points: RANK_GOLD_THRESHOLD, resolvedCount: 1, submittedCount: 5}), {
    active: true, elite: true, resolved: true, rising: true, starter: true,
  });
});

test("your rank counts you among the sample warriors", () => {
  const top = Math.max(...mockWarriors.map((row) => row.points));
  assert.deepEqual(computeRank(top + 1), {rank: 1, total: mockWarriors.length + 1});
  assert.deepEqual(computeRank(0), {rank: mockWarriors.length + 1, total: mockWarriors.length + 1});
});

test("each report category has a unique value and an unknown type falls back to 'other'", () => {
  const values = reportCategories.map((item) => item.value);
  assert.equal(new Set(values).size, values.length);
  assert.equal(reportCategoryLabelKey("PHISHING"), "categoryPhishing");
  assert.equal(reportCategoryLabelKey("NOT_A_TYPE" as never), "categoryOther");
});

test("level progress places points inside their tier and points at the next one", () => {
  assert.deepEqual(levelProgress(0), {level: 1, next: RANK_SILVER_THRESHOLD, percent: 0, points: 0, tier: "BRONZE"});
  assert.equal(levelProgress(RANK_SILVER_THRESHOLD / 2).percent, 50);
  const silver = levelProgress(RANK_SILVER_THRESHOLD);
  assert.deepEqual([silver.level, silver.tier, silver.next, silver.percent], [2, "SILVER", RANK_GOLD_THRESHOLD, 0]);
  const gold = levelProgress(RANK_GOLD_THRESHOLD + 500);
  assert.deepEqual([gold.level, gold.tier, gold.next, gold.percent], [3, "GOLD", null, 100]);
});

test("the level always agrees with the rank tier used by the leaderboard", () => {
  for (const points of [0, 1, 6, 59, 60, 61, 149, 150, 151, 999]) {
    assert.equal(levelProgress(points).tier, rankTier(points), `points ${points}`);
  }
  assert.equal(nextTier("BRONZE"), "SILVER");
  assert.equal(nextTier("SILVER"), "GOLD");
  assert.equal(nextTier("GOLD"), null);
});

test("the shared badge list covers every badge flag exactly once", () => {
  const flags = Object.keys(computeBadgeFlags({points: 0, resolvedCount: 0, submittedCount: 0})).sort();
  assert.deepEqual(BADGES.map((badge) => badge.flag).sort(), flags);
  assert.equal(new Set(BADGES.map((badge) => badge.titleKey)).size, BADGES.length);
});

test("point badges announce the same threshold the rule uses", () => {
  // The Rising badge copy once said 50 points while the rule awarded it at 60.
  const byFlag = Object.fromEntries(BADGES.map((badge) => [badge.flag, badge.points]));
  assert.equal(byFlag.rising, RANK_SILVER_THRESHOLD);
  assert.equal(byFlag.elite, RANK_GOLD_THRESHOLD);
  assert.deepEqual(computeBadgeFlags({points: RANK_SILVER_THRESHOLD - 1, resolvedCount: 0, submittedCount: 0}).rising, false);
  assert.deepEqual(computeBadgeFlags({points: RANK_SILVER_THRESHOLD, resolvedCount: 0, submittedCount: 0}).rising, true);
});
