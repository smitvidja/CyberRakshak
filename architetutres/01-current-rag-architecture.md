# Current RAG Architecture

## Purpose

Cyber Saathi retrieves guidance only from a reviewed authoritative knowledge pack. The system is intentionally lightweight and bounded: it uses a persisted JSON index with deterministic sparse vectors and optional hosted multilingual dense vectors, rather than a separate vector database.

```mermaid
flowchart LR
  subgraph Authoring[Offline / explicit knowledge ingestion]
    S[Reviewed sources.json\nofficial guidance + metadata] --> C[Semantic chunking\nsection and retrieval-term validation]
    C --> E[Sparse vectors always\nOptional Gemini multilingual dense vectors]
    E --> I[knowledge_index.json\nversioned persisted hybrid index]
  end

  subgraph Runtime[FastAPI runtime]
    Q[Citizen query + inferred domain] --> V[KnowledgeService\nvalidate index hash, schema, size and chunks]
    I --> V
    V --> F[Domain filter + lexical grounding]
    F --> R[Hybrid ranking\nlexical + sparse + dense cosine]
    R --> B[Bounded context + source metadata]
  end

  B --> O[Cyber Saathi orchestration\nanswer, source cards, or safe no-result]
```

## Runtime data flow

| Stage | Current implementation |
| --- | --- |
| Source of truth | `backend/app/data/cyber_saathi/authoritative_knowledge/sources.json` |
| Index build | An explicit CLI operation in `cyber_saathi_knowledge.py`; never run on API startup |
| Index artifact | `knowledge_index.json`, limited to 500 chunks and 8 MiB |
| Embeddings | Always local deterministic sparse vectors; optional hosted multilingual dense vectors, generated only through explicit ingestion; no local model download |
| Retrieval guards | Source-pack hash, content hashes, index version, sparse/dense vector dimensions, lexical grounding, domain filter, relevance threshold, and `top_k` cap |
| Retrieval output | Matched chunks plus title, official URL, source ID/type, jurisdiction, version, domain tags, section title, relevance score, and bounded context |
| Weak retrieval | Returns `no_result`; it never invents a procedure |

## Safety behavior

```mermaid
flowchart TD
  Q[Incoming message] --> U[Understanding engine\nintent, language, urgency, domain, entities]
  U --> D{Urgent or deterministic workflow?}
  D -->|Yes| P[Deterministic safety playbook\nor confirmation / handoff state]
  D -->|No| R[Bounded authoritative retrieval]
  R --> M{Relevant sources found?}
  M -->|Yes| G[Grounded response\nor optional LLM generation]
  M -->|No| N[Safe clarification / no-result response]
  P --> A[Assistant turn]
  G --> A
  N --> A
```

Important: an unavailable or invalid index fails closed. It cannot suppress the urgent financial-safety playbook, but it can prevent normal grounded retrieval until the index is repaired.
