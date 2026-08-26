# 06 - API

The API is versioned REST over JSON, served by FastAPI under `/api/v1`. Backend validation and authorization are mandatory.

## Conventions

- `GET`: retrieve.
- `POST`: create/submit.
- `PATCH`: partial update.
- `PUT`: full replacement only when needed.
- `DELETE`: delete only where retention policy allows.

Success shape:

```json
{
  "success": true,
  "data": {},
  "message": "Operation completed successfully"
}
```

Error shape:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request",
    "details": {}
  }
}
```

## Endpoint Domains

```text
/api/v1/auth
/api/v1/users
/api/v1/complaints
/api/v1/complaint-categories
/api/v1/evidence
/api/v1/suspects
/api/v1/cyber-warriors
/api/v1/warrior-applications
/api/v1/resume
/api/v1/warrior-reports
/api/v1/notifications
/api/v1/admin
```

## FE -> API -> BE Flow

```mermaid
sequenceDiagram
  participant FE as Frontend form
  participant Client as API client
  participant API as FastAPI endpoint
  participant Schema as Pydantic schema
  participant Service
  FE->>Client: submit typed payload
  Client->>API: REST request
  API->>Schema: validate
  Schema->>Service: safe data
  Service-->>API: result/error
  API-->>Client: consistent response
  Client-->>FE: render state
```

## Complaint APIs

Expected resources:

- `GET /complaint-categories`
- `POST /complaints/drafts`
- `PATCH /complaints/{id}`
- `POST /complaints/{id}/submit`
- `GET /complaints/my`
- `GET /complaints/track/{complaint_number}`
- `GET /complaints/{id}`
- `GET /complaints/{id}/status-history`

Anonymous create/submit must allow no user identity. Identified create/submit must require authentication.

## Evidence APIs

- `POST /evidence`
- `GET /evidence/{id}`
- `DELETE /evidence/{id}` only if allowed by ownership and retention rules.

Uploads must validate size, type, ownership, and target entity.

## Suspect APIs

- `POST /suspects/reports`
- `GET /suspects/reports/{id}`
- `GET /suspects/reports/my`

Language must distinguish reported suspects from legally confirmed criminals.

## Cyber Warrior APIs

- `POST /cyber-warriors/profile`
- `GET /cyber-warriors/me`
- `PATCH /cyber-warriors/me`
- `POST /resume/upload`
- `GET /resume/parsing-results/{id}`
- `POST /resume/parsing-results/{id}/confirm`
- `POST /warrior-applications`
- `POST /warrior-applications/{id}/submit`
- `GET /warrior-applications/my`
- `POST /warrior-reports`
- `PATCH /warrior-reports/{id}`
- `POST /warrior-reports/{id}/submit`
- `GET /warrior-reports/my`
- `GET /warrior-reports/{id}`

## Admin APIs

Admin APIs remain lightweight:

- list/review complaints
- review suspect reports
- approve/reject Cyber Warrior applications
- inspect audit/activity summaries

No FIR, investigator assignment, or police hierarchy APIs in MVP.

## Auth And Authorization

```mermaid
flowchart TD
  A[Request] --> B{Public endpoint?}
  B -->|Yes| C[Validate payload]
  B -->|No| D[Authenticate]
  D --> E[Check role]
  E --> F[Check ownership/resource access]
  F --> G{Allowed?}
  G -->|Yes| C
  G -->|No| H[401 / 403]
```

Frontend route guards never replace backend authorization.

## Synthetic Identity Prototype

The local-only mock eKYC flow is intentionally separate from real identity providers:

- `POST /api/v1/auth/mock-identity/request-otp` accepts a supplied `demo_identity_id`, checks the synthetic database record, and returns only a masked linked demo mobile and expiry. It does not send an SMS or return an OTP.
- `POST /api/v1/auth/mock-identity/verify-otp` accepts that ID plus a six-digit demonstration OTP and an optional `role` intent limited to `CITIZEN` or `CYBER_WARRIOR`. It consumes the requested OTP once, creates or reuses a role-specific local prototype account, returns an access token, and returns synthetic autofill data. It never permits this mock flow to issue an administrator session.
- `PUT /api/v1/users/me/profile` saves editable profile fields. For a mock-verified user, the server rejects a changed `full_name`; the primary mobile is not an input and remains immutable.

These endpoints accept only the supplied non-real demo identities. They must never call Aadhaar, UIDAI, mobile carriers, or any government service.

## Complaint Date and Anonymous Category Rules

`incident_at` on create and update must not be later than the server's current UTC time. Anonymous complaint drafts are allowed only for the `WOMEN_AND_CHILD_SAFETY` category; all other categories require an authenticated identified user.