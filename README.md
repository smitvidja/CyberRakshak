# CyberRakshak

CyberRakshak is a bilingual cybercrime reporting and Cyber Warrior prototype. This repository is being built in phased sessions; its foundation includes runnable frontend and backend scaffolds, but no product journeys yet.

## Project Documentation

The root Markdown files are the permanent engineering source of truth:

- `PROJECT.md` describes the product scope and constraints.
- `AGENTS.md` is the operating manual for coding agents.
- `PROJECT-STRUCTURE.md` is the required repository layout.
- `SKILLS.md` routes work to the minimum necessary technical context.
- `01-TECH-STACK.md` through `08-SECURITY.md` define the stack, architecture, data, API, design, and security contracts.

Phase execution playbooks are in `prompts/`. Follow `GIT-WORKFLOW.md` after every completed and verified session.

## Local Development

The frontend runs on http://localhost:3000; the backend runs on http://localhost:8000 and exposes GET /health plus FastAPI development docs at /docs.

### Environment Files

In PowerShell, create local environment files from the safe examples:

~~~powershell
Copy-Item frontend/.env.example frontend/.env.local
Copy-Item backend/.env.example backend/.env
~~~

Keep the example values synthetic. Replace them only in uncommitted local environment files.

### Frontend

~~~powershell
Set-Location frontend
npm install
npm run dev
~~~

Open http://localhost:3000/en for English or http://localhost:3000/hi for Hindi. Run the available checks with:

~~~powershell
npm run lint
npm run build
~~~

### Backend

From the repository root:

~~~powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
Set-Location backend
.venv/Scripts/python.exe -m pytest
.venv/Scripts/python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
~~~

### Local PostgreSQL

PostgreSQL is optional until the database phase. Start the local service when it is needed:

~~~powershell
docker compose up -d postgres
~~~

Use only synthetic development data. Do not add real government credentials, identity details, payment data, or secrets to this repository.
