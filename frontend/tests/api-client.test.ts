import assert from "node:assert/strict";
import {afterEach, test} from "node:test";

import {buildApiUrl, createApiClient} from "../lib/api/client";

/**
 * Every screen talks to the backend through this client, so a mistake here shows
 * up everywhere at once: a success read as a failure, a 401 that no longer sends
 * the user to log in, or a token that silently stops being attached.
 */

type Captured = {init: RequestInit; url: string};
const realFetch = globalThis.fetch;

function stubFetch(respond: () => Response | Promise<Response>) {
  const calls: Captured[] = [];
  globalThis.fetch = (async (url: string | URL | Request, init: RequestInit = {}) => {
    calls.push({init, url: String(url)});
    return respond();
  }) as typeof fetch;
  return calls;
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {headers: {"Content-Type": "application/json"}, status});
}

afterEach(() => {
  globalThis.fetch = realFetch;
});

test("buildApiUrl joins base, version prefix and path without doubled slashes", () => {
  assert.equal(buildApiUrl("/complaints", "http://api.test/"), "http://api.test/api/v1/complaints");
  assert.equal(buildApiUrl("complaints", "http://api.test"), "http://api.test/api/v1/complaints");
});

test("a missing API base URL fails loudly instead of calling a relative URL", () => {
  assert.throws(() => buildApiUrl("/x", ""), /NEXT_PUBLIC_API_URL/);
  assert.throws(() => createApiClient(""), /NEXT_PUBLIC_API_URL/);
});

test("a success envelope returns its data", async () => {
  stubFetch(() => json({data: {id: "c1"}, message: "ok", success: true}));
  const result = await createApiClient("http://api.test").get<{id: string}>("/complaints/c1");
  assert.deepEqual(result, {data: {id: "c1"}, message: "ok", ok: true});
});

test("a 204 with no body is a success, not a failure", async () => {
  // Deleting evidence or a warrior report returns no body; it used to be reported as failed.
  stubFetch(() => new Response(null, {status: 204}));
  const result = await createApiClient("http://api.test").delete("/evidence/e1");
  assert.equal(result.ok, true);
});

test("the backend's own error code and field details are passed through", async () => {
  stubFetch(() => json({error: {code: "VALIDATION_ERROR", details: {email: "Invalid email"}}, success: false}, 422));
  const result = await createApiClient("http://api.test").post("/x", "{}");
  assert.deepEqual(result, {error: {code: "VALIDATION_ERROR", details: {email: "Invalid email"}, status: 422}, ok: false});
});

test("HTTP status picks a sensible code when the body has none", async () => {
  for (const [status, code] of [
    [401, "UNAUTHORIZED"],
    [403, "FORBIDDEN"],
    [404, "NOT_FOUND"],
    [503, "SERVER_ERROR"],
    [418, "UNKNOWN_ERROR"],
  ] as const) {
    stubFetch(() => new Response("not json", {status}));
    const result = await createApiClient("http://api.test").get("/x");
    assert.equal(result.ok, false);
    assert.equal(!result.ok && result.error.code, code, `status ${status}`);
  }
});

test("a network failure becomes NETWORK_ERROR instead of an unhandled rejection", async () => {
  stubFetch(() => {
    throw new TypeError("fetch failed");
  });
  const result = await createApiClient("http://api.test").get("/x");
  assert.deepEqual(result, {error: {code: "NETWORK_ERROR"}, ok: false});
});

test("the access token travels as a Bearer header and JSON bodies are labelled", async () => {
  const calls = stubFetch(() => json({data: null, success: true}));
  await createApiClient("http://api.test").post("/x", JSON.stringify({a: 1}), {accessToken: "tok"});
  const headers = new Headers(calls[0].init.headers);
  assert.equal(headers.get("Authorization"), "Bearer tok");
  assert.equal(headers.get("Content-Type"), "application/json");
  assert.equal(calls[0].init.credentials, "include");
});

test("a FormData upload keeps the browser-set multipart Content-Type", async () => {
  // Forcing application/json here would strip the multipart boundary and break evidence upload.
  const calls = stubFetch(() => json({data: null, success: true}));
  await createApiClient("http://api.test").post("/evidence", new FormData());
  assert.equal(new Headers(calls[0].init.headers).has("Content-Type"), false);
});

test("download returns the file as a Blob, and errors keep the normal envelope shape", async () => {
  stubFetch(() => new Response("%PDF-1.7", {status: 200}));
  const ok = await createApiClient("http://api.test").download("/complaints/c1/copy");
  assert.equal(ok.ok, true);
  assert.equal(ok.ok && (await ok.data.text()), "%PDF-1.7");

  stubFetch(() => json({error: {code: "COMPLAINT_ACCESS_DENIED"}, success: false}, 403));
  const denied = await createApiClient("http://api.test").download("/complaints/c1/copy");
  assert.equal(!denied.ok && denied.error.code, "COMPLAINT_ACCESS_DENIED");
});
