# Phase 9 Operating Memory

## Purpose

Read this before starting or resuming every Cyber Saathi session (9.1-9.6). It preserves the Phase 6 failure analysis and the project owner's historical notes so the same tooling and verification loops are not repeated.

Target 30-40 minutes per session where scope permits. This is a diagnostic timebox, not permission to skip safety, tests, visual acceptance, or honest gate reporting.

## Preserved History

- Phase 6 Sessions 6.1 and 6.2 originally took roughly 3-3.5 hours each.
- Session 6.2 contained about 150 minutes (2 hours 30 minutes) of avoidable churn.
- Chat compaction twice hid roughly 12 hours of visible conversation, but repository work remained intact.
- Session 6.2 was pushed as da249d5 (feat(warrior): add resume application flow).
- Preserved verification: 5 focused tests and 47 full backend tests passed; lint passed; build passed with 32 routes; no hydration errors or desktop/mobile overflow; persisted status UNDER_REVIEW.
- Full original record: docs/session-6.2-postmortem.md.

## Avoidable Delay Record

Times are estimates because exact per-command telemetry was not retained.

| No. | Problem | Time | Root cause | Proven solution/prevention |
| ---: | --- | ---: | --- | --- |
| 1 | No strict timebox | 20m | Diagnostics continued without a bounded plan. | Start with one verification sequence. At 35 minutes, finish or record one exact blocker and next command. |
| 2 | Sandbox helper repeatedly failed | 18m | helper_unknown_error occurred before project commands started. | After one confirmed failure, use direct C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe with approval. Do not retry the broken helper. |
| 3 | Pytest appeared silent | 12m | Windows runner emitted no incremental output. | Run focused tests first and full suite once; track the process/session to final output and exit code. |
| 4 | Next build appeared incomplete | 10m | Polling stopped after the banner. | Run once; pass only after exit 0 and successful compilation/static generation. Never restart a live build. |
| 5 | In-app browser crashed | 8m | It used the same failing helper. | After one helper failure, use the proven standalone Playwright/Chrome route for that session. |
| 6 | Image viewer failed | 5m | view_image reached the same helper. | Use the working browser screenshot path; do not alternate tools. |
| 7 | Browser API calls failed through CORS | 18m | Frontend used 127.0.0.1 while API allowed only localhost. | Frontend is http://localhost:3000; API is http://127.0.0.1:8000; CORS accepts both frontend origin forms. |
| 8 | Origins changed unnecessarily | 5m | Frontend and API were incorrectly forced to use the same host form. | Keep canonical URLs unless a demonstrated binding/port problem requires change. |
| 9 | Upload UI stayed processing although API returned 201 | 8m | Browser response was blocked by CORS. | When UI and API disagree, inspect one browser network request before changing parser, dependencies, or UI logic. |
| 10 | Resume reconfirmation violated a unique constraint | 14m | Old child rows and replacements existed in the same flush. | For replace-all unique child collections: clear, flush, then repopulate. Preserve the regression test. |
| 11 | Reused demo user returned 409 | 6m | The identity already had an active application. | Declare fixture state. Use a fresh identity for submission or load existing data for display tests. |
| 12 | Submitted page hydration mismatch | 8m | sessionStorage was read during initial/server rendering. | Initialize neutral state and read browser storage in useEffect. |
| 13 | Hidden file input hydration warning | 4m | Automation injected caret styling before hydration. | Keep hidden inputs deterministic and separate extension noise from app defects. |
| 14 | Generic browser 404 noise | 3m | Non-product requests polluted console verification. | Fail on page/hydration errors, failed product API requests, and overflow, not generic noise. |
| 15 | Lint scope was broadened | 6m | A custom command included unrelated legacy areas. | Use checked-in lint/type/build scripts unless the session explicitly changes their scope. |
| 16 | Context interruption obscured progress | 5m | Compaction occurred during verification. | Record implementation state, last pass, blocker, and next command after milestones; recover from Git/files/tests instead of redoing work. |
|  | **Total** | **150m** |  | **2 hours 30 minutes of estimated avoidable delay** |

## Mandatory Phase 9 Rules

1. Read prompts/09-Cyber-Saathi.md, this file, and normal first-read documents before every new or resumed Phase 9 session.
2. Work on one session only. Do not begin the next until the current gate honestly passes.
3. Start with a short scope matrix: requirement/state, route/component, API/data boundary, test, and manual acceptance.
4. Reuse current architecture, API clients, auth/session conventions, i18n, shared components, and citizen reporting workflows.
5. Treat relevant design references and the design system as UI, UX, interaction, state, and feature acceptance contracts, not mood boards.
6. Verify each in-scope Cyber Saathi state: entry, empty, conversation, loading, urgent safety, clarification, entity confirmation, voice, error, handoff, prefill, persistence, and language switching as applicable.
7. Preserve anonymous/identified separation; never put identity into an anonymous handoff.
8. Never claim live police, bank, Aadhaar, government, telecom, UPI, or law-enforcement access. Use approved synthetic/mock boundaries.
9. Confirm high-impact extracted entities: amounts, phones, UPI IDs, transaction IDs, providers, dates/times, URLs, and emails.
10. Return deterministic urgent-safety guidance without waiting entirely on an LLM.
11. Keep provider credentials server-side and out of browser code/storage, Git, and logs.
12. Keep orchestration lightweight and bounded: no local LLM, local Whisper, Ollama, heavyweight vector database, unnecessary service, or startup index rebuilding.
13. Use frontend http://localhost:3000 and API http://127.0.0.1:8000.
14. After one confirmed sandbox-helper failure, use direct Windows PowerShell; use Command Prompt only for a demonstrated incompatibility.
15. Run focused tests once, broader relevant tests once, repository lint/type checks once, and build once. Rerun only after a real fix.
16. Declare browser fixture state and inspect one product request when UI and API disagree.
17. Use one proven browser path for desktop/mobile verification. Do not alternate among failing tools.
18. A silent command is not a pass; capture final output and exit code.
19. Do not expand lint, test, refactor, or architecture scope during diagnostics unless required.
20. Save a milestone checkpoint so chat compaction cannot force repeated implementation.

## 30-40 Minute Session Discipline

| Window | Expected activity |
| --- | --- |
| 0-5 min | Reload prompt/memory, inspect Git and current implementation, freeze scope matrix. |
| 5-25 min | Implement the smallest coherent scope with focused tests. |
| 25-35 min | Run bounded verification and required visual/interaction checks. |
| 35-40 min | Review diff and record results; commit/push only when requested and gates pass. |

If a gate cannot pass in the budget, preserve completed work and report:

```text
Current implementation state:
Last confirmed passing check:
Exact blocker and evidence:
Single next command/action:
Files currently changed:
```

## Attached Source Notes Preserved

- Prompt files and project Markdown documents define product and engineering intent.
- The relevant design folder defines the required visual, UX, interaction, state, and feature outcome.
- Phase 6 Cyber Warrior work used design/cyber_warrior as its non-negotiable acceptance reference.
- Repeated environment experimentation, silent commands, browser-tool switching, origin changes, and undeclared fixtures caused most avoidable delay.
- Repository checkpoints and committed work are the recovery source when chat history is unavailable.

These lessons apply to Phase 9 execution without treating stale Phase 6 scope as current work.
