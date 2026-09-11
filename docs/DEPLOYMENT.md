# Deployment Guide

Everything needed to deploy CyberRakshak's frontend and backend independently.
Prepared in Session 8.1; every command and behaviour below was executed and
verified locally, and anything that is *not* verified is called out as such.

The frontend (Next.js) and backend (FastAPI) deploy separately and only need to
know each other's public URL.

> **Deploying with Docker on Render?** Both services are containerised and there is a
> `render.yaml` Blueprint at the repository root. Jump to **§11** — it replaces the
> manual steps in §4 and §7, while §§1-3, 5, 6 and 9 still apply as written.

---

## 1. Environment variable checklist

### Backend — required

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | **Yes** | PostgreSQL only. Must use the `postgresql+psycopg://` scheme (see §4). No default — the app refuses to start without it. |
| `SECRET_KEY` | **Yes** | Minimum 32 characters, enforced at startup. Generate a fresh one per environment (see §2). |
| `CORS_ORIGINS` | **Yes in production** | The deployed frontend origin(s). Defaults to localhost only, which will block a deployed frontend. |
| `TRUSTED_PROXY_HOPS` | **Yes behind a proxy** | Number of reverse proxies in front of the API. Defaults to `0`, which is safe but wrong behind a proxy - the public rate limiter then treats every visitor as one client. `1` on Render. See §12. |

### Backend — optional (safe defaults)

| Variable | Default | Notes |
|---|---|---|
| `APP_ENVIRONMENT` | `development` | Set to `production` when deployed. Labelling only; does not change behaviour. |
| `APP_NAME` / `APP_VERSION` / `LOG_LEVEL` | see `.env.example` | Cosmetic/logging. |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Accepted range 5–1440. |
| `LOCAL_STORAGE_PATH` | `storage` | Uploaded-file directory. **Read §5 before deploying.** |
| `EVIDENCE_MAX_FILE_SIZE` | `10485760` (10 MiB) | Per-file upload cap. |
| `RESUME_LLM_ENABLED` | `false` | Model-assisted resume structuring. **Off by default on purpose**: turning it on sends resume text to the configured provider, which needs operator configuration and citizen-facing disclosure. The deterministic parser runs either way. See §13. |
| `RESUME_LLM_TIMEOUT_SECONDS` | `15` | Accepted range 1-60. Per provider attempt. |
| `RAG_SEMANTIC_EMBEDDINGS_ENABLED` | `true` | Cyber Saathi retrieval uses hosted multilingual embeddings. With no Gemini key, or set to `false`, retrieval falls back to word and character matching - it still works, but paraphrases and romanised Hindi retrieve less well. See §14. |
| `RAG_SEMANTIC_EMBEDDING_TIMEOUT_SECONDS` | `1.5` | Per query embedding. On timeout the search silently uses the sparse path. |

### Frontend

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Yes** | Backend base URL, no trailing slash, no `/api/v1` suffix. **Baked in at build time — see §3.** |

### Backend — optional Cyber Saathi LLM gateway

Session 9.4 supports server-side Gemini, Grok, and NVIDIA/Nemotron providers. The application remains functional through deterministic and grounded fallbacks when every key is absent. Configure only keys for providers you intend to use:

| Variable | Purpose |
|---|---|
| `GEMINI_API_KEY` | Gemini Developer API authentication. |
| `GROK_API_KEY` | xAI/Grok API authentication. |
| `NVIDIA_API_KEY` | NVIDIA hosted NIM authentication; optional tertiary provider. |

Provider order, current model defaults, endpoints, timeouts, retries, context/output budgets, temperature profiles, and top-p are documented in `backend/.env.example`. Keep API keys in the hosting platform's secret manager, never as Docker build arguments or frontend variables.

---

## 2. Generating a real `SECRET_KEY`

Never deploy with the placeholder from `.env.example`. It is long enough to pass
validation, which means a weak secret will *not* be caught for you.

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Set it as a secret/environment variable in your host's dashboard — never commit it.
Changing it invalidates all existing sessions, which is expected.

---

## 3. `NEXT_PUBLIC_API_URL` is a build-time value

