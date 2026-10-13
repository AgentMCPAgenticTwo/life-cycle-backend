---
type: Module
title: app-core
description: Cross-cutting FastAPI app wiring shared by every resource module — entry point, header auth, settings, DB session, shared error types and model mixins.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app
tags: [backend, core, auth, errors, config]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

| File | Role |
|---|---|
| `app/main.py` | FastAPI app, CORS middleware, 3 exception handlers, `/health`, all `app.include_router(...)` calls, startup migrations |
| `app/auth.py` | `CurrentUser`, `current_user`, `require_roles`, `current_tenant_id` |
| `app/config.py` | `Settings` (PORT, DATABASE_URL, CORS_ORIGINS from env), `settings` singleton |
| `app/db.py` | `Base`, `engine`, `SessionLocal`, `get_db` dependency |
| `app/errors.py` | `NotFoundError` (404), `ForbiddenError` (403), `ConflictError` (409), `ValidationFailedError` (400) |
| `app/models/mixins.py` | `TimestampMixin`, `SoftDeleteMixin` used by (almost) every model |

# Key symbols

* `app.main._run_migrations` — runs `alembic upgrade head` against `settings.database_url` in
  the `lifespan` startup hook; no-op if `DATABASE_URL` unset.
* `app.main.http_exception_handler` / `validation_handler` / `unhandled_exception_handler` — the
  single error-handling layer producing `{"error", "details"}` for every non-2xx response. See
  [Conventions](/conventions.md#error-shape-verified-in-apperrorspy-and-appmainpy).
* `app.auth.require_roles` — fan-in 93, the authorization chokepoint for every router in the
  repo. See [Architecture](/architecture.md#authorization-chokepoint).
* `app.auth.current_tenant_id` — the one place `X-User-Id` is joined against `users` to resolve
  a tenant scope; every tenant-scoped resource depends on this rather than re-querying `users`.

# Depended on by

Every module file in [modules/index.md](/modules/index.md) — all routers import
`require_roles`/`current_user`/`current_tenant_id` from here, all services raise the error types
from `app/errors.py`, and all models mix in `TimestampMixin`/`SoftDeleteMixin`.
