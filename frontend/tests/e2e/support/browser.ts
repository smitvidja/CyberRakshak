/**
 * Shared setup for the browser journeys in tests/e2e/.
 *
 * They drive a real Chrome (headless) against a running frontend + backend:
 *   E2E_BASE_URL   frontend under test       (default http://localhost:3010)
 *   E2E_CHROME     Chrome/Chromium executable (default: the standard Windows install)
 *
 * Point them at a THROWAWAY backend database - the journeys create complaints and
 * use up demo identities. See docs/E2E-TESTING.md for the exact setup.
 */
import {readFileSync} from "node:fs";
import {join} from "node:path";

import {chromium, type Browser, type Page} from "playwright-core";

export const BASE_URL = (process.env.E2E_BASE_URL ?? "http://localhost:3010").replace(/\/$/, "");
const CHROME = process.env.E2E_CHROME ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

// A dev server compiles each route on its first visit, which can take well over ten
// seconds on a small machine. Waits are "until it appears", never fixed sleeps.
export const SLOW = 90_000;

type Messages = {[key: string]: string | Messages};
const catalogs: Record<string, Messages> = {};

/** A UI string from messages/<locale>.json, so a copy change does not break the journeys. */
export function msg(key: string, locale: "en" | "hi" = "en"): string {
  catalogs[locale] ??= JSON.parse(readFileSync(join(process.cwd(), "messages", `${locale}.json`), "utf8")) as Messages;
  const value = key.split(".").reduce<string | Messages | undefined>(
    (node, part) => (node && typeof node === "object" ? node[part] : undefined),
    catalogs[locale]
  );
  if (typeof value !== "string") throw new Error(`No ${locale} message for ${key}`);
  return value;
}

export async function launch(): Promise<Browser> {
  return chromium.launch({
    args: ["--disable-dev-shm-usage", "--disable-gpu", "--no-sandbox"],
    executablePath: CHROME,
    headless: true,
  });
}

export type Journey = {errors: string[]; page: Page};

/** A fresh page (own storage, so journeys never share a session) that records console errors. */
export async function newJourney(browser: Browser): Promise<Journey> {
  const context = await browser.newContext({viewport: {height: 900, width: 1366}});
  const page = await context.newPage();
  page.setDefaultTimeout(SLOW);
  const errors: string[] = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("console", (message) => {
    if (message.type() === "error") errors.push(message.text());
  });
  return {errors, page};
}

/**
 * Open a path and wait until React has hydrated. Clicking a submit button before
 * hydration triggers a native form post that reloads the page and silently wipes
 * what was typed - the single biggest source of flaky journeys in dev mode.
 */
export async function open(page: Page, path: string) {
  await page.goto(BASE_URL + path, {timeout: SLOW, waitUntil: "networkidle"});
  await waitForHydration(page);
}

export async function waitForHydration(page: Page) {
  await page.waitForFunction(
    () => {
      const root = document.querySelector("main") ?? document.body;
      return Object.keys(root).some((key) => key.startsWith("__react"));
    },
    undefined,
    {timeout: SLOW}
  );
}

/** Wait for client-side navigation to a path matching `pattern`, then for hydration. */
export async function arriveAt(page: Page, pattern: RegExp) {
  await page.waitForURL((url) => pattern.test(url.pathname), {timeout: SLOW});
  await page.waitForLoadState("networkidle").catch(() => undefined);
  await waitForHydration(page);
}

export function button(page: Page, name: string) {
  return page.getByRole("button", {name}).first();
}
