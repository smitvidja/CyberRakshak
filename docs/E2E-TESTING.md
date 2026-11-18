# Browser end-to-end tests

`frontend/tests/e2e/` drives a real, headless Chrome through the journeys a person
actually takes, against the real API and database. They catch what unit and API tests
cannot: a redirect that goes nowhere, a button that never hydrates, a draft lost between
steps.

| File | Journeys |
|---|---|
| `citizen.e2e.ts` | Hindi/English switching; anonymous complaint → reference number → tracking; verified citizen complaint with PDF evidence → My Reports |
| `cyber-warrior.e2e.ts` | Wrong OTP refused; identity → profile → resume upload + review → application → first report |
| `admin.e2e.ts` | Wrong admin password refused; admin sign-in to the knowledge-gaps console and sign-out |

They use `playwright-core` with the Chrome already installed (no browser download), and
`node:test`, like the unit tests. They are **not** part of CI yet.

## Run them

They create complaints and register demo identities, so always point them at a
**throwaway database**, never your dev database.

```bash
# 1. Throwaway Postgres (5440 avoids other projects' databases on 5432/5433)
MSYS_NO_PATHCONV=1 docker run -d --rm --name cr-e2e-pg -p 127.0.0.1:5440:5432 \
  -e POSTGRES_USER=cyberrakshak -e POSTGRES_PASSWORD=cyberrakshak_local_only -e POSTGRES_DB=cyberrakshak \
  --tmpfs /var/lib/postgresql/data postgres:16-alpine

# 2. Schema, reference data, and an administrator (from backend/)
export DATABASE_URL=postgresql+psycopg://cyberrakshak:cyberrakshak_local_only@127.0.0.1:5440/cyberrakshak
./.venv/Scripts/python.exe -m alembic upgrade head
./.venv/Scripts/python.exe ../database/seeds/seed_reference_data.py
ADMIN_PASSWORD=e2e-admin-password-123 ./.venv/Scripts/python.exe -m scripts.create_admin e2e-admin@example.com

# 3. Backend on 8010 - paid AI features off, uploads to a scratch folder
LLM_ENABLED=false RESUME_LLM_ENABLED=false VOICE_ENABLED=false RAG_SEMANTIC_EMBEDDINGS_ENABLED=false \
LOCAL_STORAGE_PATH=/tmp/cr-e2e-storage CORS_ORIGINS=http://localhost:3010 \
./.venv/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8010

# 4. Frontend dev server on 3010, pointed at that backend (from frontend/)
NEXT_PUBLIC_API_URL=http://localhost:8010 npx next dev -p 3010

# 5. The journeys (from frontend/)
E2E_ADMIN_EMAIL=e2e-admin@example.com E2E_ADMIN_PASSWORD=e2e-admin-password-123 npm run test:e2e
```

Without `E2E_ADMIN_EMAIL`/`E2E_ADMIN_PASSWORD` the admin journeys are reported as
**skipped**. `E2E_BASE_URL` and `E2E_CHROME` override the frontend URL and the Chrome path.

To run again, recreate the database (step 1-2). The journeys use fixed demo identities, and
a second run on the same database finds them already registered.

## Notes

- **Memory:** a dev server, the backend and Chrome together need about 1 GB free. Stop other
  projects' dev servers first on an 8 GB machine.
- **First visits are slow.** The dev server compiles each route the first time it is opened,
  so every wait is "until it appears" (up to 90 s), never a fixed sleep.
- **Never run `npm run build`** to speed this up. It corrupts the dev server's `.next/`.
- Buttons and fields are found by their visible labels, read from `messages/en.json`, so
  a copy change does not break the journeys.
- Each journey also fails on any browser console error.
