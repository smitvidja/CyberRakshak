# PHASE 10 — SECURE INDIA, SUSPECT SEARCH & WORKFLOW COMPLETION
## Interactive Cyber-Risk Explorer • Safe Identifier Search • Real Resume Parsing • Auto-Fill • Downloadable Complaint Copy

**Status:** Master implementation prompt  
**Execution model:** Two sessions. Codex must implement, test, verify, document, and hand off Session 10.1 before beginning Session 10.2.  
**Primary goal:** Replace the remaining Phase 9 preview/planned boundaries with two coherent, safe, bilingual citizen workflows while preserving every completed CyberRakshak journey.

---

# 0. APPROVED SESSION SPLIT

Phase 10 is intentionally limited to two sessions:

1. **Session 10.1 — Interactive Secure India + Search Suspect Reports**
   - Turn the current Secure India screenshot preview into an interactive, data-backed prototype.
   - Integrate safe suspect-identifier search into Secure India as a contextual feature.
   - Keep a dedicated suspect destination in the main navbar. Integration does **not** mean removing or hiding suspect search/reporting from navigation.

2. **Session 10.2 — Real Resume Parsing/Auto-Fill + Downloadable Complaint Copy**
   - Replace the static Cyber Warrior resume parser with real, review-first extraction and auto-fill.
   - Add a secure downloadable complaint copy for submitted complaints, with correct identified/anonymous access boundaries.

Do not split either workflow into a disconnected demo. Each session must include UI, API, validation, business logic, persistence where required, tests, security, accessibility, responsive verification, and documentation.

---

# 1. PHASE ENTRY GATE

Before implementing Session 10.1:

1. Read `AGENTS.md`, `PROJECT-STRUCTURE.md`, `SKILLS.md`, and the relevant architecture/design documents selected through `SKILLS.md`.
2. Read `docs/phase-9-operating-memory.md`, `docs/phase-9-session-9.6.md`, and `docs/phase-9-completion-report.md`.
3. Confirm the Phase 9 owner physical check for the 60-second voice limit and `Finish & send` interaction is recorded as passed, or explicitly record the owner's decision to waive/defer that physical-only check. Do not silently erase the gate.
4. Inspect the working tree and preserve all existing user changes.
5. Inspect current routes, API clients, models, services, tests, i18n, auth/session helpers, and shared components before proposing new layers.
6. Inspect all three existing design folders as required by `AGENTS.md`. For Session 10.1, also treat the saved Secure India mockup at `frontend/public/images/awareness/secure-india-preview-v1.webp` and the current preview composition as the primary feature reference.
7. Create a session scope matrix mapping requirement/state → route/component → API/data boundary → automated test → manual acceptance.

Do not begin Session 10.2 until Session 10.1 has a genuine PASS gate.

---

# 2. CURRENT REPOSITORY BASELINE

Phase 10 must evolve the current implementation rather than replace it.

## 2.1 Secure India baseline

- Public route: `/[locale]/secure-india`.
- Current implementation is a server-rendered preview composed of four feature-description cards, a clearly labelled mock screenshot, a learning-resources CTA, and a safety note.
- The screenshot depicts the intended information hierarchy: hero metrics, filters, a geographic crime map, rankings, hot zones, hot crimes, a reporting CTA, and a learning corner.
- The current numbers are invented. They must never be re-presented as current, government, police, or verified national data.

## 2.2 Reported suspect baseline

- Existing dedicated route: `/[locale]/suspects/report`.
- Existing APIs support creating an authenticated suspect report, listing the current user's reports, and loading an owned report.
- Existing persistence stores identifier type/value, description, owner, status, timestamps, and optional evidence relationships.
- There is no public lookup API or `/[locale]/suspects/search` implementation yet.
- The navbar already exposes a combined suspect entry. Phase 10 must preserve a dedicated navbar destination for reporting/checking suspects.

## 2.3 Cyber Saathi handoff baseline

- `WorkflowHandoff` already supports `secure_india` as `preview` and `search_suspect_reports` as `planned`.
- Session 10.1 must consume the existing route contract and change implementation status only after the real corresponding surface is available and tested.
- Cyber Saathi must pass a purpose-specific validated identifier payload when one is confirmed; it must not pass arbitrary raw conversation text to search.

## 2.4 Resume baseline

- Cyber Warrior already has resume upload, persisted parsing results, editable review, explicit confirmation, profile/skills/education/experience/certification replacement logic, and application continuation.
- The parser currently returns a static synthetic profile through `MockResumeParser`.
- Parsed output is already treated as untrusted until the citizen reviews and confirms it. Phase 10 must preserve and strengthen this boundary.

## 2.5 Complaint-copy baseline

- Identified complaints have authenticated ownership and a My Complaints surface.
- Anonymous complaints intentionally have no user identity relationship.
- Public complaint tracking exposes bounded status information by complaint number; it is not authorization to expose the complaint body.
- There is no downloadable complaint-copy endpoint or UI action.
- A complaint number alone must never grant access to a full complaint document.

---

# 3. PHASE-WIDE NON-NEGOTIABLE CONTRACT

## 3.1 Prototype truthfulness

CyberRakshak is not connected to live police, government, bank, UIDAI, telecom, UPI, or law-enforcement systems.

- Any map/ranking/hot-zone dataset used without a validated production source must be labelled **Illustrative / Mock Data** at the page, chart, tooltip, table, download, and API-metadata levels where applicable.
- Never use real citizen complaint records as public map data unless a separate documented consent, aggregation, privacy, minimum-cell-size, and data-governance contract exists.
- A suspect-search result means only that an identifier appears in eligible reviewed reports. It does not prove ownership, guilt, criminality, or legal status.
- A downloadable complaint copy is a citizen record generated by the prototype. It is not an FIR, police acknowledgement, legal certificate, or government-issued document.

## 3.2 Privacy and identity separation

- Anonymous complaint flows must remain identity-free.
- Do not require login to preserve an anonymous complaint's allowed download path.
- Do not use a public complaint number as a bearer secret for a full complaint copy.
- Never expose reporter identity, report descriptions, evidence, storage keys, IP addresses, or internal moderation notes through suspect search.
- Never use a Secure India filter selection as consent to publish or search a citizen's report location.
- Resume contents are sensitive and untrusted. Do not place raw resume text, files, contact details, or extracted PII in ordinary logs, analytics, browser storage, or LLM traces.

## 3.3 Human review

