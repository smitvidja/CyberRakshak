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
| Backend suite | 328 passed (from 286 at phase start) |
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
- Pre-existing and untouched: 8 lint errors in `features/cyber-warriors/*`, app-wide favicon 404.

## Definition of done

Every item in the Phase 10 prompt's §14 is met, with two boundaries recorded honestly rather
than claimed: Hindi PDFs render correctly but are not text-selectable, and resume structured
parsing ships deterministic-only. All earlier citizen, Cyber Warrior, Cyber Saathi, tracking,
evidence, language-switching and admin-review behaviour still passes.

**Phase 10: COMPLETE.**
