---
type: Convention
title: life-cycle-backend conventions
description: Header-auth, layering, persistence, error-shape and id conventions as actually implemented, verified line-by-line against CLAUDE.md's stated rules.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app
tags: [backend, conventions, auth, persistence]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Header-auth (verified in `app/auth.py`)

* `X-User-Role` and `X-User-Id` are both declared via `fastapi.security.APIKeyHeader` with
  distinct `scheme_name`s (`UserRoleHeader`, `UserIdHeader`) — this is what makes them appear as
  OpenAPI security schemes so Swagger's "Authorize" UI actually sends them.
* Missing `X-User-Role` -> `current_user` raises `HTTPException(401)`. A role outside an
  endpoint's allowed list -> `require_roles`'s inner `_check` raises `HTTPException(403)`.
* `current_tenant_id` additionally resolves `X-User-Id` to a `users` row to get `tenant_id`; an
  unparseable or unknown `X-User-Id` is also a 401, not a 400 — treated as "no auth", not "bad
  input".
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
  `"*"`. `allow_headers` includes `Content-Type`, `X-User-Role`, `X-User-Id`.

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

# Deviation found: no idempotent reference-data seeding in code

CLAUDE.md requires: "Seed only reference/lookup data, and make seeding idempotent... guard every
insert with an existence check." **No seeding logic exists in `app/` or `alembic/` at all** —
searches for `seed`, `INSERT INTO`, and `op.bulk_insert` across `alembic/versions/` and `app/`
found no reference-data seed step (the hits for "seed" in `app/services/lifecycle_clauses.py`,
`settings_integrations.py`, `settings_notifications.py` are unrelated identifiers, not seeding
code). This isn't necessarily a bug — none of the five modules' contracts appear to define
fixed reference/lookup data that needs seeding (lookups like folder tags, approval roles, etc.
are created via normal CRUD endpoints, not pre-seeded) — but it means the idempotent-seeding
convention has no code to check against, and a future module that *does* need seed data should
not assume a pattern already exists to copy.

# Ids (verified)

Every path parameter and body field carrying an id is typed as UUID in both the Pydantic
schemas and the SQLAlchemy models (`PGUUID(as_uuid=True)`), so a malformed id in a path or body
fails FastAPI/Pydantic validation and comes back as the 400 shape above, not a raw driver error.

# Roles (verified)

Only `TENANT_ADMIN`, `CONTRACT_OWNER`, `LEGAL_REVIEWER`, `APPROVER` appear as literals passed
into `require_roles(...)` across the router files sampled — no project-foreign role name found.