- Suspect search must communicate uncertainty and offer a correction/false-positive path.
- Resume extraction must never silently update the Cyber Warrior profile. Every suggestion remains editable and must be explicitly confirmed.
- Complaint generation must use persisted, citizen-reviewed data. Never generate a supposedly official copy directly from raw Cyber Saathi chat text.

## 3.4 Architecture

- Follow `PROJECT-STRUCTURE.md` and existing dependency direction.
- UI calls the central frontend API clients; route handlers call services; services call repositories/storage/rendering adapters.
- Reuse existing authentication, authorization, audit, notification, upload, i18n, design-system, and error-response conventions.
- Do not place business logic in React components or FastAPI route functions.
- Do not create duplicate complaint, suspect, resume, storage, or session architectures.
- Do not add a database table or migration without reconciling it with `02-DATABASE.md` and updating that contract.

## 3.5 Language and accessibility

- Every new citizen-facing string must exist in English and Hindi through `next-intl`.
- Preserve practical Hinglish inputs for identifier/search handoffs where relevant.
- All interactive charts/maps require keyboard support, visible focus, screen-reader labels, and an equivalent non-map list/table view.
- Do not encode meaning by colour alone.
- Controls must remain usable at 390 × 844 and common desktop widths without horizontal page overflow.
- Generated complaint copies must render English and Hindi text legibly with embedded/subset fonts that support required scripts.

## 3.6 Performance and resource constraints

- Keep the local architecture lightweight and hackathon-appropriate.
- Do not add Elasticsearch/OpenSearch, a heavyweight GIS server, a distributed queue, a local LLM, or a large startup-time index.
- Load map/search datasets through bounded, versioned application APIs or build-time/static assets as appropriate.
- Lazy-load genuinely heavy map code and avoid blocking the page's useful first render.
- Paginate/bound suspect operations and never allow an unbounded public listing endpoint.

## 3.7 Security baseline

- Validate all inputs on the server even when the browser validates them first.
- Apply strict file signature, type, size, decompression, and extraction limits.
- Use authorization for identified resources and a scoped, unguessable capability for anonymous complaint-copy access.
- Use no-store/private caching headers on sensitive responses and downloads.
- Redact logs and audit only safe metadata.
- Prevent CSV/formula, HTML, template, PDF, path, archive, and prompt-injection payloads from becoming executable output.
- Add abuse controls to public suspect search: exact-match only, rate limiting/throttling, bounded responses, no wildcard/prefix enumeration, and safe error messages.

---

# 4. PHASE-WIDE PRODUCT PRINCIPLE

Phase 10 should connect four related citizen needs without merging their trust boundaries:

```text
Understand regional cyber-risk patterns
  → Secure India interactive explorer

Check a suspicious identifier
  → safe exact-match reported-signal search

Apply as a Cyber Warrior
  → real resume extraction → review → confirmed auto-fill

Keep a copy of a submitted complaint
  → authorized/redacted downloadable document
```

The experience should be useful to a low-digital-literacy citizen, but every result must remain transparent about source, freshness, mock/provider status, and uncertainty.

---

# 5. SESSION 10.1 — INTERACTIVE SECURE INDIA + SEARCH SUSPECT REPORTS

## Objective

Turn the current Secure India preview into an interactive public cyber-risk explorer and make safe suspect-identifier search available both contextually inside Secure India and through a dedicated navbar-accessible suspect surface.

Search integration must not remove, replace, or hide the suspect navbar item or the existing `/suspects/report` journey.

## 5.1 Required route and navigation outcome

At minimum preserve or implement:

```text
/[locale]/secure-india
/[locale]/suspects/search
/[locale]/suspects/report
```

The navbar's suspect destination must remain visible. It may lead to a clear Search/Report landing state or preserve the existing combined label, but both **Check an identifier** and **Report an identifier** must be discoverable without entering Secure India.

Secure India must include a contextual entry into suspect search, for example a clearly separated **Check a suspicious phone, UPI ID, email, link, account or profile** panel/action. Do not visually imply that the map itself identifies a person.

## 5.2 Scope matrix

| Requirement / state | Route / component | API / data boundary | Automated verification | Manual acceptance |
| --- | --- | --- | --- | --- |
| Hero and summary | Secure India page/hero | versioned aggregate metadata | schema and rendering tests | reference hierarchy, clear mock/source label |
| Filters | crime type, State/UT, city/region, time range, count/per-lakh toggle | bounded query validated by API | filter/query tests | keyboard, URL/deep-link and reset behavior |
| Interactive map | accessible map/choropleth layer | approved synthetic/aggregate geometry and metrics only | data joins, tooltip values, no-data tests | hover, focus, click, zoom/pan where justified, mobile fallback |
| Rankings | city/state ranking list | same selected aggregate snapshot | sorting/tie/empty tests | selected filters stay synchronized |
| Hot zones | zone cards/list | same selected aggregate snapshot | consistency tests | selecting a zone focuses the corresponding map/list entry |
| Hot crimes | crime cards/list | same selected aggregate snapshot | totals/percent tests | each item links to matching prevention guidance |
| Loading/error/empty | all Secure India regions | typed safe API errors | component/API failure tests | retry works; stale values are not presented as current |
| Suspect search | dedicated route plus Secure India module | exact normalized identifier query | validation/privacy/abuse tests | clear pending, match, no-match, error and correction states |
| Suspect report | existing report route | existing create/evidence APIs | regression tests | search can lead to report without overwriting entered identifier |
| Cyber Saathi handoff | Cyber Saathi action card | existing typed workflow handoff | routing/payload tests | confirmed identifier pre-fills search; unconfirmed data does not |
| i18n/accessibility | all new states | English/Hindi message namespaces | key parity and a11y checks | desktop/mobile, keyboard and screen-reader labels |

## 5.3 Secure India visual acceptance contract

The saved reference composition is not a decorative screenshot. Recreate its information hierarchy as real interface elements:

1. A navy public-service hero with:
   - `Secure India` eyebrow;
   - a clear citizen-focused title;
   - a concise explanation of what the page shows;
   - a compact summary-metric strip.
2. A filter band containing:
   - crime type;
   - State/UT;
   - city/region where data permits;
   - time range such as 7D / 30D / 1Y or the exact ranges supported by the dataset;
   - view mode such as raw count / per-lakh population only when denominator data is valid.
3. A large primary map area with visible source/mock labeling, selected geography, legend, and accessible selected-region details.
4. City/state rankings synchronized with the selected filters.
5. Hot-zone cards and hot-crime cards with restrained severity colours, meaningful labels, and prevention-guide links.
6. A high-contrast report CTA band and a Learning Corner connection.
7. A clearly separated suspect-search entry that complements this risk view without suggesting that map areas or people are criminal.

