# Phase 9, Session 9.4: Multi-LLM Brain, Prompting, and Safety Validation

## Implemented

- Provider-agnostic `MultiProviderLLMGateway` with `generate()`, validated buffered `stream()`, `health_check()`, and `healthCheck()` compatibility alias.
- Native Gemini adapter plus OpenAI-compatible Grok and NVIDIA/Nemotron adapters. Missing credentials produce `not_configured` and are skipped without delaying the citizen response.
- Configurable primary/secondary/tertiary order, model IDs, HTTPS endpoints, per-provider timeout, total deadline, retry count, token budgets, temperature profiles, and top-p.
- One retry for rate limits and server failures; timeouts, authentication/client errors, malformed output, and safety failures move directly to the next configured provider.
- Strict internal response object containing answer, confidence, urgency, suggested actions, clarification state, workflow action, source chunk IDs, and safety flags.
- Separately versioned system policy, assistant role, and output rules. Context assembly adds incident state, compacted older turns, six recent turns, current input, bounded RAG context, deterministic playbook, and output schema as distinct sections.
- Post-generation validator for required fields, allow-listed sources, unsupported government access, invented police/bank/provider actions, criminality and legal conclusions, recovery guarantees, fabricated emergency outcomes, unsafe whole-account freezing, secret-shaped output, internal-prompt disclosure, extended critical entity mismatch, urgency downgrade, workflow safety, and English/Hindi/Hinglish anonymous identity leakage.
- Real conversation integration for grounded non-critical guidance and progress-aware follow-ups, including an explicit bounded deterministic-playbook prompt section. The first urgent financial safety response, entity confirmation, reporting handoffs, and low-confidence clarification remain deterministic; later bank-contacted/what-next turns can use Gemini without repeating the first checklist.
- Ordered multi-incident state keeps separate events in one chat, queues later incidents, prevents detail mixing, records completed actions, and activates the next incident only after the current incident reaches a safe handoff state.
- Specific domain precedence prevents broad payment/bank words from swallowing KYC phishing, digital-arrest impersonation, cyberstalking, Women/Child Safety, account compromise, and e-commerce non-delivery. Audience filtering prevents child/women-specific sources from being cited for an unrelated generic KYC question.
- Reporting-mode clicks are handled as workflow actions, corrected critical entities are re-confirmed without replaying safety copy, and every generated or grounded guidance answer ends with a focused domain question.
- Safe per-turn observability: provider, model, provider-fallback flag, generation latency, and safety flags. Credentials, raw prompts, provider payloads, and provider error bodies are never returned.
- Repeatable provider-free evaluation and a server-side provider health command.

## Architecture

```text
Understanding + conversation state
        ↓
Deterministic safety/routing gate
        ↓
Authoritative retrieval (bounded chunks)
        ↓
PromptAssembler (bounded sections + response profile)
        ↓
Gemini → Grok → NVIDIA/Nemotron
        ↓ each output
Pydantic structure + SafetyValidator
        ↓ valid                     ↓ invalid/failure
Grounded conversation turn          next provider
                                    ↓ all fail
                         deterministic grounded fallback
```

Business logic calls only the gateway. Provider order changes through environment configuration; adapters translate the shared prompt package into provider-specific HTTP contracts.

## Acceptance audit

