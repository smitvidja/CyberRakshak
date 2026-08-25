# Database Support Files

This directory holds database-specific support material only. PostgreSQL schema migrations belong in `backend/alembic/`, and SQLAlchemy models belong in `backend/app/models/` once those layers are introduced.

Place synthetic local seed fixtures in `database/seeds/`. Do not place production exports, real personal data, credentials, or uploaded evidence here.

## Synthetic Reference Data

After applying migrations, seed the local complaint-category and Cyber Warrior skill reference data:

```powershell
Push-Location backend
python ../database/seeds/seed_reference_data.py
Pop-Location
```

The command is idempotent. It adds only missing synthetic categories and skills; it does not use or import production data.