Preserve the established victim-report navbar/header pattern and CyberRakshak design language. Do not redesign this into a generic SaaS analytics dashboard. Safe neutral branding must replace any prohibited emblem or government mark.

The current preview panel's explanatory content may remain only if it helps users understand source/methodology. The large static screenshot must be removed from the primary experience once its real interactive equivalent passes acceptance; do not retain two competing full dashboards.

## 5.4 Secure India interaction contract

Required interactions:

- Filters update the map, metric strip, ranking, hot zones, and hot crimes from one consistent data response/snapshot.
- Current filter state is shareable/restorable through safe URL search parameters where practical.
- Hover and keyboard focus show the same tooltip/detail facts.
- Click/Enter selects a geography and updates the adjacent detail/ranking context.
- A reset action restores a documented default view.
- Loading states keep layout stable; errors offer retry; no-data states explain the selected combination.
- Mobile may use a simplified map plus the equivalent ranked list/table, but it must not remove information or require hover.
- Reduced-motion users do not receive forced animated map transitions.
- The map has a text/table alternative with the same values and selection semantics.

Do not implement interactions that the dataset cannot truthfully support. For example, do not offer `per 1 lakh population` unless population denominator, period, geography, and calculation are defined and tested.

## 5.5 Secure India data contract

Until a validated production source is approved, use a small versioned **synthetic/illustrative** dataset with internally consistent values.

Each dataset/snapshot must carry at least:

```text
dataset_id
version
source_type: synthetic | approved_public
source_label
methodology_note
generated_or_published_at
period_start
period_end
geography_level
crime_category
complaint_count
population_denominator (nullable)
```

Requirements:

- Keep geometry/region identifiers separate from display names and translated labels.
- Validate that aggregate rows join to known geography IDs.
- Derive summary cards, rankings, legends, and percentages from the same response rather than hard-coding inconsistent numbers in several components.
- Enforce non-negative counts, valid periods, unique keys, valid parent geography, and percentage/total consistency.
- Version and test the demo seed/snapshot.
- Never read raw `complaints`, `complaint_locations`, reporter profiles, or evidence tables into a public map merely because the data exists locally.
- If an approved public source is added later, document license, attribution, jurisdiction, freshness, transformations, and limitations before changing `source_type`.

## 5.6 Secure India API contract

Prefer a compact typed API that returns metadata, available filters, aggregates, rankings, and selected-region detail without exposing row-level complaints.

Conceptual endpoints (adapt names to existing API conventions):

```text
GET /api/v1/secure-india/metadata
GET /api/v1/secure-india/summary?crime_type=&state=&city=&period=&view=
```

The service layer owns filtering, aggregation consistency, sorting, and calculation. The frontend owns presentation only.

Responses must include source type/label, data period, last-updated value, methodology/limitations, and whether figures are illustrative. Validate/bound query values and cache only non-sensitive aggregate responses appropriately.

## 5.7 Search Suspect Reports meaning

The feature answers a narrow question:

> Has this exact identifier appeared in eligible reviewed reports in this prototype?

It does **not** answer:

- Who owns the identifier?
- Is the owner a criminal?
- Is a transaction fraudulent?
- Is the identifier safe merely because there is no match?
- What private evidence or reporter details were submitted?

Every result state must repeat the correct meaning in plain language.

## 5.8 Search input and normalization

Supported types should reuse the existing enum unless a documented migration is approved:

```text
PHONE
EMAIL
UPI
BANK_ACCOUNT
WEBSITE
SOCIAL_MEDIA
OTHER
```

Requirements:

- Use the same validation rules in report and search flows, with the server authoritative.
- Implement type-specific canonical normalization in one backend helper/service; do not duplicate it across UI, repository, and Cyber Saathi.
- Normalize case, whitespace, phone punctuation/country conventions, URL host/scheme rules, and social handles only where equivalence is safe and documented.
- Preserve the citizen's original display input only as needed for the current UI; search/audit/log paths must mask or hash sensitive values.
- Use exact canonical match. Do not allow wildcard, partial, prefix, fuzzy, bulk, or autocomplete enumeration of identifiers.
- If efficient/privacy-preserving lookup requires a normalized or keyed-hash column, add a reviewed Alembic migration and reconcile `02-DATABASE.md`; never invent a shadow data store.

## 5.9 Public search eligibility and result contract

Only records that have passed the project's explicit admin review/display eligibility rule may contribute to a public match. `SUBMITTED`, `UNDER_REVIEW`, and `REJECTED` records must not silently appear as public accusations.

The response may return only a bounded aggregate signal such as:

```text
query_type
masked_query
match_state: reviewed_signal_found | no_reviewed_signal | unavailable
eligible_report_count (bounded/coarsened where needed)
first_reported_period (optional, coarse)
last_reported_period (optional, coarse)
categories (optional, reviewed and non-identifying)
disclaimer
source_scope
```

Do not return reporter IDs, names, contact data, raw identifier variants, descriptions, evidence, complaint IDs, storage keys, admin notes, or row-level timestamps.

The no-match message must say that no eligible reviewed signal was found in this prototype dataset; it must not say the identifier is safe.

The match message must say the identifier has appeared in eligible reviewed reports and recommend independent caution/reporting; it must not say the person is guilty or the identifier is definitely fraudulent.

## 5.10 Search API and abuse controls

Prefer a request body so identifiers do not appear in URLs, browser history, access logs, or analytics:

```text
POST /api/v1/suspects/search
{
  "identifier_type": "UPI",
  "identifier_value": "example@upi"
}
```

The endpoint must:

- return a typed bounded result;
- use no-store headers;
- avoid echoing the full raw identifier;
- enforce request size and type-specific validation;
- enforce throttling/rate limits appropriate to the project's stack;
- reject batch queries, wildcards, prefixes, and unsupported types;
- use constant-shape success/no-match responses where practical to reduce enumeration value;
- log only safe request ID, type, masked/hash metadata, result class, latency, and rate-limit outcome;
- degrade safely when the database is unavailable.

Do not add CAPTCHA unless justified and testable. A clean adapter boundary for a future production abuse-control provider is acceptable; a fake working CAPTCHA is not.

## 5.11 Correction / false-positive pathway

A visible result action must let a person report a possible mistake or misuse.

The pathway must:

