# Phase 9, Session 9.3: Authoritative Knowledge Base and Lightweight RAG

## Implemented

- Separate reviewed authoritative source pack at `backend/app/data/cyber_saathi/authoritative_knowledge/sources.json`.
- Fourteen reviewed official-public and regulatory sources with 32 semantically meaningful guidance chunks. Coverage includes financial/UPI fraud, phishing/account compromise, digital-arrest and package threats, fake banking apps and remote access, job/loan/trading scams, harassment/cyberstalking, Women and Child Safety, image misuse/blackmail, suspicious identifiers, general cyber safety, and e-commerce non-delivery/refund grievances.
- Exact per-chunk coverage tags for all 12 original priority knowledge domains plus the e-commerce consumer-grievance domain. Filtering is chunk-level rather than document-level.
- Deterministic 384-dimension Unicode-aware hashed embedding, with English, Devanagari Hindi, and Hinglish retrieval terms. This avoids a local model download, provider dependency, or translation hop.
- Explicit ingestion command that validates, cleans, chunks, embeds, hashes, and persists `knowledge_index.json`. Startup only reads the persisted small index when retrieval is requested.
- Bounded `POST /api/v1/cyber-saathi/knowledge/search` retrieval API with domain filtering, top-k cap of five, relevance threshold, latency measurement, and source-traceable metadata.
- Lexical-grounding guard in addition to vector similarity. Unrelated requests return `no_result` rather than receiving a collision-driven or invented answer.
- Real conversation routing now uses the authoritative retriever for eligible guidance turns. Each assistant turn records `grounded`, `no_result`, `deterministic_playbook`, or `not_used`; urgent financial safety remains deterministic even if the index is unavailable.
- The web conversation renders a compact official-source card with the exact chunk's title, section, version, and Learn More URL. Existing locally stored conversations without the new field remain render-safe.
- Thirty-two-case gold evaluation with all priority domains, English, Hindi, Hinglish, urgent fraud, phishing, harassment, Women/Child Safety, e-commerce, cross-domain filtering, exact chunk assertions, ambiguous/no-result, unrelated, and adversarial-invention cases.

## Source and index contract

Every persisted chunk contains a chunk ID, source ID/title/type/URL, jurisdiction, per-chunk domain tags, language, version/date, section title, normalized text, content hash, curated retrieval terms, and the 384-value embedding. The index retains source-pack hash, index schema, and embedding version for traceability. Runtime rejects stale source packs, corrupted content hashes, incompatible schemas, indexes over 500 chunks, and files over 2 MiB.

The corpus is intentionally separate from the Session 9.2 supplementary datasets. It uses reviewed guidance from the National Cybercrime Reporting Portal, CERT-In, RBI, and the Department of Consumer Affairs National Consumer Helpline. The source documents used for this expansion are staged locally under `knowledge-sources/cyber-saathi/authoritative/` and are intentionally Git-ignored; runtime uses only the committed reviewed JSON source pack and generated index. It does not query source sites at runtime and must not claim live access to them.

## Commands

```powershell
cd backend
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_knowledge
.\.venv\Scripts\python.exe -m app.services.cyber_saathi_knowledge_evaluation
```

The evaluation command persists `backend/app/data/cyber_saathi/knowledge_evaluation_report.json`, including failures, actual and expected no-result rates, exact chunk/domain correctness, false-positive/negative counts, and real nearest-rank p95 latency.

## Known coverage gaps

- This is an intentionally bounded citizen-guidance corpus, not a complete legal, banking, or emergency-procedure corpus.
- Hindi coverage includes the NCRP Hindi FAQ and CERT-In Hindi Mahila Raksha guidance. Further direct-language official material is required before claiming broad multilingual knowledge coverage.
- RBI material retains its published date and version. The assistant must not promise liability, reversal, or complaint outcomes because these depend on the applicable directions and a provider's current policy.
- The deterministic hash embedding is appropriate for this small, curated corpus but is not a replacement for a provider-backed semantic embedding model if the corpus grows substantially.
- There is no live suspect-repository, bank, police, or government-system lookup.

## Verification

- Ingestion command: passed; 14 sources, 32 chunks, and a 384-dimension persisted index (`297,988` bytes).
- Gold evaluation: 32 cases passed; retrieval relevance, source correctness, exact-chunk correctness, domain-filter correctness, and no-result correctness all `1.0`; false positives `0`; false negatives `0`; mean retrieval latency `2.904 ms`; real p95 `6.694 ms`.
- Focused knowledge/conversation/API and clarification tests: `17 passed`.
- Full backend suite: `104 passed`.
- TypeScript: passed.
- ESLint: passed.
- Production build: passed; 56 routes generated. The sandboxed build hit the known Windows `spawn EPERM`; the required direct-PowerShell rerun exited `0`.
- Browser acceptance: grounded phishing guidance rendered its official CERT-In source title, section/version, and Learn More link with no browser warnings or errors.

## Security notes

- Retrieval never calls an external source at request time and never exposes provider credentials.
- The source pack contains reviewed public guidance and URLs only; it does not contain citizen reports, evidence, or raw Session 9.2 datasets.
- Weak retrieval returns an explicit no-result response. Source metadata on the actual assistant turn makes every knowledge-backed answer traceable without claiming a live government lookup. If retrieval is unavailable, the assistant either asks for clarification or uses the separately labelled deterministic urgent-safety playbook.

## Session gate

**PASS.** Ingestion, gold evaluation, retrieval/API tests, the full backend suite, TypeScript, ESLint, and the production build passed. Session 9.4 may now start; Session 9.3 has no known implementation blocker.