| Requirement | Status | Evidence |
|---|---|---|
| Gateway contract | Passed | The application-facing protocol exposes `generate()`, validated `stream()`, and `healthCheck()`; provider details stay behind adapters. |
| Provider configuration and routing | Passed | Provider order, models, HTTPS endpoints, credentials, retries, and timeouts are server environment settings. Gemini is live; unconfigured providers are skipped. |
| Fallback | Passed | Timeout, 429 retry, malformed output, secondary failure, tertiary success, safety rejection, and all-provider deterministic fallback have regression coverage. |
| Structured output | Passed | The eight-field response is validated with Pydantic and provider schemas; extra/malformed fields are rejected. |
| Prompt separation and context budget | Passed | Policy, role, incident, compacted history, current input, RAG, playbook, and schema are separately labelled and bounded. |
| RAG grounding | Passed | Generated citations are restricted to retrieved chunk IDs and mapped back to reviewed source metadata. |
| Hallucination and safety boundary | Passed | Authority/legal/emergency claims, criminality, guarantees, secrets, unsupported critical values, unsafe workflow actions, and multilingual anonymous identity requests are rejected. |
| Deterministic critical behavior | Passed | First-response urgent financial guidance, confirmation, low-confidence clarification, and workflow handoffs do not depend on an LLM; later progress guidance is bounded and has a deterministic fallback. |
| Secret isolation | Passed | Keys are `SecretStr`, server-only, excluded from responses/log payloads, absent from frontend configuration, and disabled during automated tests. |
| Learning artifact and evaluation | Passed | The required concepts are tied to implementation decisions and the repeatable 22-case evaluation passes its gate. |

## Configuration

Real credentials belong only in `backend/.env` or a deployment secret manager:

```text
GEMINI_API_KEY=
GROK_API_KEY=
NVIDIA_API_KEY=
```

Gemini API-key label/project metadata and Grok/Sarvam key labels are not runtime inputs. `backend/.env.example` documents every supported non-secret setting. NVIDIA remains a complete but inactive tertiary adapter while its key is blank.

The conservative defaults are `gemini-2.5-flash` and `grok-3-mini`. The configured-provider smoke gate must check these against the model catalog visible to the owner's keys; model names remain environment overrides rather than business logic.

Safe health command after adding credentials:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_llm --health-check
```

It prints provider, model, status, and latency only. It never prints credentials.

## Generation controls

- Safety/action: temperature `0.1`; predictable, but urgent financial instructions remain deterministic.
- Explanatory guidance: temperature `0.25`; modest flexibility while staying close to retrieved material.
- Normal conversation: temperature `0.4`; slightly more natural phrasing.
- Top-p: `0.9` for every profile unless configuration overrides it.
- Input estimate: maximum `3,000` tokens by default.
- Output: maximum `600` tokens.
- Recent turns: six; older-turn compact summary: 900 characters.
- Knowledge context: 2,200 characters; deterministic playbook: 1,200 characters.
- Provider timeout: 6 seconds; total gateway deadline: 8 seconds. These apply only to eligible generated guidance; urgent safety and confirmation paths remain immediate and deterministic.

The hosted Gemini smoke took about four seconds. The larger ceiling avoids premature fallback for ordinary guidance, while deterministic urgent responses preserve the first-useful-response target and the hosted call adds negligible local CPU/RAM load.

## Commands

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_llm_evaluation
.\.venv\Scripts\python.exe -m pytest tests/test_cyber_saathi_llm.py -q
```

## Evaluation

The 22-case provider-free regression set covers financial fraud, phishing, harassment, Women and Child Safety, impersonation, malware, uncertain incidents, Hindi, Hinglish, amount/transaction/UPI/helpline consistency, criminality and legal refusal, government/provider/emergency-action refusal, multilingual anonymous privacy, source integrity, secret exposure, and recovery uncertainty.

Measured results are persisted in `backend/app/data/cyber_saathi/llm_evaluation_report.json`.

## Verification

- LLM safety evaluation: `22/22` cases passed; regression accuracy, valid acceptance, unsafe rejection, and context-budget correctness were all `1.0`. Validator latency was `0.2148 ms` mean and `0.5038 ms` p95 on this run.
- Focused understanding/conversation/knowledge/provider regression gate: `86 passed`.
- Full backend suite after the 9.4.1/9.4.2 refinement: `155 passed` with one existing Starlette/httpx deprecation warning.
- TypeScript: passed with `tsc --noEmit`.
- ESLint: passed.
- Production build: passed; `56/56` static pages generated. The first sandboxed build compiled but its TypeScript worker hit Windows `spawn EPERM`; the required direct PowerShell rerun exited `0`.
- Live Gemini health: persisted `gemini-3.1-flash-lite` configuration available. The first request exposed and verified a Gemini wire-schema compatibility fix (`additionalProperties` is omitted on the wire while Pydantic still rejects extra output fields). A 9.4.1 two-turn Women/Child smoke used Gemini for the grounded first response (`2072.826 ms`) and the blocked-screenshot alternative (`2117.089 ms`); the second answer used available URL/chat/profile evidence instead of repeating the screenshot instruction.
- Live Grok health: unavailable because the auto-created Playground key secret is not recoverable from its editor and no paid API credential was supplied. The adapter remains implemented and its failure/fallback paths are covered offline.