- explain that search signals are not a finding of guilt;
- avoid revealing the original reporter;
- accept only the minimum information needed to review the concern;
- validate and rate-limit submissions;
- create a durable reviewable record or use an existing genuinely persisted support workflow;
- never claim a correction was completed merely because a message was submitted;
- expose an appropriate admin/review status boundary if the product claims status tracking.

If a new persistence model is required, document and migrate it through the existing database architecture. Do not represent a mailto link or static message as a completed correction workflow.

## 5.12 Search and report journey integration

- From search, citizens can choose **Report this identifier** and continue to the existing `/suspects/report` flow with validated type/value prefilled for review.
- Search must never automatically create a report.
- Reporting must retain its existing authentication/ownership and evidence rules.
- A report submission may link back to search education, but a newly submitted unreviewed report must not immediately change public search results.
- From Secure India, citizens can open search without losing safe map filter state.
- From the navbar, citizens can reach Search and Report directly.
- From Cyber Saathi, only a confirmed identifier may prefill the search form; otherwise the UI asks the citizen to enter/review it.

## 5.13 Cyber Saathi contract update

After `/suspects/search` passes its implementation and security gates:

- change `search_suspect_reports` from `planned` to `available`;
- change copy from “not available” to accurate search-result expectations;
- include a validated optional identifier type/value handoff object or a scoped browser handoff store consistent with existing patterns;
- preserve critical-entity confirmation before handoff;
- keep `secure_india` as `preview` until the interactive route itself passes, then mark it `available`;
- keep all statements explicit that no live government/police lookup occurs.

## 5.14 Session 10.1 automated tests

At minimum cover:

### Secure India data/API

- metadata/source/mock label is always present;
- invalid filters are rejected;
- filter combinations return internally consistent summary/rank/map/card values;
- rankings use deterministic tie-breaking;
- per-lakh calculations require a valid denominator;
- no raw complaint/user/evidence fields are exposed;
- unknown geography and no-data states are distinct;
- synthetic snapshot integrity and geography joins pass;
- response size and query limits are bounded.

### Suspect search

- each supported identifier type has valid/invalid normalization cases;
- exact normalized equivalents match;
- partial, prefix, wildcard and batch attempts fail;
- submitted/under-review/rejected records do not appear publicly;
- eligible reviewed fixtures return only aggregate safe fields;
- no-match never claims safety;
- match never claims guilt/criminality;
- raw identifiers are absent from logs and safe response metadata;
- throttling returns a controlled error;
- correction requests validate and persist without exposing reporters;
- prefill from search to report remains reviewable and does not auto-submit;
- Cyber Saathi unconfirmed entities cannot enter search handoff.

### Frontend

- filter/map/list state stays synchronized;
- keyboard and pointer selection produce the same details;
- loading, error, retry, no-data, match, no-match, rate-limited, and correction states render;
- navbar retains the suspect destination;
- English/Hindi message keys remain in parity;
- no horizontal overflow at required viewports.

## 5.15 Session 10.1 manual acceptance

Use the real local frontend/API and record evidence for:

1. Default Secure India desktop view.
2. State/UT selection, crime-type change, time-range change, and reset.
3. Map pointer interaction and keyboard-only equivalent.
4. Mobile selection without hover.
5. Count/per-lakh behavior or its deliberate omission when denominator data is unavailable.
6. Ranked list, hot zone, and hot crime synchronization.
7. Prevention guide navigation.
8. Secure India → suspect search.
9. Navbar → suspect Search and Report.
10. Exact reviewed-signal match, no-match, invalid, rate-limited, unavailable, and correction flows.
11. Search → prefilled report review without automatic submission.
12. Cyber Saathi confirmed-identifier handoff.
13. English and Hindi.
14. Loading/slow response, empty state, API failure/recovery.
15. No console errors, failed product requests, hydration failures, broken focus, or horizontal page overflow.

## 5.16 Session 10.1 gate

Session 10.1 passes only when:

- Secure India is a real interactive prototype, not a static dashboard image;
- its data is internally consistent and truthfully labelled;
- map information has an accessible non-map equivalent;
- suspect search is available from both Secure India and the preserved navbar destination;
- search is exact, privacy-bounded, abuse-controlled, and aggregate-only;
- no public result treats an unreviewed allegation as a criminality finding;
- correction/false-positive handling is actionable and honest;
- Cyber Saathi handoff statuses reflect actual availability;
- existing suspect reporting and all earlier citizen/Cyber Warrior journeys still pass;
- backend tests, frontend lint/type/build, desktop/mobile/browser acceptance, and documentation pass.

**Do not begin Session 10.2 until this gate passes.**

---

# 6. SESSION 10.2 — REAL RESUME PARSING/AUTO-FILL + DOWNLOADABLE COMPLAINT COPY

## Objective

Complete two review-and-export workflows:

1. turn a citizen-authorized Cyber Warrior resume into real, traceable, editable profile suggestions; and
2. let a citizen securely download a faithful copy of a persisted complaint without weakening anonymous/identified access boundaries.

These features share a product principle—structured output must be generated from user-owned data and reviewed before it is treated as final—but they must remain separate services and permission domains.

## 6.1 Scope matrix

| Requirement / state | Route / component | API / data boundary | Automated verification | Manual acceptance |
| --- | --- | --- | --- | --- |
| Resume upload | existing Cyber Warrior resume route | object storage + resume API | signature/type/size/ownership tests | drag/drop, selection, replacement, errors |
| Text extraction | backend resume parser adapter | bounded PDF/DOCX/DOC extraction | parser fixtures and hostile-file tests | real sample files produce source text or honest error |
| Structured parsing | resume parsing service | validated schema; optional configured hosted model | mapping/validation/fallback tests | extracted fields reflect the uploaded file, not static mock data |
| Review | existing resume review UI | persisted untrusted parsing result | ownership/status tests | provenance/confidence, edit/remove, empty fields |
| Confirmed auto-fill | existing profile/skills/education/experience/certification services | explicit confirmation transaction | replacement/idempotency tests | only reviewed values update profile |
| Resume failure/retry | upload/review states | controlled parser errors | timeout/failure tests | original profile remains unchanged |
| Submitted complaint copy | submitted/tracking/My Complaints actions | authorized PDF endpoint | ownership/token/content tests | correct bilingual PDF downloads |
| Anonymous copy access | anonymous submission/session | scoped unguessable capability, stored hashed | leakage/replay/revocation tests | no login/identity required; complaint number alone fails |
| Identified copy access | authenticated complaint ownership | existing bearer auth + owner check | 401/403/404 tests | another account cannot download |
| PDF rendering | backend complaint document adapter | persisted reviewed complaint snapshot | structure/redaction/render tests | legible, paginated, no clipping/overflow |
| i18n/accessibility | actions/status/errors | English/Hindi strings | key parity and a11y tests | keyboard, screen reader, mobile |

