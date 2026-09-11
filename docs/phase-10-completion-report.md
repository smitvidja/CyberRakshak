# Phase 10 Completion Report

Secure India, suspect search, real resume parsing, and downloadable complaint copies.

Session reports: [10.1](phase-10-session-10.1.md), [10.2](phase-10-session-10.2.md).
Dataset record: [secure-india-dataset.md](secure-india-dataset.md).

## Final routes and components

```text
/[locale]/secure-india        SecureIndiaDashboard   interactive explorer
/[locale]/suspects/search     SuspectSearch          exact identifier lookup
/[locale]/suspects/report     ReportedSuspectForm    unchanged reporting journey
/[locale]/cyber-warrior/apply/resume + review        real parsing, review-first
/[locale]/complaints/submitted/{number}              complaint copy download
/[locale]/complaints                                 copy download per submitted row
```

The navbar keeps a suspect destination; search and report are both reachable without entering
Secure India.

## Backend APIs added

```text
GET  /secure-india/metadata
GET  /secure-india/summary
POST /suspects/search
POST /suspects/corrections
GET  /admin/suspect-corrections
PATCH /admin/suspect-corrections/{id}/status
GET  /complaints/{id}/copy
```

`POST /complaints/{id}/submit` additionally returns `access_token`, non-null only for anonymous
complaints. `POST /resume/upload` now advertises PDF/DOCX only.

## Migrations

| Revision | Adds |
| --- | --- |
| `a1b2c3d4e5f6` | `reported_suspects.normalized_identifier` + composite index; `suspect_correction_requests` |
| `b2c3d4e5f6a7` | `resume_parsing_results.error_code` |
| `c3d4e5f6a7b8` | `complaint_access_grants` |

All three verified up **and** down on a throwaway database. The container entrypoint runs
`alembic upgrade head` on start, so they apply on deploy with no manual step. The schema is now
24 tables, reconciled in `02-DATABASE.md`.

## Security posture

- **Suspect search**: identifier travels in a request body, exact canonical match only,
  `VERIFIED` reports only, bounded aggregate response, rate limited, no-match never claims
  safety, a match never claims guilt, corrections store an HMAC fingerprint with no reporter
  link.
- **Secure India**: `SecureIndiaService` has no repository and no database access at all, so
  complaint, reporter, location and evidence rows cannot reach the public map by construction.
  Every response is labelled `SYNTHETIC` with version, period and methodology.
- **Complaint copy**: a complaint number opens nothing. Identified access uses owner
  authorization and returns 404 to a stranger; anonymous access uses a separate scoped
  capability stored only as a digest, with no identity column. Wrong, expired, revoked and
  other-complaint codes fail identically. The renderer consumes a sanitized model, so storage
  keys, internal ids, tokens and reporter identity cannot reach a PDF.
- **Resume**: file signature is verified rather than the filename, every path is bounded, no
  macros or embedded content are executed, resume text is data and never instructions, and
  contact details are dropped before persistence.
- Control characters are stripped from citizen text at the API boundary.

## Verification

| Gate | Result |
| --- | --- |
| Backend suite | **332 passed** (from 286 at phase start) |
| Real-browser Secure India | 43/43 at 1280 and 390, both locales |
| Real-browser complaint copy | 11/11, cross-origin |
| Frontend lint / TypeScript / build | clean, 58 static pages |
| EN/HI parity | 0 drift, 0 placeholder mismatches |
| Migrations | clean up and down on a throwaway database |
| Deployment image | built; deps install, fonts present, bilingual PDF renders inside it |

Every new guard was mutation-tested: the assertion was flipped or the behaviour deliberately
broken, and the intended test was confirmed to fail.

## What Phase 10 got wrong first, and how it was caught

Worth recording, because in each case the code looked right and the tests passed:

- **A wrong map of India shipped.** Containment was asserted against the national outline,
  which a distorted outline passes trivially. Replaced with real state geometry and a test that
  asserts each city lands inside its *declared state polygon*.
- **A misplaced coastline put Chennai in the sea**, found by `isPointInFill`, not by eye.
- **Three resume parsing bugs** were invisible until real PDF/DOCX fixtures were generated and
  parsed.
