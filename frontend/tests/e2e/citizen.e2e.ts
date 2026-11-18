import assert from "node:assert/strict";
import {join} from "node:path";
import {after, before, test} from "node:test";

import type {Browser} from "playwright-core";

import {arriveAt, BASE_URL, button, launch, msg, newJourney, open} from "./support/browser";

/**
 * Citizen journeys in a real browser: what a person actually clicks, end to end,
 * against the real API. Unit and API tests cannot see a broken redirect, a button
 * that never hydrates, or a step that loses the draft between pages.
 */

let browser: Browser;
before(async () => {
  browser = await launch();
});
after(async () => {
  await browser?.close();
});

test("switching to Hindi changes the page language and the navigation, and back again", async () => {
  const {errors, page} = await newJourney(browser);
  await open(page, "/en");
  assert.equal(await page.locator("html").getAttribute("lang"), "en");

  await page.getByRole("link", {exact: true, name: msg("shell.languages.hi")}).first().click();
  await page.waitForURL((url) => url.pathname === "/hi", {timeout: 90_000});
  assert.equal(await page.locator("html").getAttribute("lang"), "hi");
  const hindiNav = await page.locator("nav, header").first().innerText();
  assert.match(hindiNav, /[ऀ-ॿ]/, "the Hindi navigation is written in Devanagari");

  await page.getByRole("link", {exact: true, name: msg("shell.languages.en", "hi")}).first().click();
  await page.waitForURL((url) => url.pathname === "/en", {timeout: 90_000});
  assert.equal(await page.locator("html").getAttribute("lang"), "en");
  assert.deepEqual(errors, []);
});

test("an anonymous complaint can be filed, gets a reference number, and can be tracked with it", async () => {
  const {errors, page} = await newJourney(browser);

  // Entry: anonymous reporting is offered for the women and child safety category.
  await open(page, "/en/report-crime?mode=anonymous&category=women");
  await arriveAt(page, /\/en\/report-crime\/dashboard$/);
  await page.getByRole("heading", {name: msg("citizenEntry.anonymousReadyTitle")}).waitFor();

  // Step 1 - the incident.
  await button(page, msg("citizenEntry.dashboardReportAction")).click();
  await arriveAt(page, /\/report-crime\/new\/incident$/);
  // Category names come from the seeded reference data, not the message files.
  await page.getByRole("button", {name: /women and child safety/i}).first().click();
  await page.getByLabel(msg("complaintDraft.titleLabel")).fill("E2E anonymous - threatening messages");
  await page
    .getByLabel(msg("complaintDraft.descriptionLabel"))
    .fill("An unknown account sent repeated threatening messages over two days. Automated end-to-end test.");
  await button(page, msg("complaintDraft.continuePeople")).click();

  // Step 2 - people involved. The draft now exists server-side, so the URL carries its id.
  await arriveAt(page, /\/report-crime\/[0-9a-f-]{36}\/people$/);
  await button(page, msg("complaintDraft.affectedSelfTitle")).click();
  await button(page, msg("complaintDraft.suspectNo")).click();
  await button(page, msg("complaintDraft.saveContinue")).click();

  // Step 3 - review, declaration, submit.
  await arriveAt(page, /\/report-crime\/[0-9a-f-]{36}\/review$/);
  await page.getByRole("heading", {name: msg("complaintCompletion.title")}).waitFor();
  const submit = button(page, msg("complaintCompletion.submitAction"));
  await page.getByRole("checkbox").first().check();
  await submit.click();

  // Submitted: a reference number the citizen can keep.
  await arriveAt(page, /\/complaints\/submitted\/CR-\d{4}-[0-9A-F]+$/);
  const reference = decodeURIComponent(page.url().split("/").pop() ?? "");
  await page.getByRole("heading", {name: msg("complaintCompletion.submittedTitle")}).waitFor();
  assert.match(await page.locator("main").innerText(), new RegExp(reference));

  // Tracking from scratch, the way someone returning later would: type the number in.
  const tracker = await newJourney(browser);
  await open(tracker.page, "/en/complaints/track");
  await tracker.page.getByLabel(msg("complaintCompletion.referenceLabel")).fill(reference);
  await button(tracker.page, msg("complaintCompletion.trackAction")).click();
  await arriveAt(tracker.page, new RegExp(`/complaints/track/${reference}$`));
  // The page shows a loading panel first; wait for the outcome, whichever it is.
  // exact: the loading panel's title ("Loading complaint status") contains this one.
  const found = tracker.page.getByRole("heading", {exact: true, name: msg("complaintCompletion.trackingTitle")});
  const notFound = tracker.page.getByText(msg("complaintCompletion.trackingErrorTitle"));
  await found.or(notFound).first().waitFor();
  assert.equal(await notFound.count(), 0, "the backend found the complaint by its reference number");
  const tracked = await tracker.page.locator("main").innerText();
  assert.match(tracked, new RegExp(reference), "the tracking page shows the complaint");

  assert.deepEqual([...errors, ...tracker.errors], [], `no console errors on ${BASE_URL}`);
});

