import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {join} from "node:path";
import {test} from "node:test";

/**
 * Every screen ships in English and Hindi. A key that exists in only one file shows
 * the raw key (or crashes next-intl) for users of the other language, and nothing
 * else catches it before a user does.
 */

type Messages = {[key: string]: string | Messages};

function load(locale: string): Messages {
  return JSON.parse(readFileSync(join(process.cwd(), "messages", `${locale}.json`), "utf8")) as Messages;
}

function flatten(messages: Messages, prefix = ""): Map<string, string> {
  const out = new Map<string, string>();
  for (const [key, value] of Object.entries(messages)) {
    const path = prefix ? `${prefix}.${key}` : key;
    if (typeof value === "string") out.set(path, value);
    else for (const [k, v] of flatten(value, path)) out.set(k, v);
  }
  return out;
}

const en = flatten(load("en"));
const hi = flatten(load("hi"));

test("English and Hindi define exactly the same message keys", () => {
  const missingInHindi = [...en.keys()].filter((key) => !hi.has(key));
  const missingInEnglish = [...hi.keys()].filter((key) => !en.has(key));
  assert.deepEqual({missingInEnglish, missingInHindi}, {missingInEnglish: [], missingInHindi: []});
});

test("no message is left empty", () => {
  const empty = [...en, ...hi].filter(([, value]) => value.trim() === "").map(([key]) => key);
  assert.deepEqual(empty, []);
});

test("both languages use the same {placeholders} in each message", () => {
  // A Hindi string that drops {name} renders without the user's name; one that invents
  // {nmae} throws at runtime. Either way only Hindi users would see it.
  // Only real arguments: "{name}" or "{count, plural, ...}". The branch text inside a plural
  // ("{No notifications}") is prose, not an argument, and is translated on purpose.
  const placeholders = (value: string) => [...value.matchAll(/\{(\w+)\s*[,}]/g)].map((m) => m[1]).sort();
  const mismatched = [...en.keys()]
    .filter((key) => hi.has(key))
    .filter((key) => placeholders(en.get(key)!).join() !== placeholders(hi.get(key)!).join());
  assert.deepEqual(mismatched, []);
});
