# CyberRakshak Context Routing

This file prevents unnecessary context loading. Do not read every project document for every task. Read the smallest set that is sufficient for a correct architectural decision.

## Mandatory Base Context

For every implementation task, read:

1. `AGENTS.md`
2. `PROJECT-STRUCTURE.md`
3. This `SKILLS.md`

## Product / Planning

Read:

- `PROJECT.md`
- `AGENTS.md`
- `PROJECT-STRUCTURE.md`

Add other documents only when the planning decision crosses technical contracts.

## Frontend / UI

Read:

- `AGENTS.md`
- `PROJECT-STRUCTURE.md`
- `05-FRONTEND.md`
- `07-DESIGN-SYSTEM.md`
- `design.md`
- Inspect `design/cyber_warrior/`, `design/home/`, and `design/victim_Report/`; use only the in-scope references to implement the requested screens

Also read `06-API.md` when API integration is involved. Read `03-ARCHITECTURE.md` when module boundaries or cross-layer behavior are affected.

## Backend

Read:

- `AGENTS.md`
- `PROJECT-STRUCTURE.md`
- `04-BACKEND.md`
- `06-API.md`
- `03-ARCHITECTURE.md`

Read `02-DATABASE.md` when persistence, models, migrations, ownership, or constraints are involved.

## Database

Read:

- `AGENTS.md`
- `PROJECT-STRUCTURE.md`
- `02-DATABASE.md`
- `03-ARCHITECTURE.md`

Read `06-API.md` only when database changes alter API behavior.

## Full-Stack Feature

Read:

- `AGENTS.md`
- `PROJECT-STRUCTURE.md`
- `03-ARCHITECTURE.md`
- `04-BACKEND.md`
- `05-FRONTEND.md`
- `06-API.md`

Add `02-DATABASE.md` for persistence changes, `07-DESIGN-SYSTEM.md` for UI changes, and relevant design references for screen work.

## Security

Read:

- `AGENTS.md`
- `PROJECT-STRUCTURE.md`
- `08-SECURITY.md`
- Relevant architecture/backend/frontend/API/database document based on the affected layer.

## Documentation

Read only the documents directly related to the requested documentation change. Read all core docs only for a consistency audit.

## Completion Check

Before declaring work complete:

- Confirm the task followed the selected context route.
- Confirm no unrelated docs or implementation areas were loaded without need.
- Confirm architecture and source-of-truth documents still agree.
