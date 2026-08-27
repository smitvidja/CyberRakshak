#!/bin/sh
# Container entrypoint: normalise the database URL, bring the schema and reference
# data up to date, then hand PID 1 to uvicorn.
set -eu

# Managed Postgres providers (Render included) hand out postgres:// or postgresql://
# URLs, but SQLAlchemy needs the psycopg v3 driver named explicitly - see
# docs/DEPLOYMENT.md section 4. Rewriting the scheme here means render.yaml's
# fromDatabase wiring and a URL pasted straight from a dashboard both work with no
# application code involved.
case "${DATABASE_URL:-}" in
  postgresql+*)   ;;
  postgresql://*) DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgresql://}" ;;
  postgres://*)   DATABASE_URL="postgresql+psycopg://${DATABASE_URL#postgres://}" ;;
esac
export DATABASE_URL

# Both steps are idempotent, so running them on every start is safe. The retry loop
# covers a database that is still accepting connections slowly (compose start-up
# ordering, or a Render instance waking cold).
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  attempt=1
  until python -m alembic upgrade head; do
    if [ "$attempt" -ge 10 ]; then
      echo "alembic upgrade head failed after $attempt attempts" >&2
      exit 1
    fi
    echo "database not ready yet, retrying migrations (attempt $attempt)..." >&2
    attempt=$((attempt + 1))
    sleep 3
  done

  # Required, not optional: without it complaint-category dropdowns are empty.
  python ../database/seeds/seed_reference_data.py
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
