import assert from "node:assert/strict";
import {test} from "node:test";

import {CYBER_SAATHI_CONVERSATION_KEY, citizenScopedStorageKeys} from "../lib/auth/citizen-session";

/**
 * Logging out has to leave nothing about the case behind.
 *
 * It used to remove the access token and the identity profile only, so the whole
 * Cyber Saathi conversation, the draft complaint and the evidence filenames all
 * survived. A citizen could log out on a shared computer and the next person
 * would read their case.
 *
 * These assert the LIST the app clears from, imported from the source rather than
 * copied, so a key added later without being registered fails here.
 */
test("logout is responsible for every citizen-scoped storage key", () => {
  const keys = citizenScopedStorageKeys();

  for (const expected of [
    "cyberrakshak.access-token",
    "cyberrakshak.mock-identity-profile",
    "cyberrakshak.complaint-draft",
    "cyberrakshak.complaint-evidence",
    "cyberrakshak.report-mode",
    "cyberrakshak.report-category-hint",
    "cyberrakshak.cyber-saathi.conversation.v2",
    "cyberrakshak.cyber-saathi.report-handoff.v1",
  ]) {
    assert.ok(keys.includes(expected), `logout must clear ${expected}`);
  }
});

test("the conversation key the composer uses is the one logout clears", () => {
  // The bug was possible because the key lived in a component constant that
  // logout could not see. If those ever drift apart again, the leak returns.
  assert.ok(
    citizenScopedStorageKeys().includes(CYBER_SAATHI_CONVERSATION_KEY),
    "the Cyber Saathi conversation must be cleared by logout"
  );
});

test("every registered key is namespaced, so the list cannot quietly grow wrong", () => {
  for (const key of citizenScopedStorageKeys()) {
    assert.match(key, /^cyberrakshak\./);
  }
});