Next.js inlines `NEXT_PUBLIC_*` variables into the browser bundle when you run
`npm run build` — it is not read at runtime. Verified: after a local build,
`localhost:8000` is present as a literal string inside `.next/static/chunks/*.js`.

Consequences:

- Set it **before** building, not after.
- Changing it requires a **rebuild/redeploy**, not just a restart.
- Never put a secret in a `NEXT_PUBLIC_` variable — it ships to every browser.

---

## 4. Database and migrations

The schema uses PostgreSQL-specific types; SQLite will not work.

**Driver scheme:** managed providers hand you a URL starting `postgresql://`.
This app uses the `psycopg` driver and needs `postgresql+psycopg://`. Rewrite the
scheme, keeping everything else identical:

```
postgresql://user:pass@host:5432/db      ->  won't load the right driver
postgresql+psycopg://user:pass@host:5432/db   <- use this
```

> **In Docker this is automatic.** The backend container's entrypoint rewrites the URL
> scheme and runs both the migration and the seed on every start (both are idempotent),
> so the two manual steps below are only needed for a non-container deploy. See §11.

**Run migrations** against the deployed database before first use, from `backend/`:

```bash
python -m alembic upgrade head
```

Verified: applies cleanly from a completely empty database through all four
migrations.

**Seed reference data** (complaint categories and the skill catalogue) — required,
or category dropdowns will be empty. From `backend/`:

```bash
python ../database/seeds/seed_reference_data.py
```

Idempotent — safe to run on every deploy; a second run inserts nothing.

---

## 5. File storage limitation — read before deploying

Uploaded evidence and résumés are written to the **local filesystem**
(`LOCAL_STORAGE_PATH`). There is no S3/object-storage adapter; `LocalStorageAdapter`
is the only implementation.

On hosts with ephemeral filesystems (Render/Railway/Fly/Heroku default, and any
container that restarts), **uploaded files are lost on restart or redeploy** while
their database metadata rows remain — so a report will still list its evidence, but
opening the file will fail.

Options:

1. **Accept it for a short demo.** Upload during the demo, show it immediately — fine
   for a live walkthrough, and the failure only appears after a restart.
2. **Attach a persistent volume** mounted at `LOCAL_STORAGE_PATH`. Simplest real fix.
3. **Implement an object-storage adapter.** `StorageAdapter` is a Protocol with three
   methods (`store` / `delete` / `read`), so a swap is contained — but this is new
   work, not configuration.

This is a genuine limitation, not a misconfiguration. Do not let it surprise you
mid-demo.

---

## 6. CORS

The API sends credentials, so a wildcard `*` origin is not usable and is never the
default.

`CORS_ORIGINS` accepts either format — use whichever your host's dashboard allows:

```
CORS_ORIGINS=["https://your-app.example.com","https://www.your-app.example.com"]
CORS_ORIGINS=https://your-app.example.com,https://www.your-app.example.com
```

Use the exact scheme and host of the deployed frontend, **no trailing slash**.

> Session 8.1 found and fixed a real bug here: the comma-separated form (the one
> most hosting dashboards push you toward) previously crashed the backend at
> startup with a `SettingsError`, because pydantic-settings JSON-decoded the value
> before the parsing validator ran. Even a single bare URL failed — only JSON array
> syntax worked. Both forms are now covered by regression tests.

Verified end-to-end with production-style settings: a request from an allowed
origin receives `access-control-allow-origin`; an unknown origin is rejected.

---

## 7. Build and start commands

These are the commands for a **non-container** deploy. For Docker, the images already
encode all of this — see §11.

### Backend

