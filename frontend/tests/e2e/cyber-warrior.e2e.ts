import assert from "node:assert/strict";
import {join} from "node:path";
import {after, before, test} from "node:test";

import type {Browser, Page} from "playwright-core";

import {arriveAt, button, launch, msg, newJourney, open} from "./support/browser";

/**
 * The Cyber Warrior onboarding in a real browser: synthetic identity + OTP, profile,
 * resume upload and extraction, human review of the extracted data, application.
 *
 * Uses demo identities from DEMO-CREDENTIALS.md. Each completed run registers that
 * identity, so run against a throwaway database (docs/E2E-TESTING.md).
 */

const RESUMES = join(process.cwd(), "..", "demo-assets", "resumes");

let browser: Browser;
before(async () => {
  browser = await launch();
});
after(async () => {
  await browser?.close();
});

async function verifyIdentity(page: Page, identity: string, otp: string) {
  await open(page, "/en/cyber-warrior/verify");
  await page.getByLabel(msg("warriorOnboarding.identityLabel")).fill(identity);
  await button(page, msg("warriorOnboarding.requestOtp")).click();
  await page.getByLabel(msg("warriorOnboarding.otpLabel")).fill(otp);
  await button(page, msg("warriorOnboarding.verifyAction")).click();
}

test("a wrong demo OTP is refused and the applicant stays on the verify step", async () => {
  const {page} = await newJourney(browser);
  await verifyIdentity(page, "99000000000005", "000000");
  await page.getByRole("alert").or(page.locator("[aria-invalid=true]")).first().waitFor();
  assert.match(new URL(page.url()).pathname, /\/cyber-warrior\/verify$/);
});

