# Session 6.2 Postmortem

## Purpose

This document records the avoidable delays from Phase 6, Session 6.2 so they are not repeated in Sessions 6.3, 6.4, 7, or 8.

The user-observed elapsed time was roughly 3.5 hours. Exact per-issue telemetry was not retained, so the figures below are rounded estimates. The estimated avoidable debugging and tooling churn totals about 150 minutes; normal implementation and final verification account for the remaining time.

## Delay Breakdown

| No. | Problem | Estimated avoidable time | Root cause | Resolution used | Mandatory prevention |
| ---: | --- | ---: | --- | --- | --- |
| 1 | No strict timebox or stop condition | 20 min | Diagnostics continued one issue at a time without a bounded verification plan. | Reduced the remaining work to one browser gate, one backend suite, lint, build, review, commit, and push. | Start every session with a 40-minute execution budget and one-pass verification plan. Stop and report the exact blocker instead of opening another loop. |
| 2 | Repeated Windows sandbox helper failures | 18 min | The default helper repeatedly failed with `helper_unknown_error: setup refresh had errors` before the project command started. | Used `C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe` directly with the required approval. | On this host, after the first helper failure, immediately use the proven direct PowerShell path. Never retry the broken helper repeatedly. |
| 3 | Full Pytest command appeared silent | 12 min | The Windows runner returned no incremental output, making a live command look hung. | Captured the actual process/session and waited for its exit result; final result was `47 passed`. | Run focused tests first, then the full suite once. Track the returned process/session and judge only by its exit code and final output. |
| 4 | Next production build appeared incomplete | 10 min | Earlier polling was interrupted after the script banner and no completed build result was captured. | Ran one clean `npm run build` and captured the complete route output and exit code. | A build passes only when the command exits `0` and Next reports successful compilation/static generation. Do not repeatedly restart a live build. |
| 5 | In-app browser runtime crashed | 8 min | The browser plugin used the same failing Windows runtime helper. | Used the installed Chrome executable through Playwright for one controlled visual check. | If the in-app browser fails once due to the runtime helper, use standalone Playwright immediately. Do not alternate repeatedly between browser tools. |
| 6 | Local image viewer failed | 5 min | `view_image` hit the same Windows helper failure. | Used browser screenshots and direct image output for visual inspection. | After one `view_image` helper failure, use the already-working screenshot path for the rest of the session. |
| 7 | Browser API calls failed because of CORS | 18 min | The frontend was opened on `127.0.0.1:3000`, while backend CORS initially allowed only `localhost:3000`. | Backend CORS now accepts both local frontend origins. | Canonical setup is frontend `http://localhost:3000` and backend `http://127.0.0.1:8000`. Keep both local frontend origins in backend CORS; do not unnecessarily move the frontend to `127.0.0.1`. |
| 8 | Local origin setup was changed unnecessarily | 5 min | The frontend and backend origins were treated as if both needed to use `127.0.0.1`. | Restored the architecture rule: browser frontend uses `localhost`; API can remain on `127.0.0.1`. | Preserve the existing dev URLs unless a real port/binding failure proves a change is necessary. |
| 9 | Resume upload looked stuck even though the API worked | 8 min | Direct API upload returned `201`, but the browser request was blocked by CORS and remained in the processing UI. | Verified the API independently, fixed CORS, restarted only the API, and reran the browser flow once. | When UI and API disagree, inspect one browser network request before changing dependencies, parser logic, or UI state. |
| 10 | Reconfirming a resume caused a unique-constraint failure | 14 min | Existing warrior skills were deleted and new rows inserted in the same flush order, violating `uq_warrior_skills_pair`. | Cleared related collections, flushed deletions, then inserted confirmed replacements. Added a regression test for confirming a second resume with the same skill. | For replace-all child collections with unique constraints: clear, flush, then repopulate. Keep the regression test. |
| 11 | Reusing the same demo user returned application conflict | 6 min | The visual journey attempted to submit another application for a user who already had an active application, correctly returning `409`. | Reused the existing submitted application for the final status-screen check. | Visual tests must start from a declared fixture state. Use a fresh identity for submission tests or load the existing application for display tests. |
| 12 | Submitted page had a hydration mismatch | 8 min | `sessionStorage` was read during initial React state creation, so server and client markup differed. | Initialized neutral state and loaded session data inside `useEffect`. | Never read `window`, local storage, or session storage during server render or initial state evaluation in App Router components. |
| 13 | Hidden file input produced a caret-style hydration warning | 4 min | Browser automation injected `caret-color: transparent` before React hydration. | Made the hidden input's caret style deterministic. | Keep hidden upload inputs deterministic and exclude extension-injected DOM noise before treating it as an application defect. |
| 14 | Generic browser `404` noise distracted verification | 3 min | Non-product development/browser requests appeared in console output. | Filtered only confirmed generic `404` noise while still failing on hydration and page errors. | Define the browser failure criteria before the run: page errors, hydration errors, failed product API requests, and overflow. |
| 15 | Lint scope was broadened and exposed unrelated legacy errors | 6 min | A diagnostic lint invocation checked feature areas outside the repository's established script scope. | Restored and used the repository command `npm run lint`; did not disable rules or refactor unrelated features. | Never change verification scope mid-session unless the session requires it. Use the checked-in scripts as the contract. |
| 16 | Context interruption made completed work look lost | 5 min | A long-running task was compacted/interrupted while verification was active, obscuring the current checkpoint. | Recovered from Git status, existing files, test results, and generated screenshots instead of redoing implementation. | After each major milestone, record a one-line checkpoint: implementation state, last passing check, current blocker, and next single command. |

## Session 6.3 Operating Rules

1. Use the existing repository state; do not redo Sessions 6.1 or 6.2.
2. Canonical local URLs are frontend `http://localhost:3000` and API `http://127.0.0.1:8000`.
3. Use direct Windows PowerShell after the first confirmed sandbox-helper failure; do not retry the failing helper.
4. Read the Session 6.3 prompt and inventory only its in-scope `design/cyber_warrior/` references before coding.
5. Build a short route/component/API coverage checklist from those references. Screenshots are acceptance contracts, not mood boards.
6. Reuse the existing warrior API client, session helpers, application data, layout, and backend boundaries.
7. Use a known fixture state for browser verification. Do not repeatedly submit the same demo application.
8. Run focused tests once, full backend tests once, `npm run lint` once, and `npm run build` once.
9. Run one desktop and one mobile browser acceptance pass. Do not iterate between multiple broken browser/image tools.
10. At 35 minutes, either finish review/commit/push or report one exact blocker. Do not continue an unbounded diagnostic loop.

## Session 6.2 Final Verified State

- Focused Cyber Warrior tests: passed.
- Full backend suite: `47 passed`.
- Frontend lint: passed.
- Production build: passed with 32 routes.
- Browser acceptance: zero hydration errors and no desktop/mobile overflow.
- Persisted application status: `UNDER_REVIEW`.
- Commit: `da249d5`.
- Push: `origin/main` successful.