## 6.2 Resume parsing applies to Cyber Warrior

“Resume parsing and auto-fill” in this session refers to the existing Cyber Warrior application journey:

```text
/[locale]/cyber-warrior/apply/resume
  → upload
  → extraction/parsing
  → editable review
  → explicit confirmation
  → profile/application auto-fill
```

Do not attach resumes to complaint evidence or use resume content to populate a citizen complaint.

## 6.3 Resume parser architecture

Preserve the existing adapter boundary and replace the static `MockResumeParser` as the normal runtime implementation.

Required pipeline:

```text
Citizen-selected resume
  → server-side signature/type/size validation
  → existing object-storage adapter
  → bounded text extraction
  → normalization and section detection
  → structured suggestion parser
  → strict schema validation
  → persisted ResumeParsingResult (untrusted)
  → citizen review/edit/remove
  → explicit confirmation transaction
  → Cyber Warrior profile/application fields
```

The mock parser may remain only as an explicit test fixture or clearly labelled demo fallback selected by configuration. Production-shaped runtime must never silently return the same synthetic person for every uploaded file.

## 6.4 Supported file contract

Inspect the existing upload/storage implementation before changing formats. The current UI/API advertises PDF, DOC, and DOCX up to 10 MB.

Requirements:

- Verify extension, declared MIME type, and file signature; do not trust the filename.
- Enforce compressed/decompressed size, page/paragraph/character, processing-time, and recursion limits.
- PDF and DOCX must have a real safe extraction path.
- Keep DOC only if the repository/runtime has a proven safe extractor. If it does not, align UI/API/docs to an honest supported set rather than treating binary data as text or returning synthetic output.
- Encrypted/password-protected, empty, corrupted, image-only, malformed, or unsupported files must return a controlled reviewable error.
- OCR for scanned/image-only resumes is optional unless a safe bounded adapter is implemented and documented. Never claim OCR occurred when it did not.
- Do not execute macros, embedded scripts, links, objects, commands, or templates.
- Do not send files to a third party without explicit configuration, privacy documentation, and citizen-facing disclosure/consent where required.

## 6.5 Deterministic extraction and optional model parsing

Prefer a two-stage design:

1. **Deterministic extraction** obtains bounded plain text and basic sections from the file.
2. **Structured parsing** maps that text to the existing Cyber Warrior schema.

If the existing hosted LLM gateway is used for structured parsing:

- keep provider selection/configuration server-side;
- send only the minimum bounded resume text required;
- use a resume-specific strict structured-output schema;
- set conservative generation settings;
- reject invalid/malformed/unsupported fields;
- treat all resume text as untrusted data, never as instructions;
- prevent prompt injection from overriding system policy, requesting secrets, changing routes, or inventing credentials;
- record provider/model/latency/status metadata without logging raw resume contents;
- fall back to deterministic partial extraction or a reviewable failure, not static fictional details.

Do not add a local LLM or heavyweight parsing service.

## 6.6 Resume structured suggestion contract

Map only fields supported by the existing schema, such as:

```text
profile:
  bio
  location
skills[]
education[]:
  institution
  degree
  field_of_study
  start/end dates where supported
experience[]:
  organization
  title
  description
  start/end dates and is_current where supported
certifications[]:
  name
  issuing_organization
  issue/expiry dates and credential metadata where supported
```

Requirements:

- Do not invent missing dates, organizations, degrees, skills, certifications, locations, or job titles.
- Normalize values only when meaning is preserved.
- Deduplicate cautiously without merging different roles/qualifications.
- Keep unknown values null/empty.
- Retain per-field or per-section provenance (source page/section/text span or an equivalent non-sensitive reference) and optional confidence where the schema can support it.
- Never allow extracted name/mobile/email to overwrite immutable synthetic identity-verified fields.
- Do not infer protected traits or score employability.
- Do not make hiring, eligibility, certification, or trustworthiness decisions from resume text.

If persistence needs provenance/confidence fields, reconcile the schema with `02-DATABASE.md` and add a migration. Do not store unnecessary full-text duplicates.

## 6.7 Review-first UI contract

The resume review screen must show:

- uploaded filename and parser status;
- what was extracted and what was not found;
- clear **Suggested from your resume** labeling;
- editable profile, skills, education, experience, and certification entries;
- add/remove controls for repeatable sections;
- per-field validation and useful error summaries;
- a notice that parser output may be wrong and will not be saved until confirmation;
- retry/upload replacement without losing the existing confirmed profile;
- explicit confirmation before replacing existing parsed profile collections;
- success state and continuation into the existing application flow.

Do not use disabled-looking fields for editable suggestions. Immutable verified identity fields must be visually distinct and explain why they cannot be edited here.

## 6.8 Auto-fill transaction and state contract

- Upload creates a new parsing attempt owned by the authenticated Cyber Warrior.
- Parsing failure is persisted as a safe status/error without updating profile tables.
- Review fetch is owner-authorized.
- Confirmation accepts a validated, citizen-reviewed payload rather than blindly trusting the original parser JSON.
- Confirmation is idempotent or returns a clear conflict on repeat.
- Replace-all child collections must use the proven clear → flush → repopulate transaction order to preserve uniqueness constraints.
- A new upload/review must not delete the prior confirmed profile until the new confirmation commits.
- If confirmation fails, roll back the complete transaction and preserve the prior profile.
- Audit upload/processing/confirmation using safe metadata only.
- Refresh/resume must reopen the correct owned parsing result and review state.

## 6.9 Resume parser observability

Track only safe metadata such as:

```text
request_id
resume_result_id
user_id (internal audit only)
file_type
file_size
page_count or bounded unit count
extractor
parser_adapter
provider/model when applicable
extraction_latency
parsing_latency
validation_status
error_class
confirmed_at
```

Never log raw resume text, file bytes, home address, phone, email, education descriptions, employer descriptions, access tokens, provider keys, or prompt contents.

## 6.10 Downloadable complaint copy scope

Provide a **Download complaint copy** action at minimum from:

- the complaint submitted success page;
- the identified citizen's My Complaints/tracking detail where ownership is available;
- the anonymous post-submission/session state when its scoped capability remains available.

The required artifact is a PDF. A print-only browser page or client-generated screenshot is not sufficient.

