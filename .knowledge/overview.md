---
type: Codebase Overview
title: life-cycle-backend
description: Python/FastAPI backend for contract-lifecycle management, serving a camelCase JSON API over PostgreSQL to a separate React frontend.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/
tags: [backend, fastapi, python, postgresql]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Purpose

A contract lifecycle management API: dashboards, contract CRUD and third-party-paper intake,
templates/clauses, lifecycle negotiation (clause analysis, ask-AI, routing, external-party
negotiation), approvals and e-signature, contract detail/obligations/renewal/termination, and
a management tracker + tenant settings surface. One FastAPI app serves all of it under
`/api/v1`, consumed by a separate React frontend over header-stub auth (no login/tokens).

# Stack

| Layer | Technology |
|---|---|
| Frontend (separate repo) | React (JavaScript) |
| Backend | Python, FastAPI, Pydantic schemas |
| Database | PostgreSQL, SQLAlchemy ORM, Alembic migrations |
| Server | uvicorn |
| Tests | pytest |

# Scale

282 files total, 207 Python files, 4893 graph nodes / 14460 edges (per
`get_architecture(aspects=["all"])`).

# Layout

```
app/main.py                   FastAPI app wiring: CORS, exception handlers, router includes, migrations-at-startup
app/auth.py                   header-auth dependency (current_user, require_roles, current_tenant_id)
app/config.py                 Settings read from the environment (PORT, DATABASE_URL, CORS_ORIGINS)
app/db.py                     SQLAlchemy Base/engine/SessionLocal/get_db
app/errors.py                 NotFoundError/ForbiddenError/ConflictError/ValidationFailedError -> shared error body
app/models/<area>.py          15 files: ORM models, grouped by feature area, not 1:1 with resources
app/routers/<resource>.py     ~25 files, one APIRouter per resource; thin HTTP binding
app/services/<resource>.py    ~25 files; business rules
app/repositories/<resource>.py ~23 files; data access only
app/schemas/<resource>.py     ~26 files; Pydantic request/response DTOs
alembic/versions/             51 migrations, 0001-0051, one table per migration, applied at startup
tests/                        32 files, one per resource/concern, pytest
```

# Entry points

* `app/main.py` — ASGI app (`app = FastAPI(...)`), started via `uvicorn app.main:app --port 5199`.
* `GET /health` — unauthenticated liveness check, defined directly in `app/main.py`.
* Migrations run automatically in the `lifespan` startup hook (`_run_migrations`), calling
  `alembic upgrade head` against `DATABASE_URL` — a no-op if `DATABASE_URL` is unset, so the app
  still boots for the health check without a database.

# Scripts / checks

```bash
python -m compileall app      # syntax check
pytest -q                     # test suite (32 files under tests/)
uvicorn app.main:app --port 5199 &   # run for manual verification
```

# Where to go next

* [Architecture](/architecture.md) for layering, clusters and hotspots.
* [Conventions](/conventions.md) for the rules every module in this repo follows (and the one
  gap found against CLAUDE.md).
* [modules/index.md](/modules/index.md) for a concept file per resource area.
