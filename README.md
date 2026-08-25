# CyberRakshak

CyberRakshak is a bilingual cybercrime reporting and Cyber Warrior prototype. This repository is being built in phased sessions; the initial workspace foundation contains no product implementation yet.

## Project Documentation

The root Markdown files are the permanent engineering source of truth:

- `PROJECT.md` describes the product scope and constraints.
- `AGENTS.md` is the operating manual for coding agents.
- `PROJECT-STRUCTURE.md` is the required repository layout.
- `SKILLS.md` routes work to the minimum necessary technical context.
- `01-TECH-STACK.md` through `08-SECURITY.md` define the stack, architecture, data, API, design, and security contracts.

Phase execution playbooks are in `prompts/`. Follow `GIT-WORKFLOW.md` after every completed and verified session.

## Local Development

Frontend, backend, and database setup will be introduced in the Foundation phase. `docker-compose.yml` provides an optional local PostgreSQL service for later database work.

Use only synthetic development data. Do not add real government credentials, identity details, payment data, or secrets to this repository.
