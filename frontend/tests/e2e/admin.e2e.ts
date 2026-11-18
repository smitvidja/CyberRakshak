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
