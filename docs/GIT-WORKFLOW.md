# Git Workflow

This project uses GitHub for version control.

## Rule

After every completed and verified session or meaningful feature:

1. Review the changed files.
2. Run the relevant tests/checks - the same ones CI runs (`.github/workflows/ci.yml`):
   - backend, from `backend/`: `./.venv/Scripts/python.exe -m pytest -q` (needs a migrated and seeded Postgres: `alembic upgrade head`, then `../database/seeds/seed_reference_data.py`)
   - frontend, from `frontend/`: `npm run lint`, `npm run typecheck`, `npm test` (never `npm run build` on the dev machine - it corrupts the running dev server's `.next/`)
3. Make sure no unrelated changes are included.
4. Create a clear Git commit.
5. Push the commit to the configured GitHub remote.
6. Report the commit hash and push status, and confirm the CI run for that push is green.

Do not commit known broken code unless explicitly instructed.

Keep commits focused on the completed session or feature.

Before starting the next session, the previous work should be committed and pushed successfully.