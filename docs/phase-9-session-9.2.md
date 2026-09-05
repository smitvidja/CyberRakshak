# Phase 9, Session 9.2: Dataset Engineering and Understanding Engine

## Scope delivered

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Dataset registry and purpose controls | `dataset_registry.json` plus immutable observations in `dataset_inspection.json` | Registry policy test, row/schema/hash evidence, and dataset CLI |
| Controlled multilingual generation | `language_sources.json` to generated `normalized_examples.jsonl` through `generate_controlled_variants` | Required EN/HI/Hinglish variants, schema validation, deduplication, and split-leak test |
| Cyber taxonomy | `backend/app/data/cyber_saathi/taxonomy.json` | Engine and evaluation fixtures |
| Structured understanding | `UnderstandingEngine` | English, Hindi, Hinglish and ambiguity tests |
| Understanding API | `POST /api/v1/cyber-saathi/understand` | FastAPI contract test |
| Conversation integration | Existing conversation service consumes structured understanding | Session 9.1 regression suite |
| Critical entity confirmation | Amount, phone, email, UPI ID, transaction ID, URL, provider, date and time | Entity and conversation confirmation tests |
| Sentiment and confidence behavior | Conversation response strategy and focused confidence-band clarification | Response-level service tests |
| Repeatable evaluation | `python -m app.services.cyber_saathi_evaluation` | 69-case threshold-enforced command with exact entity matching |

## Dataset policy

- Bitext 27K is excluded from training, evaluation, intent logic, and RAG.
- cybermetric 10K validation is held out and cannot be used for training.
- Generic chatbot, sentiment, cybersecurity corpus, 32K instructions, and cybermetric train are supplementary only.
- The authoritative citizen knowledge corpus is a separate empty slot for Session 9.3. No generic dataset is treated as citizen guidance.
- Nine supplied datasets were inspected without ingesting them into runtime or RAG. `dataset_inspection.json` records file fingerprints, row counts, observed schemas, null counts where supported, and the policy decision used by the registry.
- Women and Child Online Safety and Online Harassment have explicit `source_required` taxonomy slots. Current examples are small manually reviewed safety fixtures, not claims of broad coverage.

## Normalization and split controls

Every normalized example retains:

```text
source_example_id
original_text
variant_text
language
script
transformation_method
source_dataset
quality_status
```

The pipeline also retains labels and an explicit `support` or `evaluation` split. It normalizes whitespace, removes duplicate variant text, and fails if variants from one source example cross the support/evaluation boundary.

Each selected source group must provide reviewed English, Hindi, and Hinglish variants. The generator currently produces 9 support and 24 held-out evaluation examples from 11 source groups; it does not blindly translate source datasets.

## Inspected source inventory

| Source | Rows | Observed fields | Decision |
| --- | ---: | --- | --- |
| Bitext 27K | 26,872 | flags, instruction, category, intent, response | Excluded |
| Generic chatbot workbook | 1,358 | session/message/response/category/intent fields | Supplementary conversation only |
| Generic intent JSON | 278 patterns across 29 intents | tag, context, patterns, responses | Supplementary intent only |
| Chat history CSV | 29 | id, session_id, role, message | Supplementary conversation only |
| Sentiment chat CSV | 584 | message, sentiment | Supplementary sentiment only |
| Cybersecurity corpus | 1,000 | text, label | Supplementary technical only |
| cybermetric train | 9,189 | system, instruction, input, output, info | Supplementary technical only |
| cybermetric validation | 1,022 | same as train | Held out validation only |
| Cybersecurity 32K | 32,569 | ds, instruction, input, output, index | Supplementary technical only |

Commands:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_dataset
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_dataset --output app\data\cyber_saathi\normalized_examples.jsonl
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_evaluation
```

## Evaluation result

Evaluation uses 39 multilingual classification fixtures, 10 exact entity fixtures, 12 false-positive fixtures, and 8 ambiguous-input fixtures: 69 cases total.

| Metric | Result |
| --- | ---: |
| Intent accuracy / macro F1 | 1.000 / 1.000 |
| Crime-domain accuracy / macro F1 | 1.000 / 1.000 |
| Language accuracy | 1.000 |
| Sentiment accuracy | 1.000 |
| Entity exact match | 1.000 |
| Urgent precision / recall | 1.000 / 1.000 |
| False-positive pass rate | 1.000 |
| Ambiguous clarification rate | 1.000 |

Extra incorrect entities fail exact-match evaluation. These numbers still describe a controlled fixture set only; they are not production-model accuracy claims.

## Verification

- Focused Cyber Saathi suite: `25 passed`.
- Dataset preparation: `9` support and `24` evaluation variants.
- Evaluation: `69` cases, all enforced metrics passed.
- Full backend suite: `94 passed`.
- Frontend TypeScript (`tsc --noEmit`): passed.
- Frontend ESLint: passed.
- Frontend production build: passed, including 56 generated routes/pages.
- Known warning: Starlette reports the existing `httpx` TestClient deprecation warning.

## Known weak domains

- Hindi/Hinglish spelling variation beyond curated markers.
- Long narratives containing several unrelated incidents.
- Unseen banks, wallets, social platforms, locations, and account-service names.
- Informal date/time expressions beyond the current deterministic patterns.
- Women and Child Safety and Online Harassment need reviewed authoritative source expansion.
- Sentiment is a response-strategy label only and must never be used as evidence of truth or criminality.

## Handoff to Session 9.3

1. Build the separate authoritative knowledge registry and ingestion path without mixing supplementary datasets into RAG.
2. Preserve `UnderstandingResult` as the retrieval query contract, including response language and confirmed entities.
3. Keep urgent deterministic safety guidance ahead of retrieval or provider calls.
4. Add reviewed sources for the two explicit missing-domain slots before claiming coverage.
5. Do not start provider/voice work or ingest all external datasets into RAG.
