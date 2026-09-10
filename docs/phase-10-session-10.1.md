# Session 10.1 Completion Report

Interactive Secure India + Search Suspect Reports.

## Scope matrix outcome

| Requirement / state | Route / component | API / data boundary | Automated verification | Manual acceptance |
| --- | --- | --- | --- | --- |
| Hero and summary | `SecureIndiaDashboard` hero | `GET /secure-india/summary` source block | source/label test | PASS - hierarchy matches reference, synthetic label present |
| Filters | crime type, State/UT, city, period, count/per-lakh | bounded, validated query | invalid-filter test (5 cases) | PASS - keyboard, deep link, reset |
| Interactive map | proportional-symbol SVG | projected aggregate coordinates only | projection + containment audit | PASS - hover, focus, Enter, tap |
| Legend | legend rendered from API bins | `legend` in the same response | legend/bucket agreement test | PASS - follows the active view |
| Rankings | ranked table | same ordered snapshot | consistency + determinism tests | PASS - stays synchronized |
| Hot zones | zone cards | same snapshot, `zone` names | consistency test | PASS - selecting focuses the map |
| Hot crimes | crime cards | same snapshot | totals/percent test | PASS - links to prevention guides |
| Loading/error/empty | all regions | typed safe errors | derived-loading design | PASS - retry works, no stale figures |
| Suspect search | `/suspects/search` + Secure India band | exact normalized lookup | normalization/privacy/abuse tests | PASS - match, no-match, correction |
| Suspect report | `/suspects/report` | existing create/evidence APIs | existing suite green | PASS - prefill without auto-submit |
| Cyber Saathi handoff | action card | typed workflow handoff | handoff tests | PASS - confirmed identifier only |
| i18n / accessibility | all new states | EN/HI namespaces | parity + placeholder checks | PASS - both locales, 1280 and 390 |

## Implemented

- `GET /secure-india/metadata` and `GET /secure-india/summary`, backed by a versioned synthetic
  snapshot with server-side filtering, aggregation, projection, ranking and legend derivation.
- `POST /suspects/search` - exact-match, `VERIFIED`-only, aggregate-only, rate-limited public
  lookup that takes the identifier in the request body.
- `POST /suspects/corrections` plus admin list/status endpoints for the false-positive pathway.
- `/[locale]/secure-india` rebuilt from a static screenshot into a real interactive explorer.
- `/[locale]/suspects/search` as a new route, with the navbar suspect destination preserved.
- Cyber Saathi `secure_india` and `search_suspect_reports` moved to `available`, carrying a
  confirmed identifier only.

## Work completed in this session on top of the inherited working tree

The tree already contained a working first pass. This session:

1. Replaced hand-placed `x`/`y` pixel pairs with real `lon`/`lat` plus a declared projection,
   and moved projection into the service (snapshot `1.0.0` -> `1.1.0`).
2. Added API-derived `legend` bins and per-region `bucket`, so map, legend and cards cannot
   disagree about a threshold - previously there was no legend at all.
3. Surfaced the snapshot's `zone` names, which were present in the data but unused.
4. Added URL deep-linking and restore for filter state, plus a reset control (both missing).
5. Added hover/focus tooltips, a graduated legend, rank badges, intensity meters, a breadcrumb
   and a bilingual hero line, closing the gap to the reference composition.
6. Replaced effect-driven filter state with `useSyncExternalStore` over the query string, and
   made `loading` derived - removing two `react-hooks/set-state-in-effect` errors and any
   possibility of a hydration mismatch.
7. Added a request debounce that also removes a redundant aborted API call on every deep link.
8. Redrew the national outline from 76 to 116 projected points and corrected the Coromandel
   coast, which had been leaving Chennai plotted in the sea.
9. Added 7 backend contract tests and mutation-tested them.
10. Removed the dead preview/screenshot CSS and message keys left behind by the old page.

## Files changed

32 tracked files modified, 15 new files. Principal additions:

```text
backend/app/api/v1/secure_india.py
backend/app/services/secure_india_service.py
backend/app/schemas/secure_india.py
backend/app/data/secure_india/snapshot.json
backend/app/core/public_rate_limit.py
backend/alembic/versions/a1b2c3d4e5f6_add_suspect_search_and_corrections.py
backend/tests/test_secure_india_and_suspect_search.py
frontend/features/secure-india/SecureIndiaDashboard.tsx
frontend/features/suspects/SuspectSearch.tsx
frontend/app/[locale]/suspects/search/page.tsx
frontend/lib/api/secure-india.ts
frontend/lib/suspect-handoff.ts
docs/secure-india-dataset.md
```

## Architecture and data decisions

- **Secure India has no database access.** The service reads a cached snapshot file and owns
  all calculation. Complaint, reporter, location and evidence rows therefore cannot reach the
  public map by construction rather than by filtering discipline.
- **One response drives every surface.** Metrics, map, legend, rankings, hot zones and hot
  crimes all come from a single `summary` call.
- **Geometry is data.** Coordinates live in the snapshot as lon/lat with a declared projection
  window; the service projects, the frontend renders.
- **The query string owns filter state**, consumed via `useSyncExternalStore` with the default
  view as the server snapshot, so the route still prerenders and cannot mismatch on hydration.
