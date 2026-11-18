import assert from "node:assert/strict";
import {beforeEach, test} from "node:test";

import {installBrowserStorage, type MemoryStorage} from "./support/browser-storage";

import {
  clearWarriorSession,
  getWarriorIdentity,
  getWarriorReportDraft,
  setWarriorApplication,
  setWarriorIdentity,
  setWarriorProfileSetup,
  setWarriorReportDraft,
  setWarriorResume,
  setWarriorToken,
} from "../lib/auth/warrior-session";
import {getActiveSession} from "../lib/auth/session-guard";
import {consumeGuestDraftFinalSubmit, markGuestDraftForFinalSubmit} from "../lib/auth/guest-report-session";
import {saveSuspectHandoff, takeSuspectHandoff} from "../lib/suspect-handoff";
import {getComplaintCopyAccess, rememberComplaintCopyAccess} from "../lib/complaint-copy";

let local: MemoryStorage;
let session: MemoryStorage;

beforeEach(() => {
  ({local, session} = installBrowserStorage());
});

const identity = {
  accountEmail: "warrior@example.test",
  demoIdentityId: "99000000000003",
  profile: {full_name: "Rohan Mehta"} as never,
};

test("warrior logout leaves nothing of the warrior behind", () => {
  // Same privacy rule as citizen logout: a shared computer must not show the next person
  // the previous warrior's identity, resume, application or unsent report.
  setWarriorToken("tok");
  setWarriorIdentity(identity);
  setWarriorProfileSetup({city: "Pune", preferredLanguage: "en", profileId: "p1", state: "MH"});
  setWarriorResume({fileName: "cv.pdf", resultId: "r1"});
  setWarriorApplication({application_number: "CWA-1", id: "a1"} as never);
  setWarriorReportDraft({step: 2} as never);
  assert.ok(local.length >= 6);

  clearWarriorSession();
  assert.deepEqual(local.keys().filter((key) => key.startsWith("cyberrakshak.warrior")), []);
});

test("corrupt or incomplete saved warrior data is ignored instead of crashing the page", () => {
  local.setItem("cyberrakshak.warrior-identity", "{not json");
  assert.equal(getWarriorIdentity(), null);
  local.setItem("cyberrakshak.warrior-identity", JSON.stringify({accountEmail: "a@b.c"}));
  assert.equal(getWarriorIdentity(), null);
  local.setItem("cyberrakshak.warrior-report-draft", JSON.stringify({step: "2"}));
  assert.equal(getWarriorReportDraft(), null);
});

test("only one account can be signed in at a time, and the warrior session is seen first", () => {
  assert.equal(getActiveSession(), null);

  setWarriorToken("tok");
  assert.equal(getActiveSession(), null, "a token without an identity is not a session");

  setWarriorIdentity(identity);
  assert.deepEqual(getActiveSession(), {name: "Rohan Mehta", role: "warrior"});
});

test("the guest 'submit after login' flag fires exactly once", () => {
  assert.equal(consumeGuestDraftFinalSubmit(), false);
  markGuestDraftForFinalSubmit();
  assert.equal(consumeGuestDraftFinalSubmit(), true);
  assert.equal(consumeGuestDraftFinalSubmit(), false);
});

test("a suspect search handoff is trimmed, validated and readable only once", () => {
  saveSuspectHandoff({identifierType: "PHONE", identifierValue: "  9876543210  "});
  assert.deepEqual(takeSuspectHandoff(), {identifierType: "PHONE", identifierValue: "9876543210"});
  assert.equal(takeSuspectHandoff(), null);

  saveSuspectHandoff({identifierType: "NOT_A_TYPE", identifierValue: "x"});
  saveSuspectHandoff({identifierType: "EMAIL", identifierValue: "   "});
  assert.equal(takeSuspectHandoff(), null);

  session.setItem("cyberrakshak.suspect-identifier-handoff", JSON.stringify({identifierType: "HACK", identifierValue: "x"}));
  assert.equal(takeSuspectHandoff(), null, "tampered storage is rejected");
});

test("an anonymous complaint's copy capability stays in sessionStorage, keyed by complaint number", () => {
  rememberComplaintCopyAccess("CR-2026-1", {accessToken: "secret-capability", complaintId: "c1"});
  assert.deepEqual(getComplaintCopyAccess("CR-2026-1"), {accessToken: "secret-capability", complaintId: "c1"});
  assert.equal(getComplaintCopyAccess("CR-2026-2"), null);
  assert.equal(local.length, 0, "the capability must never reach localStorage");

  session.setItem("cyberrakshak.complaint-copy-access", "[]");
  assert.equal(getComplaintCopyAccess("CR-2026-1"), null, "a malformed store reads as empty");
});