A draft export may be added only as an explicit action and must be watermarked **DRAFT — NOT SUBMITTED**. The required Phase 10 completion path is the submitted complaint copy.

## 6.11 Complaint copy source-of-truth

Generate the document from the persisted complaint and its authorized related records at request time or from an immutable persisted submission snapshot if that architecture is explicitly introduced.

Do not generate from:

- raw Cyber Saathi turns;
- browser localStorage alone;
- URL query parameters;
- unconfirmed prefill;
- arbitrary client-provided HTML/JSON;
- a public tracking response.

The service/repository layer must load exactly one authorized complaint and create a sanitized document view model before rendering.

## 6.12 Identified complaint authorization

For identified complaints:

- require the existing authenticated session/access token;
- load the complaint through an owner-authorized service/repository path;
- return 401 for missing authentication, 403 or the project's standard non-disclosing response for another owner, and 404 for absent resources according to existing conventions;
- never authorize by complaint number alone;
- prevent IDOR across complaint IDs and numbers;
- expose the action only when the UI has sufficient ownership context, while retaining server enforcement.

## 6.13 Anonymous complaint access

Anonymous users must be able to download their own allowed copy without creating identity linkage.

Use a separate high-entropy, narrowly scoped complaint-access capability:

- generate it server-side using a cryptographically secure source;
- bind it to one anonymous complaint and allowed actions;
- return/display it only through the anonymous creation/submission workflow;
- store only a secure hash/digest server-side if persistence is required;
- keep it separate from the public complaint number;
- persist it in the existing anonymous browser/session boundary only with clear recovery guidance;
- never include identity claims in the token or complaint record;
- support expiration/rotation/revocation semantics appropriate to the prototype and document them;
- redact it from logs, errors, analytics, referrers, URLs, filenames, and PDF content;
- use an authorization header or another non-URL transport for the download request.

If the current schema cannot support this safely, add the smallest reviewed model/migration and update `02-DATABASE.md`, `06-API.md`, and `08-SECURITY.md`.

Losing the anonymous capability may mean the full copy cannot be recovered. Explain this honestly; do not weaken privacy by asking for or silently attaching identity.

## 6.14 Complaint PDF content contract

The PDF should contain only fields that are appropriate for the complaint's reporting mode and current persisted state.

Required structure:

1. CyberRakshak neutral header and clear document title.
2. Prominent prototype disclaimer:
   - citizen-generated complaint copy;
   - not an FIR;
   - not a police/government acknowledgement;
   - not proof of submission to an external authority.
3. Complaint reference number.
4. Submission/status and relevant timestamps.
5. Reporting mode and who the report concerns.
6. Category, title, description, incident date/time, and financial loss when present.
7. Location fields when present.
8. Suspect information when present, labelled as reported/alleged information.
9. Evidence manifest containing safe user-facing metadata only—never object-storage keys or private URLs.
10. A concise next-steps/tracking note using only existing prototype capabilities.
11. Generation timestamp, document version, and page numbers.

Anonymous copy rules:

- no reporter name, profile, registered mobile, identity/Aadhaar, user ID, access capability, or hidden identity metadata;
- do not reconstruct identity from Cyber Saathi, browser data, evidence metadata, or affected-person fields;
- affected-person details appear only if they belong to the reviewed complaint body and comply with the existing anonymous/category contract.

Identified copy rules:

- include reporter information only if the product/data contract explicitly permits it and the field is loaded through the authorized profile boundary;
- do not include secrets, OTP state, tokens, internal IDs, private notes, or provider metadata.

## 6.15 PDF rendering and delivery

Create a backend document-rendering adapter/service that:

- consumes a typed sanitized complaint document model;
- escapes all citizen-controlled content;
- supports English and Hindi Unicode correctly;
- embeds/subsets approved local fonts with suitable licensing;
- wraps long URLs/identifiers/descriptions safely;
- paginates long content without clipping, overlaps, orphaned headings, or blank pages;
- provides descriptive headings and logical reading order where the chosen PDF library supports it;
- uses a safe filename such as `CyberRakshak-Complaint-CR-....pdf` without user-controlled path fragments;
- returns `application/pdf`, `Content-Disposition: attachment`, `X-Content-Type-Options: nosniff`, and no-store/private cache headers;
- does not write long-lived temporary files when in-memory/secure temporary rendering is sufficient;
- cleans temporary files deterministically on success and failure;
- records safe audit metadata and render latency.

The frontend should download the authenticated response blob through the central API client, preserve error handling, and never place an access token/capability in the URL.

## 6.16 Conceptual complaint-copy API

Adapt to current conventions, but preserve the security semantics:

```text
GET /api/v1/complaints/{complaint_id}/copy
Authorization: Bearer <identified access token>

or for anonymous ownership:

GET /api/v1/complaints/{complaint_id}/copy
X-Complaint-Access-Token: <scoped anonymous capability>
```

One endpoint with a service-level authorization policy is preferred over duplicate rendering implementations.

Do not expose the full copy at `/track/{complaint_number}`. Public tracking remains a bounded status-only contract.

## 6.17 Session 10.2 automated tests

At minimum cover:

### Resume upload/extraction

- valid text PDF and DOCX extraction;
- DOC only when a proven extractor exists;
- filename/MIME/signature mismatch;
- oversize, decompression bomb, page/character limit, encrypted, corrupt, empty, and image-only files;
- extraction/parser timeout and controlled provider failure;
- prompt-injection text cannot change schema, system policy, or expose secrets;
- static mock profile is never returned in normal runtime;
- raw text/PII is absent from logs.

### Resume structured parsing/review

- education, experience, skills, certification, bio, and location mapping;
- missing values remain missing;
- no invented dates/credentials;
- malformed/extra model fields are rejected;
- duplicate handling is deterministic;
- immutable verified identity fields cannot be overwritten;
- another user cannot read/confirm a parsing result;
- failed parsing/confirmation leaves the current profile unchanged;
- successful edited confirmation replaces collections transactionally;
- repeated confirmation is idempotent or a controlled conflict;
- replacement upload/resume state works after refresh.

### Complaint copy authorization

- identified owner downloads successfully;
- unauthenticated and wrong-owner requests fail;
- anonymous scoped capability succeeds for only its complaint;
- complaint number alone cannot download;
- guessed, expired, revoked, malformed, or other-complaint capability fails;
- anonymous download does not create or require identity;
- public tracking remains status-only;
- tokens/capabilities are absent from logs, URL, filename, PDF, and error body.

### PDF correctness and safety

