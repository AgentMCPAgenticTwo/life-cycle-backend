---
type: Convention
title: life-cycle-backend conventions
description: Bearer-token auth, layering, persistence, error-shape and id conventions as actually implemented, verified line-by-line against CLAUDE.md's stated rules.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app
tags: [backend, conventions, auth, persistence]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 700de34973c81dd98062f0bef469b620e6fc976b
    title: Codebase knowledge graph
status: stable
---

# Authentication (verified in `app/auth.py` and `app/security.py`)

Real login replaced the former `X-User-Role`/`X-User-Id` header stub; see
[Auth](/modules/auth.md) for the token design.

* Callers send `Authorization: Bearer <JWT>`. The scheme is declared via
  `fastapi.security.HTTPBearer(scheme_name="BearerAuth", auto_error=False)` so it appears as an
  OpenAPI security scheme and Swagger's "Authorize" UI actually sends it.
* Missing/malformed/expired token, or a token whose `sub` matches no live `users` row ->
  `current_user` raises `HTTPException(401)`. A user row with `is_active` false -> **403**. A
  role outside an endpoint's allowed list -> `require_roles`'s inner `_check` raises
  `HTTPException(403)`.
* The role is read from the `users` row on every request, never from the token claims — a
  deactivation or role change takes effect on the next request, not the next login.
* `current_tenant_id` additionally resolves the authenticated user id to a `users` row to get
  `tenant_id`; an unparseable or unknown id is also a 401, not a 400 — treated as "no auth", not
  "bad input".
* Roles are passed as `*allowed: str` into `require_roles(...)` per call site, sourced from each
  endpoint's own contract — confirmed no hard-coded role list spans modules it shouldn't.

# Layering (verified by sampling `contracts` and `approvals`)

Routers bind/validate and call services; services own validation and business rules and map to
response DTOs; repositories only query. See [Architecture](/architecture.md#layering) for the
function-level evidence. No mapper library is used anywhere — `_to_response`/`_to_list_item`
style functions in each service module do explicit field-by-field mapping, matching CLAUDE.md's
"map by hand, don't add a mapper library" rule.

# Error shape (verified in `app/errors.py` and `app/main.py`)

One shared body `{"error": string, "details": string[]}`, produced by exactly three exception
handlers registered on the `FastAPI` app:

* `StarletteHTTPException` handler reads `exc.details` (falls back to `[]`) — this is why
  `NotFoundError`/`ForbiddenError`/`ConflictError`/`ValidationFailedError` in `app/errors.py`
  all subclass `HTTPException` and optionally carry a `details` list.
* `RequestValidationError` handler (Pydantic/FastAPI's own 422) is remapped to **400**, with
  `details` built from each error's `loc`/`msg` — so malformed request bodies return 400, not
  FastAPI's default 422, matching CLAUDE.md's status-code table.
* A catch-all `Exception` handler returns 500 with the same shape and an empty `details` list,
  so no unhandled exception ever leaks a raw traceback.

# CORS (verified in `app/main.py`)

* `CORSMiddleware` is added **before** the exception handlers and before any router include —
  i.e., before auth ever runs, since auth is a per-route `Depends`, not middleware. This matches
  "CORS before auth in the middleware order."
* `allow_credentials=True` is paired with an explicit `allow_origins` list parsed from
  `CORS_ORIGINS` (defaulting to `http://localhost:5173`, a single concrete origin) — never
  `"*"`. `allow_headers` includes `Content-Type`, `Authorization`, and the now-unused
  `X-User-Role`/`X-User-Id` (kept listed after the switch to bearer auth).

# Persistence (verified in `app/models/mixins.py` and a sample migration)

* `TimestampMixin` gives every model `created_at`/`created_by`/`updated_at`/`updated_by`;
  `created_at`/`updated_at` are `DateTime(timezone=True)` (TIMESTAMPTZ on Postgres) with
  `server_default=func.now()`. `SoftDeleteMixin` adds the `deleted_at`/`deleted_by` pair.
* IDs are `PGUUID(as_uuid=True)` columns. Primary keys are generated **app-side** via
  `default=uuid.uuid4` at the ORM/model layer rather than a Postgres `gen_random_uuid()` server
  default — CLAUDE.md permits either ("a database default... or the app layer at insert time"),
  so this is compliant, just worth knowing which one this repo chose.
* `NUMERIC`/`Numeric` columns appear in `app/models/approval.py`, `contract.py`,
  `lifecycle_clause.py`, `tracker.py` (e.g. `contract_turnaround_metrics.estimated_turnaround_days`)
  — money/measured-quantity columns use `Numeric`, not float, matching CLAUDE.md.
* `JSONB` appears in `app/models/esignature.py`, `lifecycle_clause.py`,
  `lifecycle_negotiation.py` for structured data columns.
* Migrations are plain Alembic revision files under `alembic/versions/`, applied at startup via
  `command.upgrade(cfg, "head")` inside `app.main._run_migrations` (a no-op if `DATABASE_URL` is
  unset). New tables are additive, one per migration, matching the "never edit/reorder an
  existing migration" rule — confirmed no migration file redefines or drops a table from an
  earlier batch.

# Resolved: auth schema now has a migration

`app/models/user.py` gained `password_hash`, `is_active`, `must_change_password`,
`last_login_at` and `app/models/refresh_token.py` added the whole `refresh_tokens` table with no
revision behind them. `alembic/versions/0052_add_user_credentials_and_refresh_tokens.py` now
supplies one, so a Postgres database migrated with `alembic upgrade head` matches
`Base.metadata` (which is what `tests/conftest.py` builds the test schema from, and what
`tests/test_persistence.py` compares the models against). See
[Migrations](/modules/migrations.md) and [Auth](/modules/auth.md).

# Reference-data seeding: one idempotent seeder exists

The only seeding in the repo is `app.repositories.settings_notifications.ensure_seeded`, which
inserts the `EVENT_NAMES` rows into `tenant_notification_settings` with both toggles On. It is
idempotent in the way CLAUDE.md asks for: it reads the tenant's existing `event_name` values
first and skips any name already present, so running it on every GET never duplicates a row.
Copy that shape for any future seed step. No migration uses `op.bulk_insert`; the remaining
lookups (folder tags, approval roles) are created through normal CRUD endpoints, not pre-seeded.
See [Notifications](/modules/notifications.md) and [Settings](/modules/settings.md).

# Ids (verified)

Every path parameter and body field carrying an id is typed as UUID in both the Pydantic
schemas and the SQLAlchemy models (`PGUUID(as_uuid=True)`), so a malformed id in a path or body
fails FastAPI/Pydantic validation and comes back as the 400 shape above, not a raw driver error.

# Roles (verified)

Only `TENANT_ADMIN`, `CONTRACT_OWNER`, `LEGAL_REVIEWER`, `APPROVER` appear as literals passed
into `require_roles(...)` across the router files sampled — no project-foreign role name found.
