---
type: Module
title: app-core
description: Cross-cutting FastAPI app wiring shared by every resource module — entry point, bearer auth, settings, DB session, shared error types and model mixins.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app
tags: [backend, core, auth, errors, config]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T06:30:03Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 086ad0dd7cfe1a9581dd2f87de143759ef781634
    title: Codebase knowledge graph
status: stable
---

# Files

| File | Role |
|---|---|
| `app/main.py` | FastAPI app, CORS middleware, 3 exception handlers, `/health`, all `app.include_router(...)` calls, startup migrations, the background notification sweep |
| `app/auth.py` | `bearer_scheme`, `CurrentUser`, `current_user`, `require_roles`, `current_tenant_id` |
| `app/security.py` | password rules/hashing and JWT + refresh-token primitives — see [Auth](/modules/auth.md) |
| `app/config.py` | `Settings` (PORT, DATABASE_URL, CORS_ORIGINS, JWT_SECRET, access/refresh TTLs, refresh-cookie name/secure flag, the `SMTP_*` block read by [Notifications](/modules/notifications.md), and `EXPORT_STORAGE_DIR`), `settings` singleton |
| `app/db.py` | `Base`, `engine`, `SessionLocal`, `get_db` dependency |
| `app/errors.py` | `NotFoundError` (404), `ForbiddenError` (403), `ConflictError` (409), `ValidationFailedError` (400) |
| `app/models/mixins.py` | `TimestampMixin`, `SoftDeleteMixin` used by (almost) every model |

`Settings.smtp_host` defaults to empty, and the notification service treats that as
"log the message, do not send" — so the app and the test suite run with no mail relay
configured. `smtp_username`/`smtp_password`/`smtp_from`/`smtp_use_tls`/`smtp_timeout_seconds`
are read from the environment alongside it; none are hard-coded.

`Settings.export_storage_dir` (`EXPORT_STORAGE_DIR`, default `var/exports`) is the directory
[Tracker](/modules/tracker.md)'s `_persist_export` writes generated export files into; the
`uploaded_files` row records the resulting path in `storage_url`.

`Settings.notification_sweep_interval_seconds` (`NOTIFICATION_SWEEP_INTERVAL_SECONDS`, default
3600) controls the in-process sweep that `lifespan` starts as an `asyncio` task after
`_run_migrations` and cancels on shutdown. It starts only when `DATABASE_URL` is set and the
interval is above zero — set it to `0` to drive
[Scheduled Notifications](/modules/scheduled-notifications.md)'s `run_all` from outside instead.

# Key symbols

* `app.main._run_migrations` — runs `alembic upgrade head` against `settings.database_url` in
  the `lifespan` startup hook; no-op if `DATABASE_URL` unset.
* `app.main.http_exception_handler` / `validation_handler` / `unhandled_exception_handler` — the
  single error-handling layer producing `{"error", "details"}` for every non-2xx response. See
  [Conventions](/conventions.md#error-shape-verified-in-apperrorspy-and-appmainpy).
* `app.auth.require_roles` — the authorization chokepoint for every router in the
  repo. See [Architecture](/architecture.md#authorization-chokepoint).
* `app.auth.current_user` — resolves `Authorization: Bearer <JWT>` (declared to OpenAPI via
  `bearer_scheme`, an `HTTPBearer` named `BearerAuth`) by decoding the token with
  `app.security.decode_access_token` and loading the `users` row; 401 on a missing/invalid token
  or unknown user, 403 when `is_active` is false. This replaced the former
  `X-User-Role`/`X-User-Id` header stub — `require_roles` and `current_tenant_id` kept their
  signatures, so no router changed. See [Auth](/modules/auth.md).
* `app.auth.current_tenant_id` — the one place the authenticated user id is joined against
  `users` to resolve a tenant scope; every tenant-scoped resource depends on this rather than
  re-querying `users`.

# Depended on by

Every module file in [modules/index.md](/modules/index.md) — all routers import
`require_roles`/`current_user`/`current_tenant_id` from here, all services raise the error types
from `app/errors.py`, and all models mix in `TimestampMixin`/`SoftDeleteMixin`.