## Security notes

- Secrets use Pydantic `SecretStr`, remain server-side, and are redacted from configuration representations.
- Provider clients do not log prompts, citizen content, credentials, raw responses, or provider error bodies.
- The frontend receives only safe generation metadata and already-reviewed source cards.
- Model output cannot mutate confirmed entities or reporting mode. Deterministic workflow code remains authoritative.
- Anonymous handoff rules are validated both before generation and after generated output.

## Known limitations

- Character-based token estimation is deliberately conservative but is not identical to each provider tokenizer.
- Buffered streaming prioritizes post-generation safety over displaying raw partial tokens.
- The validator combines structural, provenance, pattern, entity, urgency, and workflow checks; it is not a formal proof that every sentence is entailed by a source.
- Live latency, quota, and model availability vary by the owner's provider account and network; the recorded Gemini smoke is an observation, not a latency guarantee.
- No fine-tuning, local LLM, or local quantized model is used.
- Multi-incident separation is deterministic and intentionally conservative. Users can say `next incident`/`agla incident` after the active incident is ready; ambiguous references may still require a clarifying turn.
- Attached binaries are kept only in browser runtime until the complaint draft owns them. Refreshing or closing the tab intentionally discards those transient `File` objects; only safe attachment metadata remains in conversation state.
- Citizen conversations are not automatically promoted into the authoritative knowledge index. Reuse requires de-identification, quality/safety review, provenance, and a separate approved ingestion path; this prevents private or incorrect model output from becoming trusted guidance.

## Session 9.4.1 + 9.4.2 refinement

- Follow-up turns merge into the active incident instead of overwriting its original summary, confirmed entities, urgency, and completed actions.
- Related phishing/account/payment details can remain one incident, while distinct domains or explicitly different affected people enter an ordered queue.
- Exact and high-similarity repeats match the existing incident number instead of creating a new one.
- Blocked actions receive a concrete alternative. Five repeated blockers escalate the incident state; `1930` is added only for an urgent financial-loss case.
- Common noisy spellings are normalized before classification and retrieval. The tested `morfed img` / `mminor girl` input reaches Women and Child Online Safety.
- The LLM validator rejects substantial repetition of one of the latest three assistant answers and moves to the next provider or deterministic grounded fallback.
- The UI no longer shows a Gemini/provider badge under every citizen response. It shows a deterministic-playbook marker only when that distinction is safety-relevant.
- A report-preparation packet records who was affected, domain-specific required/optional fields, unavailable actions, confirmed entities, and attachment metadata.
- PDF/PNG/JPG/JPEG evidence up to 10 MB is inspected transiently, held only in browser memory, then uploaded through the existing complaint evidence API after draft creation.
- The Cyber Saathi handoff prefills the editable incident form and people/suspect data. Upload failures retain only the failed runtime files for retry and do not duplicate successfully transferred files.
- The user-facing prototype no longer calls synthetic OTP verification eKYC. It remains a local 14-digit synthetic identity + demo OTP boundary and never calls Aadhaar/UIDAI or claims government verification.

## Gate status

**GATE PASSED WITH DOCUMENTED PROVIDER LIMITATION.** Automated safety/fallback gates and the configured Gemini live path passed. Grok and NVIDIA remain inactive without usable credentials; their adapters and fallback behavior are verified without live paid calls. Do not start Session 9.5 without the owner's explicit instruction.
