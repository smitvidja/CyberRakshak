# 04 - Backend

The backend is the primary API and security boundary. It uses FastAPI, Pydantic, SQLAlchemy, Alembic, PostgreSQL, and object storage.

## Backend Structure

```text
backend/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── security.py
│   │   └── logging.py
│   ├── models/
│   ├── schemas/
│   ├── api/v1/
│   ├── services/
│   ├── repositories/
│   └── utils/
├── alembic/
├── tests/
└── requirements.txt
```

## Request Lifecycle

```mermaid
flowchart TD
  A[FastAPI route] --> B[Auth dependency]
  B --> C[Pydantic request schema]
  C --> D[Service function]
  D --> E[Repository / SQLAlchemy]
  E --> F[(PostgreSQL)]
  D --> G[Object storage if files]
  D --> H[Notification / audit side effects]
  H --> I[Pydantic response schema]
  F --> I
```

## API Domains

- `auth.py`: register, login, current user, logout/session behavior.
- `users.py`: user profile basics.
- `complaints.py`: citizen complaint drafts, submission, tracking, status.
- `complaint_categories.py`: category list.
- `suspects.py`: public suspect reports.
- `evidence.py`: evidence upload and metadata.
- `cyber_warriors.py`: profile, skills, education, experience, certifications.
- `warrior_applications.py`: application draft, review, submission.
- `resume.py`: resume upload, parsing result, confirmation support.
- `warrior_reports.py`: Cyber Warrior reporting and tracking.
- `notifications.py`: user notifications.
- `admin.py`: lightweight review/moderation.

## Business Logic Rules

- Routes coordinate HTTP concerns only.
- Services enforce business rules and transactions.
- Repositories own database queries.
- Pydantic schemas validate requests/responses.
- SQLAlchemy models represent persistence.
- Audit logging is written from services when meaningful state changes occur.

## Anonymous Complaints

The backend must not attach an authenticated user to an anonymous complaint.

```mermaid
flowchart TD
  A[Create complaint request] --> B{is_anonymous}
  B -->|true| C[Require user_id null]
  B -->|false| D[Require authenticated user]
  D --> E[Set user_id to current user]
  C --> F[Persist complaint]
  E --> F
```

## File Handling

- Validate MIME type, extension, and size.
- Store files in object storage.
- Store metadata in `evidence`, `cyber_warrior_profiles`, `resume_parsing_results`, or certification fields as appropriate.
- Never expose object storage credentials to the frontend.

## Resume Parser

The parser service returns untrusted structured suggestions. Save suggestions to `resume_parsing_results`; update final profile tables only after user review and confirmation.

## Authorization

Enforce server-side:

- Citizens can access only their own identified complaints.
- Anonymous complaint identity must remain unavailable.
- Cyber Warriors can edit their own profile/application/reports only.
- Admins can perform approved lightweight review actions.
- Users cannot modify audit logs directly.
- Evidence access must check ownership or admin role.

## Error Handling

Use a consistent response shape:

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

Do not expose stack traces or secrets in API responses.
