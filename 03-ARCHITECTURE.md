# 03 - Architecture

CyberRakshak is a monorepo-style full-stack MVP with a Next.js frontend, FastAPI backend, PostgreSQL database, object storage, and an optional resume parser / AI adapter. The architecture is production-shaped but hackathon-appropriate.

## System Architecture

```mermaid
flowchart TD
  U[Citizen / Cyber Warrior / Admin] --> FE[Next.js frontend]
  FE --> Client[Central REST API client]
  Client --> API[FastAPI /api/v1]
  API --> Auth[Authentication and authorization]
  API --> Services[Domain services]
  Services --> DB[(PostgreSQL)]
  Services --> Store[Object storage]
  Services --> Parser[Resume parser / AI adapter]
  Services --> Notify[Notification service]
  Services --> Audit[Audit logging]
```

## Module Boundaries

- Frontend owns user interaction, responsive layout, i18n, form state, client-side convenience validation, loading, error, and success states.
- Backend owns authentication, authorization, business rules, server validation, persistence, file processing, audit logging, and API contracts.
- PostgreSQL owns durable relational application data.
- Object storage owns uploaded evidence, resumes, and certificates.
- Resume parser / AI owns extraction suggestions only; users own final confirmed profile data.

## Request Lifecycle

```mermaid
sequenceDiagram
  participant User
  participant FE as Next.js
  participant Client as API client
  participant API as FastAPI route
  participant Service
  participant Repo as SQLAlchemy/repository
  participant DB as PostgreSQL
  User->>FE: Submit form
  FE->>FE: Local validation and i18n messages
  FE->>Client: Typed request
  Client->>API: REST / JSON
  API->>API: Auth and Pydantic validation
  API->>Service: Domain command
  Service->>Repo: Query/transaction
  Repo->>DB: Persist/fetch
  DB-->>Repo: Rows
  Repo-->>Service: Entities
  Service-->>API: Result
  API-->>Client: Consistent response
  Client-->>FE: Data/error
  FE-->>User: UI state update
```

## Authentication And Authorization

```mermaid
flowchart TD
  A[Login/register form] --> B[FastAPI auth endpoint]
  B --> C[Verify credentials / create account]
  C --> D[Issue secure session or token]
  D --> E[Frontend sends authenticated requests]
  E --> F[Backend validates user, role, ownership]
  F --> G{Allowed?}
  G -->|Yes| H[Perform action]
  G -->|No| I[401 / 403 safe error]
```

Frontend route guards improve UX but are not security boundaries.

## Citizen Complaint Flow

```mermaid
flowchart TD
  A[Select anonymous or identified] --> B[Collect allowed details]
  B --> C[Incident details]
  C --> D[Location]
  D --> E[Suspect / people involved]
  E --> F[Evidence upload]
  F --> G[Review sections]
  G --> H[Declaration]
  H --> I[Create complaint]
  I --> J[Create status history]
  J --> K[Create notification]
  K --> L[Return complaint number]
```

## Evidence Upload Flow

```mermaid
flowchart TD
  A[User selects file] --> B[Frontend checks size/type]
  B --> C[FastAPI upload endpoint]
  C --> D[Authorize owner/action]
  D --> E[Validate file type and size]
  E --> F[Store file in object storage]
  F --> G[Store metadata in evidence table]
  G --> H[Return evidence id]
```

## Resume Processing Flow

```mermaid
flowchart TD
  A[Resume PDF/DOC] --> B[FastAPI upload]
  B --> C[Object storage]
  C --> D[Parser / AI extraction]
  D --> E[resume_parsing_results]
  E --> F[Frontend review]
  F --> G[User edits/confirms]
  G --> H[Profile, skills, education, experience, certifications]
```

## Error Flow

```mermaid
flowchart TD
  A[Exception or invalid input] --> B{Expected?}
  B -->|Validation| C[422 validation response]
  B -->|Auth| D[401 or 403 response]
  B -->|Conflict| E[409 response]
  B -->|Unexpected| F[500 safe response]
  F --> G[Structured server log]
```

## External And Mock Dependencies

Mock or synthetic:

- Aadhaar/eKYC labels and OTP-style verification.
- Authority status updates.
- Admin review outcomes for demo data.
- Resume parser responses if no safe parser is available.

Never integrate with live government systems, private government APIs, or real restricted identity/payment data during the hackathon MVP.