```bash
# install
pip install -r requirements.txt

# migrate + seed (once per environment, and after schema changes)
python -m alembic upgrade head
python ../database/seeds/seed_reference_data.py

# start (bind the port your host provides)
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Do **not** use `--reload` in production. Health check endpoint: `GET /health`.

### Frontend

```bash
npm ci
npm run build      # NEXT_PUBLIC_API_URL must already be set here
npm run start      # or the host's own Next.js runtime
```

---

## 8. Deployment order

CORS and the API URL each depend on the other side's final URL, so deploy in this
order to avoid a chicken-and-egg problem:

1. **Provision the database**, get its connection URL.
2. **Deploy the backend** with `DATABASE_URL` + `SECRET_KEY`. Set `CORS_ORIGINS` to a
   placeholder for now. Note its public URL.
3. **Run migrations and the seed script** against the deployed database.
   *(Skip this on a Docker deploy — the container entrypoint does it. See §11.)*
4. **Deploy the frontend** with `NEXT_PUBLIC_API_URL` = the backend URL from step 2.
   Note its public URL.
5. **Update `CORS_ORIGINS`** on the backend to the frontend URL from step 4 and
   restart the backend.
6. Smoke test (Session 8.3).

---

## 9. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Backend exits at startup, `SettingsError` / validation error | `DATABASE_URL` or `SECRET_KEY` missing, or `SECRET_KEY` under 32 chars. |
| Backend starts, all DB calls fail | Wrong driver scheme — use `postgresql+psycopg://` (§4). |
| Browser console: CORS policy errors | `CORS_ORIGINS` missing the frontend origin, or has a trailing slash / wrong scheme. |
| Frontend loads but every API call fails | `NEXT_PUBLIC_API_URL` wrong, or changed without rebuilding (§3). |
| Category dropdowns empty | Seed script never run (§4). |
| Complaint submit fails with a DB error | Migrations never run (§4). |
| Evidence uploads fine, later 404s | Ephemeral filesystem (§5). |

---

## 10. Secret hygiene

- `.env` and `.env.local` are gitignored; only `.env.example` files are tracked.
- Verified: no `.env` file has ever been committed in this repository's history.
- The example files contain placeholders only — no real credentials.
- Set real secrets through your host's environment/secret manager, never in source.

---

## 11. Deploy with Docker on Render

Both services ship as Docker images. `render.yaml` at the repository root is a
Blueprint that provisions the database and both web services in one apply.

Everything in this section was executed and verified locally with
`docker compose up --build` before being written down; the Render-side steps are
marked where they have not been.

### What is in the repository

| File | Purpose |
|---|---|
| `backend/Dockerfile` | FastAPI image. **Build context is the repository root**, not `backend/` — `database/seeds/seed_reference_data.py` locates the backend through `parents[2]`, so the image must keep the `<root>/backend` + `<root>/database` layout. |
| `backend/docker-entrypoint.sh` | Normalises the `DATABASE_URL` scheme, runs `alembic upgrade head` (retrying while the database wakes up), runs the seed, then `exec`s uvicorn on `$PORT`. |
| `frontend/Dockerfile` | Multi-stage Next.js build. Context is `frontend/`. Requires the `NEXT_PUBLIC_API_URL` build arg. |
| `.dockerignore`, `frontend/.dockerignore` | Keep tests, docs, design sources, demo assets, and `.env` files out of the images. `frontend/public` is deliberately kept — every asset in it is referenced at runtime. |
| `render.yaml` | Blueprint: one Postgres, two Docker web services, env wiring. |
| `docker-compose.yml` | The same two images plus Postgres, for local parity. |

### Two things the containers do for you

- **Driver scheme.** Render's `fromDatabase` wiring injects a `postgresql://` (or
  `postgres://`) URL, which will not load the psycopg driver. The entrypoint rewrites
  it. Verified: a container started with a bare `postgres://` URL boots cleanly.
- **Migrations and seeding.** Both run on every container start and are idempotent.
  Verified: a cold database applies all four migrations and seeds 6 categories +
  8 skills; the next start reports `0 categories, 0 skills added` and runs no
  migrations. Step 3 of §8 therefore no longer applies.

### Deploy steps

1. Push the repository to GitHub, then in Render choose **New → Blueprint** and point
   it at the repo. It reads `render.yaml` and creates `cyberrakshak-db`,
   `cyberrakshak-api`, and `cyberrakshak-web`.
2. Check the generated `SECRET_KEY` on `cyberrakshak-api` is **at least 32 characters**
   — the app refuses to start otherwise. If it is shorter, replace it with the output of
   the command in §2.
3. Set `NEXT_PUBLIC_API_URL` on `cyberrakshak-web` to the API's public URL (no trailing
   slash, no `/api/v1`) and deploy it. This is consumed as a **build arg**, so it must
   be set before the build runs, and changing it later needs a rebuild, not a restart.
   The frontend build fails loudly with a clear message if the value is missing, rather
   than producing a bundle that breaks in the browser.
