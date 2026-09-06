# Phase 9, Session 9.3: Authoritative Knowledge Base and Lightweight RAG

## Implemented

- Separate reviewed authoritative source pack at `backend/app/data/cyber_saathi/authoritative_knowledge/sources.json`.
- Six official-public sources and eight semantically meaningful guidance chunks covering financial/UPI fraud, phishing/account compromise, harassment/cyberstalking, Women and Child Safety, impersonation/device-risk, suspicious identifiers, and general cyber safety.
- Deterministic 384-dimension Unicode-aware hashed embedding, with English, Devanagari Hindi, and Hinglish retrieval terms. This avoids a local model download, provider dependency, or translation hop.
- Explicit ingestion command that validates, cleans, chunks, embeds, hashes, and persists `knowledge_index.json`. Startup only reads the persisted small index when retrieval is requested.
- Bounded `POST /api/v1/cyber-saathi/knowledge/search` retrieval API with domain filtering, top-k cap of five, relevance threshold, latency measurement, and source-traceable metadata.
- Lexical-grounding guard in addition to vector similarity. Unrelated requests return `no_result` rather than receiving a collision-driven or invented answer.
- Twelve-case gold evaluation with English, Hindi, Hinglish, urgent financial fraud, phishing, harassment, Women/Child Safety, ambiguous/no-result, identifier, and general-safety cases.

## Source and index contract

Every persisted chunk contains a chunk ID, source ID/title/type/URL, jurisdiction, domain tags, language, version/date, section title, normalized text, content hash, curated retrieval terms, and the 384-value embedding. The index retains source-pack hash and embedding version for traceability.

The corpus is intentionally separate from the Session 9.2 supplementary datasets. It uses reviewed public guidance from the National Cybercrime Reporting Portal, including its financial-fraud guidance, citizen manual, FAQ, Hindi FAQ, and portal safety/identifier information. It does not query those sites at runtime and must not claim live access to them.

## Commands

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_knowledge
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_knowledge_evaluation
```

## Known coverage gaps

- This is an intentionally small baseline, not a complete legal, banking, or emergency-procedure corpus.
- Source content is English-first apart from the reviewed Hindi FAQ; additional reviewed Indian-language source material is needed before broader language coverage is claimed.
- The deterministic hash embedding is appropriate for the small, curated baseline but is not a replacement for a provider-backed semantic embedding model if the corpus grows substantially.
- There is no live suspect-repository, bank, police, or government-system lookup.

## Verification

- Ingestion command: passed; six sources, eight chunks, and a 384-dimension persisted index.
- Gold evaluation: 12 cases passed; retrieval relevance `1.0`, source correctness `1.0`, no-result correctness `1.0`, mean retrieval latency `4.871 ms`, p95 `42.955 ms`.
- Focused knowledge/API tests: `4 passed`.
- Full backend suite: `98 passed`.
- TypeScript: passed.
- ESLint: passed.
- Production build: passed; 56 routes generated. The sandboxed build hit the known Windows `spawn EPERM`; the required direct-PowerShell rerun exited `0`.

## Security notes

- Retrieval never calls an external source at request time and never exposes provider credentials.
- The source pack contains reviewed public guidance and URLs only; it does not contain citizen reports, evidence, or raw Session 9.2 datasets.
- Weak retrieval returns an explicit no-result response. Source metadata makes every returned knowledge chunk traceable without claiming a live government lookup.

## Session gate

**PASS.** Ingestion, gold evaluation, retrieval/API tests, the full backend suite, TypeScript, ESLint, and the production build passed. Session 9.4 may now start; Session 9.3 has no known implementation blocker.
