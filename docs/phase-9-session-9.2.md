# Phase 9, Session 9.2: Dataset Engineering and Understanding Engine

## Scope delivered

| Requirement | Implementation | Verification |
| --- | --- | --- |
| Dataset registry and purpose controls | `backend/app/data/cyber_saathi/dataset_registry.json` | Registry policy test and dataset CLI |
| Normalized multilingual schema | `NormalizedExample` plus `source_examples.json` and generated `normalized_examples.jsonl` | Schema validation, deduplication, split-leak test |
| Cyber taxonomy | `backend/app/data/cyber_saathi/taxonomy.json` | Engine and evaluation fixtures |
| Structured understanding | `UnderstandingEngine` | English, Hindi, Hinglish and ambiguity tests |
| Understanding API | `POST /api/v1/cyber-saathi/understand` | FastAPI contract test |
| Conversation integration | Existing conversation service consumes structured understanding | Session 9.1 regression suite |
| Critical entity confirmation | Amount, phone, email, UPI ID, transaction ID, URL, provider, date and time | Entity and conversation confirmation tests |
| Repeatable evaluation | `python -m app.services.cyber_saathi_evaluation` | Threshold-enforced command |

## Dataset policy

- Bitext 27K is excluded from training, evaluation, intent logic, and RAG.
- cybermetric 10K validation is held out and cannot be used for training.
- Generic chatbot, sentiment, cybersecurity corpus, 32K instructions, and cybermetric train are supplementary only.
- The authoritative citizen knowledge corpus is a separate empty slot for Session 9.3. No generic dataset is treated as citizen guidance.
- No external source dataset is checked into this repository at present. Registry locations state `not_present` instead of pretending ingestion occurred.
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

Commands:

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_dataset
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_dataset --output app\data\cyber_saathi\normalized_examples.jsonl
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_evaluation
```

## Evaluation result

Evaluation uses 10 held-out citizen fixtures plus dedicated entity and false-positive fixtures.

| Metric | Result |
| --- | ---: |
| Intent accuracy / macro F1 | 1.000 / 1.000 |
| Crime-domain accuracy / macro F1 | 1.000 / 1.000 |
| Language accuracy | 1.000 |
| Sentiment accuracy | 1.000 |
| Entity fixture accuracy | 1.000 |
| Urgent precision / recall | 1.000 / 1.000 |
| False-positive pass rate | 1.000 |
| Ambiguous input clarification | Passed |

These numbers describe the small controlled fixture set only; they are not production-model accuracy claims.

## Verification

- Focused Cyber Saathi suite: `21 passed`.
- Full backend suite: `90 passed`.
- Known warning: Starlette reports the existing `httpx` TestClient deprecation warning.
- No frontend files changed, so frontend lint/build/browser gates were not repeated for this backend-only session.

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