test("a new applicant can verify, set up a profile, upload a resume, review it and apply", async () => {
  const {errors, page} = await newJourney(browser);

  // Verify the synthetic identity with its demo OTP (Rohan Mehta in DEMO-CREDENTIALS.md).
  await verifyIdentity(page, "99000000000003", "111222");
  await arriveAt(page, /\/cyber-warrior\/verify\/profile$/);

  // Profile.
  await page.getByLabel(msg("warriorOnboarding.state"), {exact: false}).fill("Maharashtra");
  await page.getByLabel(msg("warriorOnboarding.city"), {exact: false}).fill("Pune");
  await button(page, msg("warriorOnboarding.saveProfile")).click();
  await arriveAt(page, /\/cyber-warrior\/apply\/resume$/);

  // Resume upload and extraction.
  await page.locator("input[type=file]").first().setInputFiles(join(RESUMES, "rohan-mehta-resume.pdf"));
  const upload = page.waitForResponse((r) => r.url().includes("/resume/upload") && r.request().method() === "POST");
  await button(page, msg("warriorApplication.uploadAction")).click();
  assert.equal((await upload).status(), 201, "the resume upload is accepted");
  await button(page, msg("warriorApplication.continueDetails")).click();
  await arriveAt(page, /\/cyber-warrior\/apply\/review$/);

  // Review: extraction is only a suggestion, but from a well-formed resume it must
  // arrive complete. It used to split a degree from its institution and read job
  // descriptions as employers, leaving required fields the applicant had to repair.
  const displayName = page.getByLabel(/Display name/);
  await displayName.waitFor();
  assert.notEqual(await displayName.inputValue(), "", "the display name is pre-filled from the verified identity");
  const empty: string[] = [];
  for (const field of await page.locator("input[required], textarea[required]").all()) {
    if ((await field.inputValue()).trim() === "") empty.push((await field.getAttribute("id")) ?? "?");
  }
  assert.deepEqual(empty, [], "every required field is filled from the resume");
  assert.equal(await page.getByLabel(/Institution/).first().inputValue(), "Savitribai Phule Pune University");
  assert.equal(await page.getByLabel(/Organization/).first().inputValue(), "Sentinel InfoTech");
  await button(page, msg("warriorApplication.reviewAction")).click();

  // Final confirmation: submitting is impossible until the declaration is ticked.
  const submit = button(page, msg("warriorApplication.submitAction"));
  await submit.waitFor();
  assert.equal(await submit.isDisabled(), true, "submit stays disabled until the declaration is accepted");
  await page.getByRole("checkbox").last().check();
  await submit.click();

  await arriveAt(page, /\/cyber-warrior\/apply\/submitted$/);
  await page.getByRole("heading", {name: msg("warriorApplication.submittedTitle")}).waitFor();

  // The same signed-in warrior files a report: category, description, evidence, review.
  await open(page, "/en/cyber-warrior/reports/new");
  await button(page, msg("warriorReport.categoryPhishing")).click();
  await button(page, msg("warriorReport.nextDescribe")).click();
  await page.getByLabel(msg("warriorReport.incidentDateLabel")).fill("2026-11-01");
  const platform = page.getByLabel(msg("warriorReport.platformLabel"));
  if ((await platform.evaluate((el) => el.tagName)) === "SELECT") {
    await platform.selectOption({index: 1});
  } else {
    await platform.fill("Email");
  }
  await page
    .getByLabel(msg("warriorReport.descriptionLabel"))
    .fill("A phishing email imitating a bank asked for card details via a look-alike domain. Automated end-to-end test.");
  const draftSaved = page.waitForResponse((r) => r.url().includes("/warrior-reports") && ["POST", "PATCH"].includes(r.request().method()));
  await button(page, msg("warriorReport.nextEvidence")).click();
  assert.ok((await draftSaved).ok(), "the report draft is saved before the evidence step");
  await button(page, msg("warriorReport.nextReview")).click();

  const submitReport = button(page, msg("warriorReport.submitReportAction"));
  await submitReport.waitFor();
  assert.equal(await submitReport.isDisabled(), true, "a report cannot be submitted without the declaration");
  await page.getByRole("checkbox").last().check();
  await submitReport.click();

  await arriveAt(page, /\/cyber-warrior\/reports\/[0-9a-f-]{36}\/submitted$/);
  await page.getByRole("heading", {name: msg("warriorReport.submittedTitle")}).waitFor();

  // Profile: a real, server-assigned Warrior ID (not the application number).
  await open(page, "/en/cyber-warrior/profile");
  const factGrid = page.locator(".warrior-profile-fact-grid").first();
  await factGrid.waitFor();
  const warriorId = (await factGrid.innerText()).match(/CW\d{13}/)?.[0];
  assert.ok(warriorId, "the profile shows a Warrior ID like CW2611190000001");

  // Availability & Preferences: edit, save, and it survives a reload.
  await page.getByRole("button", {name: msg("warriorProfile.editPreferencesLabel")}).click();
  // By id: SelectField wraps the <select> inside its <label>, so the label text includes
  // every option and a label match is ambiguous (the section is labelled too).
  await page.locator("#warrior-availability").selectOption("10_TO_15");
  await page.locator("#warrior-willing").selectOption("yes");
  await page.locator("#warrior-task-REPORT_REVIEW").check();
  await page.locator("#warrior-task-EVIDENCE_ANALYSIS").check();
  await page.locator("#warrior-channel-EMAIL").check();
  const saved = page.waitForResponse((r) => r.url().includes("/cyber-warriors/me") && r.request().method() === "PATCH");
  await button(page, msg("warriorProfile.savePreferences")).click();
  assert.equal((await saved).status(), 200, "the preferences are saved");
  await page.getByText(msg("warriorProfile.preferencesSaved")).waitFor();

  await page.reload({waitUntil: "networkidle"});
  const availability = page.locator("section", {has: page.getByRole("heading", {name: msg("warriorProfile.availabilityTitle")})});
  await availability.waitFor();
  const shown = await availability.innerText();
  for (const expected of [
    msg("warriorProfile.availabilityOptions.10_TO_15"),
    msg("warriorProfile.taskOptions.REPORT_REVIEW"),
    msg("warriorProfile.taskOptions.EVIDENCE_ANALYSIS"),
    msg("warriorProfile.communicationOptions.EMAIL"),
    msg("warriorProfile.yes"),
  ]) {
    assert.ok(shown.includes(expected), `after a reload the profile still shows "${expected}"`);
  }

  // Dashboard: the same Warrior ID, and a Warrior Status computed from the one submitted
  // report (6 points -> Bronze, level 1, 6 of the 60 needed for Silver) - not "0 XP".
  await open(page, "/en/cyber-warrior/dashboard");
  await page.getByText(warriorId).first().waitFor();
  const status = page.locator(".warrior-status-widget").first();
  const statusText = await status.innerText();
  assert.ok(statusText.includes(msg("warriorBadges.rankBronze")), statusText);
  assert.ok(statusText.includes(msg("warriorDashboard.levelLabel").replace("{level}", "1")), statusText);
  assert.ok(statusText.includes(msg("warriorDashboard.xpCopy").replace("{current}", "6").replace("{total}", "60")), statusText);

  assert.deepEqual(errors, []);
});
