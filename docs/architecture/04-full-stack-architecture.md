# Full Frontend → Backend → Database Architecture

## Whole application connection map

```mermaid
flowchart LR
  U[Citizen / Cyber Warrior / Admin] --> FE[Next.js App Router\nReact + TypeScript + Tailwind + next-intl]

  subgraph Frontend[Frontend]
    FE --> R[Locale routes and feature components]
    R --> ST[React state, form validation\nloading / error / review UI]
    R --> I18N[English and Hindi message catalogs]
    ST --> AC[Central typed API client\nfrontend/lib/api]
    R --> GS[Small browser-only draft/session helpers]
  end

  AC --> API[FastAPI /api/v1]

  subgraph Backend[Backend security and business boundary]
    API --> AU[Authentication, role and ownership checks]
    API --> PS[Pydantic request / response schemas]
    PS --> SV[Domain services\ncomplaints, evidence, Cyber Saathi,\nwarriors, reports, notifications]
    SV --> RP[Repositories + SQLAlchemy]
    SV --> OS[Object-storage adapter]
    SV --> AI[Safe parser / Cyber Saathi RAG + optional LLM]
    SV --> AL[Audit and notification services]
  end

  RP --> PG[(PostgreSQL)]
  OS --> OB[(Object storage)]
  AI --> KI[Reviewed knowledge index]
  AI -. optional, server only .-> LP[Configured LLM providers]
```

## Standard request lifecycle

```mermaid
sequenceDiagram
  participant U as User
  participant FE as Next.js page / feature
  participant C as Typed API client
  participant A as FastAPI route
  participant S as Domain service
  participant R as Repository
  participant D as PostgreSQL
  participant O as Object storage

  U->>FE: Interact with a form or dashboard
  FE->>FE: Client convenience validation and UI state
  FE->>C: Typed domain request
  C->>A: REST JSON or multipart upload
  A->>A: Authenticate, authorize and validate Pydantic schema
  A->>S: Business command
  S->>R: Query / transaction
  R->>D: Read or persist relational data
  opt File upload
    S->>O: Store binary file
    S->>R: Store object metadata and ownership
  end
  D-->>R: Rows
  R-->>S: Domain entities
  S-->>A: Domain result
  A-->>C: Standard success or safe error response
  C-->>FE: Typed data or error
  FE-->>U: Updated UI, step, status, or validation message
```

## Data ownership

| Data type | Owner / location | Access rule |
| --- | --- | --- |
| User, complaint, status timeline, report, notification and audit data | PostgreSQL | Enforced through backend roles and ownership checks |
| Evidence, resumes, certificates and related binary uploads | Object storage | Frontend accesses only authorized backend endpoints; object-store credentials stay server-side |
| File metadata, checksum, owner and target linkage | PostgreSQL | Stored with the relevant domain entity; never treated as a substitute for file authorization |
| Cyber Saathi reviewed source pack and index | Versioned files in the backend repository/runtime image | Read-only at normal API runtime; explicit rebuild only |
| Cyber Saathi persisted conversation | PostgreSQL `cyber_saathi_conversations` | Saved only after storage consent, redacted, expires after 30 days, and is never an automatic training cache |
| Browser-only convenience state | React state, session storage, or local storage | Not a security boundary and not the canonical source when server persistence applies |

## Complaint and Cyber Saathi handoff

```mermaid
flowchart TD
  C[Cyber Saathi conversation] --> D{Report-ready deterministic checks pass?}
  D -->|No| Q[Ask focused question / confirm critical entity]
  D -->|Yes| P[Create report prefill\nexact category, confirmed facts, attachments metadata]
  P --> F[Next.js complaint flow\nIncident → People → Review → Declaration]
  F --> V{Identified guest needs verification?}
  V -->|Yes, only at final submit| O[Local synthetic OTP verification]
  V -->|No| S[Create or update complaint draft]
  O --> S
  S --> E[Upload evidence binary to object storage\nand metadata to PostgreSQL]
  E --> T[Submit complaint and write status history / notification]
```

The frontend is responsible for clarity and user flow. The backend remains the trust boundary for authorization, state transitions, safety rules, data validation, uploads, and all durable writes.
