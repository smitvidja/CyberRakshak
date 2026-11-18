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

  assert.deepEqual(errors, []);
});
