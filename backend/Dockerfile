# CyberRakshak backend (FastAPI + SQLAlchemy + Alembic).
#
# IMPORTANT: build this from the REPOSITORY ROOT, not from backend/:
#   docker build -f backend/Dockerfile -t cyberrakshak-api .
# database/seeds/seed_reference_data.py locates the backend via parents[2], so the
# image has to preserve the <root>/backend + <root>/database layout.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Dependencies first so application edits do not invalidate the install layer.
# psycopg[binary] and pwdlib[argon2] ship manylinux wheels, so no compiler is needed.
COPY backend/requirements.txt backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt

COPY backend/ backend/
COPY database/ database/

RUN chmod +x backend/docker-entrypoint.sh \
 && useradd --create-home --uid 10001 appuser \
 && mkdir -p /app/backend/storage \
 && chown -R appuser:appuser /app

USER appuser
WORKDIR /app/backend

# LOCAL_STORAGE_PATH defaults to the CWD-relative "storage"; pin it to an absolute
# path because LocalStorageAdapter resolves it once at import time.
ENV LOCAL_STORAGE_PATH=/app/backend/storage \
    PORT=8000

EXPOSE 8000

ENTRYPOINT ["./docker-entrypoint.sh"]