4. Set `CORS_ORIGINS` on `cyberrakshak-api` to the web service's origin and redeploy it.

Health checks are already wired: `/health` for the API, and `/en` for the frontend
(there is no `/health` route on the frontend, and `/` only 307s to `/en`).

> Not yet verified on Render: whether Render forwards a service's environment variables
> into the Docker build as build arguments. If the frontend build stops at the
> `NEXT_PUBLIC_API_URL` guard, set the value in the dashboard before triggering the
> build, or pass it explicitly as a build argument.

### Running the whole stack locally

```bash
docker compose up --build
# frontend  http://localhost:3000/en
# backend   http://localhost:8000/health
```

If a native PostgreSQL already owns port 5432, publish the container's on another
port instead — the app containers talk to it over the compose network either way:

```bash
POSTGRES_PORT=5433 docker compose up --build
```

Uploads survive local restarts via the `backend_storage` volume. Render has no
equivalent by default — §5 still applies there.

## 12. Reverse proxies and the public rate limiter

The suspect-search and correction endpoints are unauthenticated, so they are rate
limited per client. Working out *which* client a request came from is the whole
problem, and it has two failure modes that are easy to ship and hard to notice.

**Trusting the connection.** Behind a proxy the address the app sees is the
proxy's, and it is the same for everybody. The limit then applies to all visitors
at once: 30 searches a minute for the entire audience, after which a citizen who
has searched once is told to wait a minute. Nothing errors, no log says why, and
it only appears under real traffic.

**Trusting `X-Forwarded-For`.** Anyone can send that header, so if the app reads
it without a proxy actually being there, every caller picks its own bucket and
the limit stops existing.

So the header is read only as far as `TRUSTED_PROXY_HOPS` says there are proxies,
counting in from the right - the end each proxy appends to. Entries further left
came from the caller and are ignored. Set it to the number of proxies that will
actually handle the request:

| Topology | Value |
|---|---|
| Container exposed directly (local, `docker compose`) | `0` (default) |
| Render, Railway, Fly | `1` |
| Your own nginx in front of one of those | `2` |
| A CDN (Cloudflare) in front of the platform router | `2`, or `3` with your own nginx too |

**Verify rather than assume.** The count is a property of the deployment, not of
the platform's name, and setting it too high is what lets a caller forge the
value. From a machine outside the deployment, request the API and compare what
the platform reports as the client address with what you actually connected from.
If they match, one hop is being added; if you need to look further left to find
your own address, there are more. `render.yaml` ships `1`, which is what a
standalone Render web service does today.

**Uvicorn does this too, and it has to be turned off.** Uvicorn ships
`--proxy-headers` **on by default**: for any peer in `--forwarded-allow-ips`
(`127.0.0.1` unless set) it rewrites `request.client` from `X-Forwarded-For`
before the application sees it. Two layers interpreting the same caller-supplied
header under different rules means the app cannot tell a real peer from a
supplied one, and the `TRUSTED_PROXY_HOPS=0` guarantee quietly stops holding. The
container entrypoint therefore runs uvicorn with `--no-proxy-headers`, leaving
`request.client` as the true peer and `app/core/client_identity.py` as the only
thing that reads the header. If you start uvicorn yourself, pass it too.

This is not visible from the application code or from any test that uses
`TestClient`, because neither runs the uvicorn middleware. It shows up only
against a running server.

Two consequences worth knowing:

- The limiter is **per process**. One Render instance running one uvicorn worker
  is what this project deploys, so the counter is exact. Add workers or instances
  and the effective limit multiplies by that number. A shared counter would mean
  a database write on a public endpoint for every request, which is not worth it
  until there is more than one instance.
- IPv6 is limited per `/64`, not per address, because a single subscriber is
  routinely given a whole `/64` and can move around inside it freely.

## 13. Model-assisted resume structuring

Off unless `RESUME_LLM_ENABLED=true`. When off, nothing about resume handling
changes and no resume text leaves the server.

When on, the extracted text of an uploaded resume is sent to the same providers
the rest of the app uses, in the configured order, to map it onto the Cyber
Warrior schema. It runs **after** the deterministic parser and merges section by
section: where the model found nothing, the deterministic value stands, so
enabling it can add fields but cannot remove ones that were already offered.
Anything the model returns that is not supported by the document is discarded.