- response headers and filename are safe;
- generated bytes form a valid PDF;
- required sections and prototype disclaimer are present;
- anonymous identity/secrets/internal IDs/storage keys are absent;
- identified content follows the approved field contract;
- long multilingual descriptions, URLs, identifiers, empty optional fields, multiple suspects, and multiple evidence items render;
- HTML/template/control characters render as text and cannot alter the document;
- Hindi font extraction/render smoke test passes;
- multi-page layout has no clipped content using the repository's PDF render-and-inspect workflow.

### Regression

- anonymous and identified complaint creation/submission/tracking still pass;
- Cyber Saathi report prefill still requires review;
- Cyber Warrior application/resume confirmation and unique child collections still pass;
- frontend English/Hindi key parity, lint, type check, and build pass.

## 6.18 Session 10.2 manual acceptance

Use real local routes/APIs and safe synthetic fixtures. Record evidence for:

1. Upload a real synthetic text PDF resume; verify extracted details come from that file.
2. Upload a different resume; verify suggestions differ and the previous confirmed profile remains until confirmation.
3. Review, edit, remove, add, confirm, refresh, and continue the Cyber Warrior application.
4. Parser unavailable, corrupt, empty, unsupported, image-only, and timeout states.
5. English and Hindi resume UI; long values and mobile layout.
6. Identified complaint submission → download → open/rendered PDF inspection.
7. Identified My Complaints/tracking → repeat download.
8. Wrong-account/unauthenticated download rejection.
9. Anonymous complaint submission → capability-backed download without login.
10. Complaint number without capability → rejection.
11. English and Hindi PDFs with long multiline content, suspect information, and evidence manifest.
12. PDF disclaimer, redaction, filenames, headers, page breaks, typography, and no clipped/overflowing content.
13. Keyboard/focus/loading/error/retry behavior for download actions.
14. No product console errors, failed authorized requests, sensitive logs, or stale loading states.

## 6.19 Session 10.2 performance observations

Measure and record development-machine observations for:

- upload validation;
- text extraction by file type and representative size;
- optional model structured parsing;
- persisted parsing-result load;
- confirmation transaction;
- PDF generation for one-page and representative multi-page complaints;
- download time to first byte and total bytes;
- memory delta during extraction/rendering;
- frontend build/startup regression.

These are observations, not production SLAs. Enforce hard time/size bounds and avoid optimizing with heavyweight infrastructure.

## 6.20 Session 10.2 gate

Session 10.2 passes only when:

- normal resume uploads produce real file-derived suggestions rather than static mock data;
- parser output remains untrusted, editable, and explicitly confirmed;
- verified identity fields and existing profile data are protected;
- parser failures never mutate the profile;
- submitted complaint copies are generated from authorized persisted data;
- identified ownership and anonymous capability access both pass without identity leakage;
- complaint numbers cannot expose full complaint content;
- PDFs are accurate, bilingual, legible, securely delivered, and clearly non-government/prototype artifacts;
- relevant backend/full-stack regressions pass;
- frontend lint/type/build and PDF render/visual inspection pass;
- desktop/mobile/accessibility/security/performance evidence and documentation are complete.

---

# 7. CROSS-SESSION END-TO-END SCENARIOS

The Phase 10 final suite must include at least:

## Scenario A — Explore and learn

Citizen selects a State/UT, crime type, and time period in Secure India, inspects a map region through keyboard, opens the equivalent table row, then follows the matching prevention guide.

Expected:

- synchronized values;
- visible illustrative/source label;
- no hover-only information;
- no claim of live government data.

## Scenario B — Check then report an identifier

Citizen searches a suspicious UPI ID, receives a reviewed-signal/no-signal result with correct uncertainty, then chooses to report it.

Expected:

- exact canonical validation;
- no criminality claim;
- no raw reporter/evidence data;
- type/value prefilled for review;
- no auto-submission;
- newly submitted report does not instantly become a public match.

## Scenario C — Cyber Saathi suspect handoff

Citizen asks Cyber Saathi to check a phone/UPI ID.

Expected:

- critical identifier confirmation;
- typed available handoff;
- dedicated search opens with reviewed value;
- arbitrary surrounding chat is not sent to search.

## Scenario D — Real Cyber Warrior resume

Citizen uploads a synthetic resume containing distinct education, experience, skills, and certification data, edits one suggestion, removes one item, and confirms.

Expected:

- values originate from the uploaded document;
- unsupported/missing fields are not invented;
- identity fields are not overwritten;
- edited confirmed data appears in the application/profile after refresh.

## Scenario E — Identified complaint copy

An identified citizen submits a complaint and downloads the copy from the success page and later from My Complaints.

Expected:

- owner authorization;
- accurate persisted values;
- prototype disclaimer;
- bilingual text and pagination;
- another account cannot download.

## Scenario F — Anonymous complaint copy

An eligible anonymous citizen submits without identity and downloads using the scoped anonymous capability.

Expected:

- no login or identity attachment;
- complaint number alone fails;
- PDF contains no reporter identity/token/internal IDs;
- tracking remains separately usable through its bounded contract.

---

# 8. FINAL SECURITY REVIEW

Before Phase 10 completion, verify:

- no provider/API/storage/anonymous capability secrets in frontend source, Git, URLs, logs, analytics, PDFs, or error bodies;
- no suspect-search raw identifier in access logs or browser URL/history;
- no wildcard/bulk identifier enumeration;
- only eligible reviewed reports contribute to public search;
- no public result exposes reporter, evidence, description, internal status notes, or row-level data;
- correction requests cannot expose or contact reporters;
- Secure India does not publish raw complaint/person coordinates;
- map aggregates are synthetic or meet a documented minimum privacy threshold and consent/source contract;
- resume files cannot execute active content or control parser prompts;
- resume result ownership and confirmation authorization are enforced server-side;
- identified complaint download is IDOR-safe;
- anonymous complaint download uses a separate scoped capability and never creates identity linkage;
- PDF renderer escapes input, bounds resources, and cleans temporary files;
- public tracking cannot be escalated into full complaint access;
- error messages do not reveal whether private records exist beyond the designed aggregate search contract.

---

# 9. FINAL ACCESSIBILITY AND DESIGN ACCEPTANCE

Reopen the complete relevant design references before the final gate. Verify the whole interactive surface, not only CTAs.

## Secure India and suspect search

