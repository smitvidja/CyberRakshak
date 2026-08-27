# Deployment Guide

Everything needed to deploy CyberRakshak's frontend and backend independently.
Prepared in Session 8.1; every command and behaviour below was executed and
verified locally, and anything that is *not* verified is called out as such.

The frontend (Next.js) and backend (FastAPI) deploy separately and only need to
know each other's public URL.

---

## 1. Environment variable checklist

### Backend — required

| Variable | Required | Notes |
|---|---|---|
| `DATABASE_URL` | **Yes** | PostgreSQL only. Must use the `postgresql+psycopg://` scheme (see §4). No default — the app refuses to start without it. |
| `SECRET_KEY` | **Yes** | Minimum 32 characters, enforced at startup. Generate a fresh one per environment (see §2). |
| `CORS_ORIGINS` | **Yes in production** | The deployed frontend origin(s). Defaults to localhost only, which will block a deployed frontend. |

### Backend — optional (safe defaults)

| Variable | Default | Notes |
|---|---|---|
| `APP_ENVIRONMENT` | `development` | Set to `production` when deployed. Labelling only; does not change behaviour. |
| `APP_NAME` / `APP_VERSION` / `LOG_LEVEL` | see `.env.example` | Cosmetic/logging. |
| `JWT_ALGORITHM` | `HS256` | |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Accepted range 5–1440. |
| `LOCAL_STORAGE_PATH` | `storage` | Uploaded-file directory. **Read §5 before deploying.** |
| `EVIDENCE_MAX_FILE_SIZE` | `10485760` (10 MiB) | Per-file upload cap. |

### Frontend

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | **Yes** | Backend base URL, no trailing slash, no `/api/v1` suffix. **Baked in at build time — see §3.** |

There are no other variables. Earlier `.env.example` files listed
`OBJECT_STORAGE_*` and `AI_API_KEY`; those were never read by any code and have
been removed so nobody wastes time provisioning services the app does not use.

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
