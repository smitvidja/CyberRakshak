# Session 10.2 Completion Report

Real resume parsing/auto-fill + downloadable complaint copy.

## Scope matrix outcome

| Requirement / state | Route / component | API / data boundary | Automated verification | Manual acceptance |
| --- | --- | --- | --- | --- |
| Resume upload | existing Cyber Warrior resume route | object storage + resume API | signature/type/size/ownership tests | PASS - real PDF and DOCX accepted, `.doc` refused honestly |
| Text extraction | `resume_extraction` | bounded PDF/DOCX extraction | 9 extraction tests incl. hostile files | PASS - live upload through uvicorn |
| Structured parsing | `resume_structuring` | validated suggestion shape | mapping/omission/injection tests | PASS - two files give different, file-derived data |
| Review | `WarriorApplicationReview` | persisted untrusted result | ownership/status tests | PASS - every parsed entry editable |
| Confirmed auto-fill | existing profile services | explicit confirmation transaction | multi-entry replace-all test | PASS - mutation-tested |
| Resume failure/retry | upload/review states | typed parser errors | failure-path tests | PASS - profile untouched, reason translated |
| Submitted complaint copy | submitted screen + My Complaints | authorized PDF endpoint | 16 tests | PASS - real browser download |
| Anonymous copy access | anonymous submission | scoped capability, stored hashed | leakage/replay/revocation tests | PASS - no login, number alone fails |
| Identified copy access | authenticated ownership | bearer auth + owner check | 401/404 tests | PASS - another account cannot download |
| PDF rendering | `complaint_pdf_renderer` | sanitized document model | structure/redaction/pagination tests | PASS - rasterised and inspected |
| i18n/accessibility | actions, status, errors | EN/HI namespaces | parity checks | PASS - both locales, no drift |

## Implemented

**Resume (part 1, `d9b1877`)**

- `resume_extraction`: signature-verified, bounded extraction for PDF (pypdf) and DOCX
  (python-docx). Size, page, paragraph, character and decompression-ratio limits. Encrypted,
  empty, image-only and corrupt files map to typed errors with stable codes.
- `resume_structuring`: deterministic section detection and field mapping. Leaves a field
  empty rather than guessing; never emits contact details.
- `DocumentResumeParser` replaces `MockResumeParser` as the runtime parser. The mock survives
  only behind `RESUME_PARSER=mock`, for tests and a labelled demo mode.
- `resume_parsing_results.error_code` (migration `b2c3d4e5f6a7`) so the UI can translate a
  failure reason; a stored English message cannot be shown in Hindi.
- Legacy `.doc` is refused and the UI/API/docs were aligned to PDF/DOCX only.

**Complaint copy (part 2, `39c8c13` + `22c1711`)**

- `GET /complaints/{id}/copy` returning a PDF built from persisted, authorized data.
- `complaint_access_grants` (migration `c3d4e5f6a7b8`): a scoped anonymous capability, stored
  as a SHA-256 digest, bound to one complaint, with expiry and revocation, and no identity
  column of any kind.
- `ComplaintDocumentService` splits authorization from a sanitized view model; the renderer
  never sees a database row.
- `complaint_pdf_renderer`: fpdf2 + uharfbuzz shaping, Noto Sans with Noto Sans Devanagari as
  fallback, embedded and subset.
- Download actions on the submitted screen and each submitted row in My Complaints, plus a
  blob download path on the central API client.

**Review UI (`69a507e`)**

- Education, experience and certifications became repeatable rows with add/remove, following
  the add/update/remove pattern the skills section already used. Experience carries its own
  "currently work here" flag instead of every role being hard-coded `is_current: true`.

## Bugs found and fixed

Five real defects, none of which were visible from reading the code:

1. **Location took an employer line.** "Security Analyst, Aegis Cyber Solutions Pvt Ltd" has
   the same comma shape as "Bengaluru, Karnataka". Found by generating real resume files and
   running the parser on them.
2. **The bio swallowed the location line**, and **a job title was dropped** when the role word
   was missing from the token list. Same method.
3. **A NUL byte in a complaint description crashed the insert** with an unhandled
   `psycopg.DataError` (500). Pre-existing, unrelated to PDFs, found by a hostile-input test.
   Control characters are now stripped at the schema boundary, protecting the existing
   complaint create/update paths.
4. **CORS blocked the anonymous download.** `X-Complaint-Access-Token` is a custom header, so
   it triggers a preflight, and it was not in `allow_headers`. Would have been unreachable
   from the browser in the deployed split-origin topology.
5. **Chrome refuses a cross-origin `fetch()` whose response carries `Content-Disposition`.**
   The server logged 200 and sent the PDF; the browser reported a bare `net::ERR_FAILED`.
   Diagnosed by removing the header and watching the identical request succeed.

Also corrected one regression I introduced myself: narrowing a bare `except Exception` in the
resume upload turned an unexpected parser fault into a 500, violating the contract that a
failure is persisted without touching the profile. The catch-all was restored with a distinct
`RESUME_PARSER_ERROR` code.

## Test results

| Gate | Result |
| --- | --- |
| Backend suite | **328 passed** at the time of writing (was 294; 34 added). Now **332** - see the follow-up section of the phase report. |
| Mutation checks | every new guard flipped and confirmed to fail |
| TypeScript / lint / production build | clean |
| Real-browser complaint copy | **11/11**, cross-origin |
| Secure India regression | **43/43**, unchanged |
| EN/HI parity | 0 drift, 0 placeholder mismatches |
| Migrations | clean up and down on a throwaway database |
| Container check | deps install on `python:3.12-slim`; bilingual PDF renders inside the built image |

## Known limitations

- **Devanagari in a generated PDF renders correctly but cannot be copied out.** fpdf2 emits an
  unreliable ToUnicode map for a *fallback* font under text shaping. Shaping is what makes
  conjuncts and matras correct, so correct-looking Hindi was preferred over selectable text.
  Tested for embedding rather than extraction, and documented rather than hidden.
- `Content-Disposition` is omitted for cors-mode fetches (see above). Non-browser consumers
  still receive it.
- Structured parsing is deterministic only. The optional hosted-model stage described in
  §6.5 was not added; the deterministic path is the required fallback and it is what ships.
- Resume parsing has no OCR, so an image-only PDF returns a controlled "no readable text"
  error rather than pretending to read it.
- The parser is tuned for conventional single-column resumes. Heavily designed multi-column
  layouts will extract in a jumbled order; the review screen is the safeguard.
- Anonymous copy access is bound to one browser session. Losing it means the copy cannot be
  recovered - stated plainly to the citizen rather than solved by attaching identity.

## Deliberately unchanged at the time

- 8 pre-existing `react-hooks/set-state-in-effect` errors in `features/cyber-warriors/*` and an
  app-wide `/favicon.ico` 404. Both predate Phase 10 and were out of scope for this session.
  Both have since been cleared - see the follow-up section of the phase report.

## Gate status

**PASS**