- target visual hierarchy from the supplied Secure India reference;
- filters, metric strip, legend, map, tooltip/detail, table alternative, rankings, cards, search entry, report CTA, and learning CTA;
- pointer, touch, keyboard, zoom, reduced motion, visible focus, and screen-reader labels;
- English/Hindi, 390 × 844 mobile and desktop;
- loading, error, retry, no-data, match, no-match, rate-limit, unavailable, and correction states;
- explicit mock/source/freshness/uncertainty copy in every relevant state.

## Resume and complaint copy

- upload, processing, success, partial extraction, empty/corrupt/unsupported, retry, review, edit, add/remove, confirm, and resume-after-refresh states;
- existing Cyber Warrior visual reference fidelity;
- download idle/loading/success/error/retry states on submitted, tracking, and My Complaints surfaces;
- PDF pages rendered to images and visually inspected for English/Hindi glyphs, long text, wrapping, page breaks, margins, disclaimer prominence, and absence of clipped/overlapping content.

Record intentional safe substitutions. A green build is necessary but is not visual or feature acceptance.

---

# 10. DOCUMENTATION REQUIREMENTS

Create/update only the relevant durable records:

1. Session 10.1 completion report.
2. Session 10.2 completion report.
3. Phase 10 completion report.
4. `02-DATABASE.md` for any approved schema/migration changes.
5. `03-ARCHITECTURE.md` for new data/rendering/parser boundaries.
6. `04-BACKEND.md` for services/adapters/security behavior.
7. `05-FRONTEND.md` for routes/components/states.
8. `06-API.md` for Secure India, search/correction, resume, and complaint-copy contracts.
9. `08-SECURITY.md` for public search, resume parsing, PDF output, and anonymous capability controls.
10. Dataset/source/methodology documentation for Secure India.
11. Parser support/limitations and privacy disclosure.
12. Complaint-copy content/redaction/access rules.

Documentation must distinguish:

- implemented;
- synthetic/mock;
- provider-dependent;
- approved-public-source data;
- future;
- deliberately unsupported.

Do not duplicate long records across root docs. Link the detailed completion reports where appropriate.

---

# 11. CODING AND VERIFICATION RULES FOR BOTH SESSIONS

For each session:

1. Inspect the repository and relevant references first.
2. Freeze a scope matrix before coding.
3. Reuse existing architecture and shared components.
4. Preserve unrelated user changes and avoid broad refactors.
5. Implement the smallest coherent full-stack feature.
6. Add server-side validation and authorization.
7. Add English and Hindi copy.
8. Run focused tests first.
9. Run the broader affected backend suite once.
10. Run repository frontend lint, TypeScript, and production build once.
11. Verify the real local UI/API at desktop and mobile sizes.
12. Inspect one relevant browser network request if UI/API disagree.
13. Run PDF render-and-inspect verification when documents change.
14. Run `git diff --check` and inspect the final diff/status.
15. Record exact results; never claim an unexecuted gate passed.
16. Save a checkpoint after each milestone so compaction cannot erase progress.
17. Stop at the session gate; do not begin the next session in the same unapproved continuation.

Use the 30–40 minute Phase 9 operating discipline where scope reasonably permits. If blocked, report the exact evidence and single next action rather than entering an unbounded diagnostic loop.

---

# 12. SESSION COMPLETION REPORT FORMAT

At the end of each session, create:

```text
## Session 10.X Completion Report

### Scope matrix outcome
- ...

### Implemented
- ...

### Files changed
- ...

### Architecture and data decisions
- ...

### API and security contracts
- ...

### Tests run
- ...

### Test results
- ...

### Manual and visual verification
- ...

### Performance observations
- ...

### Accessibility and i18n
- ...

### Known limitations
- ...

### Synthetic / mocked / provider-dependent pieces
- ...

### Handoff to next session
- ...

### Gate status
PASS / BLOCKED / READY FOR OWNER PHYSICAL ACCEPTANCE
```

If BLOCKED, do not begin the next session.

---

# 13. FINAL PHASE 10 HANDOFF

After Session 10.2 passes, create `docs/phase-10-completion-report.md` containing:

- final routes/components;
- backend APIs/services/repositories/adapters;
- database migrations and compatibility notes;
- Secure India dataset/source/version/methodology;
- interactive map/filter/ranking behavior;
- suspect-search normalization, display eligibility, abuse control, correction workflow, and privacy guarantees;
- Cyber Saathi handoff updates;
- real resume extractor/parser support matrix;
- structured parsing validation, provider/fallback behavior, review and auto-fill mapping;
- complaint-copy authorization, anonymous capability lifecycle, redaction, content, and renderer;
- automated and manual verification results;
- desktop/mobile/accessibility/i18n evidence;
- performance/resource observations;
- security review;
- known limitations;
- synthetic/mock/provider-dependent boundaries;
- exact remaining future work.

Do not mark a preview/planned handoff `available` unless its real route, API/data contract, error states, security controls, tests, and browser acceptance pass.

---

# 14. PHASE 10 DEFINITION OF DONE

Phase 10 is DONE only when:

- Secure India is an interactive, accessible, responsive explorer backed by one versioned and truthfully labelled aggregate dataset;
- summary metrics, map, rankings, hot zones, and hot crimes remain synchronized under filters;
- suspect search is accessible both from Secure India and the preserved navbar destination;
- suspect reporting remains available as a separate review-and-submit journey;
- public search is exact-match, aggregate-only, rate-limited, and restricted to eligible reviewed records;
- search never claims guilt and includes an actionable correction/false-positive pathway;
- Cyber Saathi uses confirmed typed handoffs and reports actual availability;
- Cyber Warrior resume parsing extracts real file-derived data through a bounded adapter;
- resume suggestions remain untrusted/editable until explicit confirmation;
- confirmed auto-fill preserves identity, ownership, and transactional integrity;
- identified citizens can download only their own submitted complaint copies;
- eligible anonymous citizens can download through a separate scoped capability without identity linkage;
- complaint numbers alone cannot expose full complaint contents;
- downloadable PDFs are accurate, bilingual, legible, redacted, secure, and clearly labelled as non-government prototype copies;
- existing anonymous complaint, identified complaint, tracking, evidence, Cyber Warrior, Cyber Saathi, language-switching, and admin-review behavior remains intact;
- backend tests, security regressions, frontend lint/type/build, PDF rendering, desktop/mobile/browser checks, accessibility, and documentation all pass.

The completed phase should feel like one trustworthy citizen platform:

> **Explore patterns, check a reported signal safely, contribute through a reviewed Cyber Warrior profile, and retain a secure copy of what you submitted—without confusing prototype data with government truth or weakening citizen privacy.**
