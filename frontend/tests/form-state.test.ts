import assert from "node:assert/strict";
import {test} from "node:test";

import {errorMessageKey, toFormErrorState} from "../lib/utils/form-state";

test("every known API error code maps to its own translated message", () => {
  assert.equal(errorMessageKey({code: "UNAUTHORIZED"}), "apiErrors.unauthorized");
  assert.equal(errorMessageKey({code: "FORBIDDEN"}), "apiErrors.forbidden");
  assert.equal(errorMessageKey({code: "NOT_FOUND"}), "apiErrors.notFound");
  assert.equal(errorMessageKey({code: "VALIDATION_ERROR"}), "apiErrors.validation");
  assert.equal(errorMessageKey({code: "NETWORK_ERROR"}), "apiErrors.network");
  assert.equal(errorMessageKey({code: "SERVER_ERROR"}), "apiErrors.server");
  assert.equal(errorMessageKey({code: "SOMETHING_NEW"}), "apiErrors.unknown");
});

test("field errors are shown next to their fields, with no extra form-level banner", () => {
  const state = toFormErrorState({code: "VALIDATION_ERROR", details: {email: "Invalid", phone: "Too short"}});
  assert.deepEqual(state, {fieldErrors: {email: "Invalid", phone: "Too short"}, formErrorKey: undefined});
});

test("non-string details are dropped rather than rendered as [object Object]", () => {
  const state = toFormErrorState({code: "VALIDATION_ERROR", details: {nested: {a: 1}, count: 3}});
  assert.deepEqual(state, {fieldErrors: {}, formErrorKey: "apiErrors.validation"});
});

test("an error without field details falls back to a form-level message", () => {
  assert.deepEqual(toFormErrorState({code: "NETWORK_ERROR"}), {fieldErrors: {}, formErrorKey: "apiErrors.network"});
});
