# CyberRakshak

A bilingual (English/Hindi) cybercrime reporting and cyber-volunteer prototype for
Indian users.

> **This is a prototype, not a government service.** It is not affiliated with,
> endorsed by, or connected to any government body. It does not perform real
> Aadhaar/PAN verification, does not send real OTPs, and does not connect to any
> live government system. See [Mocked dependencies](#mocked-dependencies) for
> exactly what is simulated.

---

## What it does

**Citizens** can report a cyber incident — anonymously or with a verified identity —
attach evidence, submit, and track progress with a reference number.

**Cyber Warriors** are citizen volunteers who apply (with a résumé), get reviewed,
then submit reports about suspicious activity from their own dashboard.

Implemented journeys:

- Home / service overview with six report categories.
- Anonymous complaint reporting (no identity attached at any point).
- Identified complaint reporting via mock identity verification.
- Complaint draft → evidence upload → review → submit → reference number → tracking.
- "My reports" listing.
- Public suspect reporting.
- Cyber Warrior onboarding, résumé upload + reviewed parsing, application submission.
- Warrior dashboard, report submission and tracking, profile, leaderboard, badges.
- A Resources / awareness section with ten scam-awareness posters and a PDF guide.
- Notifications, lightweight admin review, and audit logging.

Every user-facing string exists in both English and Hindi.

---

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js (App Router), TypeScript, next-intl |
| Backend | FastAPI, SQLAlchemy, Alembic, Pydantic |
| Database | PostgreSQL |
| File storage | Local filesystem (see [limitations](#known-limitations)) |

---

## Local setup

### Option A — everything in Docker

Prerequisites: Docker.

```bash
docker compose up --build
```

Frontend at http://localhost:3000/en, backend at http://localhost:8000/health. The
backend container applies migrations and seeds reference data on start, so there is
nothing else to run. If a native PostgreSQL already owns port 5432, use
`POSTGRES_PORT=5433 docker compose up --build` instead.

These are the same images that deploy to Render — see [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) §11.

### Option B — native, with PostgreSQL in Docker

Prerequisites: Node.js, Python 3.11+, Docker (for PostgreSQL).

#### 1. Environment files

```powershell
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item backend/.env.example backend/.env
```

The defaults work for local development as-is. Never commit a real `.env`.

#### 2. Database

```powershell
docker compose up -d postgres
```

#### 3. Backend

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Set-Location backend
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe ../database/seeds/seed_reference_data.py
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --reload-dir app --host 127.0.0.1 --port 8000
```

The seed step is required — without it, complaint categories will be empty.

`--reload-dir app` matters, not just style: without it, uvicorn watches the whole `backend/`
working directory by default - including `.venv/` (every installed package) and `storage/`
(every file a user uploads at runtime, e.g. a resume or evidence file). Watching that many/that
volatile a set of files is what made `--reload` unreliable (silently missing real source edits,
or restarting mid-request when someone uploaded a file). Scoping it to `app/` - the only
directory with actual source code - fixes both.

Backend runs at http://127.0.0.1:8000 (`/health`, and API docs at `/docs`).

#### 4. Frontend

```powershell
Set-Location frontend
npm install
npm run dev
```

Open http://localhost:3000/en (or `/hi` for Hindi).

#### Checks

```powershell
# backend, from backend/
.venv/Scripts/python.exe -m pytest

# frontend, from frontend/
npm run lint
npm run build
```

---

## Demo credentials

Synthetic demo identities for the mock verification flow are in
[`DEMO-CREDENTIALS.md`](DEMO-CREDENTIALS.md), along with which are unused and
reserved for a first-time-journey walkthrough.

These are entirely fabricated — not real people, and not real Aadhaar numbers.

---

## Mocked dependencies

Simulated, and clearly labelled as such in the UI:

| Dependency | Status | Detail |
|---|---|---|
| Aadhaar / identity verification | **Mocked** | A fixed set of synthetic demo identities. No UIDAI or government system is contacted. |
| OTP delivery | **Mocked** | No SMS is sent. OTPs are fixed per demo identity and listed in `DEMO-CREDENTIALS.md`. The API never returns the OTP or the full mobile number. |
| Résumé parsing | **Static mock** | Returns the same synthetic sample data regardless of the uploaded file. There is no text-extraction or AI parsing. The human review step is real. |
| Authority / police status updates | **Not implemented** | No real authority receives reports. Status changes only via the in-app admin role. |
| Admin review decisions | **Real but in-app only** | Genuinely enforced server-side, but decisions are made inside this prototype, not by any external body. |
| Leaderboard peers | **Demo data** | Other warriors on the leaderboard are synthetic sample rows; your own row is computed from real activity. This is disclosed on the page. |
| Payments | **Not present** | No payment handling of any kind. |

---

## Known limitations

- **Uploaded files are stored on the local filesystem.** On hosts with ephemeral
  storage, uploads are lost on restart/redeploy while their metadata rows remain.
  See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) §5.
- **Résumé parsing is not real** (see above).
- **No admin UI.** Admin review endpoints are implemented, tested, and
  authorization-enforced, but there is no admin front-end; a warrior report
  therefore stays "Under Review" in the demo.
- **Cyber Warrior report categories** use the seven backend enum values rather than
  the nine in the original design. Sensitive categories were deliberately not
  mapped onto unrelated enum values just to match a label.

---

## Documentation

| Document | Purpose |
|---|---|
| [`PROJECT.md`](PROJECT.md) | Product scope, principles, and constraints |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Environment variables, build/start commands, migrations, troubleshooting |
| [`docs/SUBMISSION.md`](docs/SUBMISSION.md) | Compliance checklist, demo script, submission notes |
| [`DEMO-CREDENTIALS.md`](DEMO-CREDENTIALS.md) | Synthetic demo identities |
| `01-TECH-STACK.md` … `08-SECURITY.md` | Stack, architecture, database, API, design, and security contracts |
| [`PROJECT-STRUCTURE.md`](PROJECT-STRUCTURE.md) | Repository layout |

---

## Safety

Use only synthetic data. Do not add real government credentials, real identity
details, payment data, or secrets to this repository.
