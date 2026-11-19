import assert from "node:assert/strict";
import {after, before, test} from "node:test";

import type {Browser} from "playwright-core";

import {button, launch, msg, newJourney, open} from "./support/browser";

/**
 * The administrator console (knowledge gaps) in a real browser.
 *
 * The app never creates administrators, so the run needs one made beforehand with
 * backend/scripts/create_admin.py and its credentials passed in:
 *   E2E_ADMIN_EMAIL, E2E_ADMIN_PASSWORD
 * Without them these journeys are skipped (reported as skipped, not passed).
 */

const EMAIL = process.env.E2E_ADMIN_EMAIL;
const PASSWORD = process.env.E2E_ADMIN_PASSWORD;
const skip = EMAIL && PASSWORD ? false : "set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD (see docs/E2E-TESTING.md)";

let browser: Browser;
before(async () => {
  if (!skip) browser = await launch();
});
after(async () => {
  await browser?.close();
});

const t = (key: string) => msg(`adminKnowledgeGaps.${key}`);

test("a wrong administrator password is refused", {skip}, async () => {
  const {page} = await newJourney(browser);
  await open(page, "/en/admin/knowledge-gaps");
  await page.getByLabel(t("email")).fill(EMAIL!);
  await page.getByLabel(t("password")).fill("definitely-not-the-password");
  await button(page, t("signIn")).click();
  await page.getByText(t("signInFailed")).waitFor();
  assert.equal(await page.getByRole("heading", {name: t("title")}).count(), 0, "the console stays locked");
});

test("an administrator can sign in to the knowledge-gaps console and sign out again", {skip}, async () => {
  const {errors, page} = await newJourney(browser);
  await open(page, "/en/admin/knowledge-gaps");
  await page.getByRole("heading", {name: t("signInTitle")}).waitFor();

  await page.getByLabel(t("email")).fill(EMAIL!);
  await page.getByLabel(t("password")).fill(PASSWORD!);
  await button(page, t("signIn")).click();

  await page.getByRole("heading", {name: t("title")}).waitFor();
  await page.getByLabel(t("statusFilter")).waitFor();

  await button(page, t("signOut")).click();
  await page.getByRole("heading", {name: t("signInTitle")}).waitFor();
  assert.equal(
    await page.evaluate(() => localStorage.getItem("cyberrakshak.admin-token")),
    null,
    "signing out removes the administrator token"
  );
  assert.deepEqual(errors, []);
});

// --- closing a knowledge gap with a reviewed official source ----------------------
// Needs a second administrator (nobody approves their own proposal) and the backend
// URL, to create a real gap through the public Cyber Saathi API first.
const EMAIL2 = process.env.E2E_ADMIN2_EMAIL;
const PASSWORD2 = process.env.E2E_ADMIN2_PASSWORD;
const API_URL = (process.env.E2E_API_URL ?? "http://localhost:8010").replace(/\/$/, "");
const skipLoop = !skip && EMAIL2 && PASSWORD2 ? false : "set both admins: E2E_ADMIN_* and E2E_ADMIN2_* (see docs/E2E-TESTING.md)";
const s = (key: string) => msg(`adminKnowledgeGaps.sources.${key}`);

async function createGap(question: string) {
  const created = await fetch(API_URL + "/api/v1/cyber-saathi/conversations", {
    body: JSON.stringify({language: "EN", storage_consent: true}),
    headers: {"Content-Type": "application/json"},
    method: "POST",
  });
  assert.equal(created.status, 201, "conversation created");
  const state = (await created.json()).data.state;
  const replied = await fetch(`${API_URL}/api/v1/cyber-saathi/conversations/${state.id}/messages`, {
    body: JSON.stringify({message: question, state}),
    headers: {"Content-Type": "application/json"},
    method: "POST",
  });
  assert.equal(replied.status, 200, "question answered (and recorded as a gap)");
}

async function signInAs(page: import("playwright-core").Page, email: string, password: string) {
  await open(page, "/en/admin/knowledge-gaps");
  await page.getByLabel(t("email")).fill(email);
  await page.getByLabel(t("password")).fill(password);
  await button(page, t("signIn")).click();
  await page.getByRole("heading", {name: t("title")}).waitFor();
}

test("an admin proposes an official source for a gap and a different admin approves it", {skip: skipLoop}, async () => {
  const question = "how do I deal with a deepfake video spreading false claims about me";
  await createGap(question);

  // Admin 1 proposes a source for that gap.
  const first = await newJourney(browser);
  await signInAs(first.page, EMAIL!, PASSWORD!);
  const gapRow = first.page.locator("tr, li, [role=row], article").filter({hasText: question}).first();
  await gapRow.getByRole("button", {name: s("proposeAction")}).click();
  // SurfaceCard renders its title in a <div>, not a heading element.
  await first.page.getByText(s("formHeading"), {exact: true}).waitFor();
  await first.page.locator("#source-title").fill("CERT-In advisory on deepfakes");
  await first.page.locator("#source-url").fill("https://www.cert-in.org.in/s2cMainServlet?pageid=PUBVLNOTES02");
  await first.page.locator("#source-type").selectOption("official_public_guidance");
  await first.page.locator("#source-published-on").fill("2026-10-01");
  await first.page.locator("#source-section-title").fill("If a deepfake of you is circulating");
  await first.page.locator("#source-domain-general_cyber_safety").check();
  await first.page.locator("#source-text").fill(
    "Do not engage with or share the fake content. Save the links, screenshots and the date you found them, " +
      "report the content to the platform, and report it at cybercrime.gov.in or by calling 1930."
  );
  const proposed = first.page.waitForResponse((r) => r.url().endsWith("/admin/knowledge-sources") && r.request().method() === "POST");
  await button(first.page, s("submit")).click();
  assert.equal((await proposed).status(), 201, "the proposal is accepted");
  await first.page.getByText(s("proposed")).waitFor();
  // Their own proposal offers no approve button - only the waiting note.
  const ownRow = first.page.locator("tr, li, [role=row], article").filter({hasText: "CERT-In advisory on deepfakes"}).first();
  await ownRow.getByText(s("ownProposal")).waitFor();
  assert.equal(await ownRow.getByRole("button", {name: new RegExp(s("approve"))}).count(), 0);
  assert.deepEqual(first.errors, []);

  // Admin 2 approves it.
  const second = await newJourney(browser);
  await signInAs(second.page, EMAIL2!, PASSWORD2!);
  const pending = second.page.locator("tr, li, [role=row], article").filter({hasText: "CERT-In advisory on deepfakes"}).first();
  await pending.getByRole("button", {name: new RegExp(s("approve"))}).click();
  const reviewed = second.page.waitForResponse((r) => r.url().includes("/admin/knowledge-sources/") && r.request().method() === "PATCH");
  await pending.getByRole("button", {exact: true, name: s("approve")}).click();
  assert.equal((await reviewed).status(), 200, "the second admin's approval is saved");
  await second.page.getByText(s("reviewed").replace("{decision}", "APPROVED")).waitFor();

  await second.page.locator("#source-status-filter").selectOption("APPROVED");
  const approved = second.page.locator("tr, li, [role=row], article").filter({hasText: "CERT-In advisory on deepfakes"}).first();
  await approved.getByText("publish_knowledge_sources").waitFor();
  assert.deepEqual(second.errors, []);
});