- **One normalization helper** serves report creation, public search and corrections.

## API and security contracts

Documented in `06-API.md` and `08-SECURITY.md`. Key guarantees:

- identifiers travel in a request body, never a URL, and never reach browser history;
- only `VERIFIED` reports contribute to a public match;
- responses carry masked identifier, match state, a count capped at 5, and a disclosure code;
- no-match copy negates safety rather than asserting it, and a match never asserts guilt;
- corrections store an HMAC fingerprint, never the raw identifier, and hold no reporter link;
- every Secure India response is labelled `SYNTHETIC` with version, period and methodology.

## Tests run

- `pytest -q` (full backend suite)
- `pytest tests/test_secure_india_and_suspect_search.py`
- mutation checks against three deliberately broken service behaviours
- `npx tsc --noEmit`
- `npm run lint` plus an explicit `eslint features/` pass
- `npm run build`
- 43-check live browser acceptance script (Chrome via playwright-core)
- EN/HI parity, key-existence and placeholder-consistency check

## Test results

| Gate | Result |
| --- | --- |
| Backend suite | **293 passed** (was 286; 7 added) |
| Focused Secure India / suspect tests | **12 passed** |
| Mutation checks | 3/3 caught by the intended test, green after restore |
| TypeScript | 0 errors |
| Lint (`app components lib`) | clean |
| Lint (`features/secure-india`, `features/suspects`, `lib`) | clean |
| Production build | success, 58 static pages, both locales |
| Live browser acceptance | **43/43 pass** |
| EN/HI parity | 0 drift, 0 placeholder mismatches |

## Manual and visual verification

Run against the production build at `127.0.0.1:3000` with a fresh backend.

Verified: default desktop view; state/crime/period/view changes; reset; deep-link restore of
all filters; hover, keyboard focus and Enter on map markers; ranked-table selection driving the
same selection; mobile tap selection without hover; both locales; Secure India to suspect
search; no-match result copy; navbar suspect destination.

Two defects were found by measurement rather than by eye and then fixed:

- `isPointInFill` containment showed **Chennai plotted outside the coastline**; the Coromandel
  edge was corrected until all 10 cities fall inside.
- Box measurement showed the **Reset control wrapping to a second row**; the filter grid was
  widened to six columns.

A first attempt at a white text halo made the rank numbers *less* legible (stroke far too heavy
for a 2.6px glyph). It was reverted in favour of a raised minimum radius, confirmed by
screenshot.

Screenshots captured: desktop default, mobile 390, Hindi desktop, suspect search, plus map and
filter close-ups.

## Performance observations

Development-machine observations, not SLAs:

- production build: compiled in ~8-10s, 58 static pages in ~5s;
- backend suite: 293 tests in ~61s;
- `summary` is served from an `lru_cache`d snapshot with no database round trip;
- filter changes are debounced at 60ms, so a rapid sequence issues one request.

## Accessibility and i18n

- Every marker is a focusable control whose accessible name carries city, state and value.
- Hover and keyboard focus surface identical facts; the ranked table is a full non-map
  equivalent with the same values and selection semantics.
- Colour is never the sole carrier of meaning: radius, rank number and exact value accompany it.
- The ranked table is present at every breakpoint; nothing is hover-only.
- Reduced-motion users get no animated skeleton, transitions or smooth scrolling.
- No horizontal overflow at 1280 or 390 in either locale.
- All new strings exist in English and Hindi with identical placeholders.

## Known limitations

- Mumbai and Pune are close enough that their symbols overlap and Mumbai's rank number can be
  covered. Inherent to a proportional-symbol map; both remain hoverable, selectable and listed
  in the ranked table.
- `trend_percent` is static per city and does not recompute per filter. It is labelled as a
  synthetic trend.
- Period filters are fixed multipliers, not real per-period observations.
- The rate limiter is in-process, which suits a single-process prototype but would need shared
  state behind multiple workers.
- The client key for rate limiting is the peer address, so it would need proxy-aware handling
  before any real deployment behind a load balancer.
- `/favicon.ico` returns 404 app-wide. Pre-existing, unrelated to this session, not fixed here.
- 8 `react-hooks/set-state-in-effect` errors remain in `features/cyber-warriors/*`. Pre-existing
  Phase 6 code, out of scope; the repository lint script does not cover `features/`.

## Synthetic / mocked / provider-dependent pieces

- The entire Secure India dataset is synthetic. See `docs/secure-india-dataset.md` for identity,
  methodology, limits and the contract required before any real source is used.
- Suspect search reads real prototype report rows, but only `VERIFIED` ones and only as a
  bounded count.
- No live police, government, bank, UIDAI or telecom system is contacted anywhere in this work.

## Handoff to next session

Session 10.2 covers real resume parsing/auto-fill and the downloadable complaint copy. Nothing
in that scope was started: `MockResumeParser` is still the runtime parser and no complaint-copy
endpoint or PDF renderer exists.

Useful context: `normalize_identifier` is the established pattern for a single shared
server-side canonicalization helper, and `SecureIndiaService` shows the file-backed, no-database
service shape. The anonymous complaint-copy capability in 10.2 must not reuse the suspect
handoff `sessionStorage` pattern - it needs server-side storage of a hashed capability.

## Gate status

**PASS**
