# Database Support Files

This directory holds database-specific support material only. PostgreSQL schema migrations belong in `backend/alembic/`, and SQLAlchemy models belong in `backend/app/models/` once those layers are introduced.

Place synthetic local seed fixtures in `database/seeds/`. Do not place production exports, real personal data, credentials, or uploaded evidence here.