- **Two browser-only defects** (CORS preflight, `Content-Disposition` on a cross-origin fetch)
  passed every backend test, because TestClient bypasses the browser.

The pattern: assert on the property that actually matters, and verify in the environment the
feature will really run in.

## After this report was written

Nine commits landed after the phase was declared complete. None changed scope; all were defects
found by using the product, which is recorded here so this stays an accurate history rather
than a snapshot.

**A deliberate behaviour change, not just a fix.** Cyber Saathi used to re-guess its reply
language from each message, so a citizen who selected English and typed one Devanagari line was
answered in Hinglish, and a single chat could hold all three languages. The rule is now simply
that the selected language is the answer language; detection applies only when nothing has been
selected. This **removed** an earlier intentional behaviour - an English-default chat adopting a
citizen who wrote Hinglish. It helped people who never touched the selector but overrode
everyone who did, and the selector sits directly above the conversation. Two journey tests
encoded the old behaviour and now start in the language the journey is actually conducted in.

Three separate layers decided that language and disagreed, which is why it took three attempts:
the understanding engine, the service resolver, and - the one that mattered in practice - the
message route, which reloads the stored server state for consented conversations and was
overwriting the language the citizen had just chosen. The stored copy stays authoritative for
conversation content; only the language is carried over from the request.

Also landed:

- Chat history is never retranslated on a language switch, and now says so inline at the point
  of the switch. A citizen's own messages become their complaint description, so rewriting them
  would alter the statement they are about to submit.
- A conversation that inherited its language from the page follows the page until the citizen
  picks one in the chat.
- The home page stopped advertising Secure India, suspect search, resume auto-fill and the
  complaint copy as "not built yet" - all four had shipped. The upcoming-features panel was then
  removed entirely.
- Duplicate navigation removed: the header's Citizen Dashboard label (the navbar already has
  one) and a suspect-search quick link that duplicated the navbar item, which was renamed to
  "Check Suspect".
- `allowedDevOrigins` now lists both loopback spellings. The dev server refuses `/_next/*` from
  an origin it does not recognise, and `127.0.0.1` is not allowed by default, so the app served
  HTML while every chunk 403'd and React never hydrated. Production is unaffected.

Backend suite: **332 passed**.

Finally, two items this report had listed as untouched debt were cleared. The frontend
lint script only ever covered `app components lib`, so `features/` - where most of the
product lives - was never linted, which is how eight `react-hooks/set-state-in-effect`
errors accumulated without the repo lint ever going red. The script now includes
`features/`, so the debt cannot return silently. One of the eight was a real defect
(`WarriorDashboard` set state synchronously before its first await); it was fixed rather
than suppressed. The other seven are cases the rule cannot see through - either state set
only after an await, or a mount-time read of browser storage that a lazy initializer would
make disagree with the server snapshot - and each carries a comment saying which it is.
The app also had no icon, so every page requested `/favicon.ico` and got a 404. It now
ships `icon.svg`, `favicon.ico` and `apple-icon.png`, drawn as a simplified form of the
header mark, since the original's thin ring and seven-node iris turn to mush at 16px.

## Known limitations

- Secure India is a synthetic dataset; `source_type` must stay `SYNTHETIC` until the source
  contract in `docs/secure-india-dataset.md` is satisfied.
- Devanagari in generated PDFs renders correctly but is not selectable (fpdf2 fallback-font
  ToUnicode limitation).
- Structured resume parsing is deterministic; the optional hosted-model stage was not added.
- No OCR: an image-only resume returns a controlled error.
- The public rate limiter is in-process and keys on the peer address; behind multiple workers
  or a proxy it needs shared state and proxy-aware client resolution.
- Mumbai and Pune symbols overlap on the map; both remain hoverable, selectable and listed.

## Definition of done

Every item in the Phase 10 prompt's §14 is met, with two boundaries recorded honestly rather
than claimed: Hindi PDFs render correctly but are not text-selectable, and resume structured
parsing ships deterministic-only. All earlier citizen, Cyber Warrior, Cyber Saathi, tracking,
evidence, language-switching and admin-review behaviour still passes.

**Phase 10: COMPLETE.**