**Before turning it on**, note what it means: a citizen's resume is sent to a
third party. Section 6.4 of the phase prompt requires explicit configuration,
privacy documentation, and citizen-facing disclosure where required. The flag
covers the first; the other two are a product decision, not a config change.

What it does not do: no local model, no new parsing service, no raw resume text
in logs or metrics, and no change to identity fields. Name, mobile and email are
verified elsewhere in the journey and cannot be written from a resume - values
that look like contact details are stripped even when the document contains them.

### What actually holds the line

Three things, in order, and it is worth being precise about which covers what:

1. **The schema.** Output is a strict, resume-specific shape: named string
   fields only, no free-form key, nothing for a contact detail to live in.
2. **Grounding.** Every returned value must appear in the uploaded document,
   compared with punctuation and spacing normalised. This catches an invented
   employer and an instruction the model followed, because both produce text the
   document does not contain.
3. **The review screen.** Nothing is written to a profile until the citizen
   confirms it.

The honest boundary: grounding compares against *that citizen's own document*.
Someone who writes a grand claim into their own resume will see it offered back
as a suggestion for their own profile, which is no more than they could achieve
by typing it into the form. What the guards prevent is text the document never
contained, and output in any shape other than the schema.

Verified against the live provider with a resume carrying an injected block
instructing the parser to reveal its system prompt and add a government job
title: the returned suggestions were byte-identical to the same resume without
the block.

## 14. Cyber Saathi retrieval: the knowledge index

The index at `backend/app/data/cyber_saathi/authoritative_knowledge/knowledge_index.json`
is **committed**, not built at deploy time. It carries two vectors per chunk: a
hashed character n-gram vector computed offline, and a 768-dimension Gemini
embedding. Nothing regenerates it on start, so a deploy ships exactly what is in
the repository.

**Rebuild it only when `sources.json` changes**, and rebuild it *with* embeddings:

```bash
cd backend
./.venv/Scripts/python.exe -m app.services.cyber_saathi_knowledge --semantic
```

Rebuilding without `--semantic` produces a valid index with the dense vectors
**missing**. Retrieval still works and nothing errors; it just gets noticeably
worse at paraphrases and at romanised Hindi, which is most of what citizens type.
The index records the provider and model it was built with, and retrieval only
uses the dense path when the running configuration matches, so a mismatch
degrades rather than breaks.

At query time one embedding call is made per distinct question, cached in
process. If the key is missing, the provider is disabled, or the call times out,
retrieval falls back to the sparse path for that query.

**The test suite must not be able to rewrite this file.** It used to: a module
setup hook called the rebuild with no arguments, so running `pytest` quietly
replaced the committed index with an embedding-free one. Anyone who ran the tests
before deploying shipped the degraded index without knowing. Ingestion is now
exercised against a temporary path.

## Runtime additions from Phase 10

Three dependencies were added for resume parsing and complaint-copy PDFs. All three ship
manylinux wheels and install cleanly on `python:3.12-slim` with no compiler, verified by
building the image and importing them inside it:

- `python-docx` - DOCX resume text extraction.
- `fpdf2` - complaint-copy PDF rendering.
- `uharfbuzz` - text shaping. **Not optional.** Without it fpdf2 silently degrades and
  Devanagari renders with broken conjuncts and misplaced matras, so Hindi PDFs would look
  wrong rather than fail loudly.

Fonts live in `backend/app/assets/fonts/` (Noto Sans + Noto Sans Devanagari, SIL OFL, licence
shipped alongside). They are inside `backend/`, so the existing `COPY backend/ backend/` layer
includes them and no `.dockerignore` rule excludes them.

The frontend ships `public/data/india-states-v1.json` (Secure India state boundaries). The
frontend Dockerfile already copies `public/` explicitly.

No new environment variables are required. `RESUME_PARSER` defaults to `document`; setting it
to `mock` forces the static demo parser and must not be used in a real deployment.

Both new tables arrive through Alembic, and the container entrypoint already runs
`alembic upgrade head` on every start, so no manual migration step is needed.