test("a verified citizen can file a complaint with evidence and find it under My Reports", async () => {
  const {errors, page} = await newJourney(browser);

  // Verify a synthetic identity (Ananya Shah in DEMO-CREDENTIALS.md).
  await open(page, "/en/report-crime?mode=identified&category=financial");
  await arriveAt(page, /\/en\/report-crime\/verify$/);
  await page.getByLabel(msg("citizenEntry.identityId")).fill("99000000000002");
  await button(page, msg("citizenEntry.sendOtp")).click();
  await page.getByLabel(msg("citizenEntry.otpLabel")).fill("654321");
  await button(page, msg("citizenEntry.verifyContinue")).click();
  await arriveAt(page, /\/en\/report-crime\/dashboard$/);
  await page.getByRole("heading", {name: /Ananya Shah/}).waitFor();

  // Incident with an evidence file. The file is uploaded when the draft is saved:
  // it goes to storage, and only its metadata to the database.
  await button(page, msg("citizenEntry.dashboardReportAction")).click();
  await arriveAt(page, /\/report-crime\/new\/incident$/);
  await page.getByRole("button", {name: /financial fraud/i}).first().click();
  await page.getByLabel(msg("complaintDraft.titleLabel")).fill("E2E identified - UPI collect-request fraud");
  await page
    .getByLabel(msg("complaintDraft.descriptionLabel"))
    .fill("A caller posing as a courier sent a UPI collect request and money was debited. Automated end-to-end test.");
  const evidenceFile = join(process.cwd(), "..", "demo-assets", "resumes", "rohan-mehta-resume.pdf");
  await page.locator("input[type=file]").first().setInputFiles(evidenceFile);
  const uploaded = page.waitForResponse((r) => /\/api\/v1\/evidence$/.test(new URL(r.url()).pathname) && r.request().method() === "POST");
  await button(page, msg("complaintDraft.saveDraft")).click();
  assert.equal((await uploaded).status(), 201, "the evidence upload is accepted");
  await arriveAt(page, /\/report-crime\/[0-9a-f-]{36}\/incident$/);
  await page.getByText("rohan-mehta-resume.pdf").first().waitFor();

  // People, review, submit.
  await button(page, msg("complaintDraft.continuePeople")).click();
  await arriveAt(page, /\/report-crime\/[0-9a-f-]{36}\/people$/);
  await button(page, msg("complaintDraft.affectedSelfTitle")).click();
  await button(page, msg("complaintDraft.suspectNo")).click();
  await button(page, msg("complaintDraft.saveContinue")).click();
  await arriveAt(page, /\/report-crime\/[0-9a-f-]{36}\/review$/);
  await page.getByText("rohan-mehta-resume.pdf").first().waitFor();
  await page.getByRole("checkbox").first().check();
  await button(page, msg("complaintCompletion.submitAction")).click();
  await arriveAt(page, /\/complaints\/submitted\/CR-\d{4}-[0-9A-F]+$/);
  const reference = decodeURIComponent(page.url().split("/").pop() ?? "");

  // A signed-in citizen sees it in their own list.
  await button(page, msg("complaintCompletion.myReportsAction")).click();
  await arriveAt(page, /\/en\/complaints$/);
  await page.getByText(reference).first().waitFor();

  assert.deepEqual(errors, []);
});
