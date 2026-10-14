---
type: Playbook
title: common-tasks
description: Where to go in life-cycle-backend to add an endpoint, a migration, a role check, or a new tracker tab without breaking an existing module.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app
tags: [backend, playbook]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 700de34973c81dd98062f0bef469b620e6fc976b
    title: Codebase knowledge graph
status: stable
---

# Add a new endpoint to an existing resource

1. Add the route function to `app/routers/<resource>.py`, wired with
   `Depends(require_roles(...))` using only roles from
   [Conventions > Roles](/conventions.md#roles-verified) — see [App Core](/modules/app-core.md).
2. Put validation/business rules in `app/services/<resource>.py`, not the router — see
   [Architecture > Layering](/architecture.md#layering) for the pattern to copy.
3. Put queries in `app/repositories/<resource>.py`. Keep repository functions free of business
   rules — they should only filter/sort/paginate.
4. Add/extend Pydantic DTOs in `app/schemas/<resource>.py`; map explicitly in the service's
   `_to_response`/`_to_list_item`-style function — no mapper library (see CLAUDE.md
   dependencies rule).
5. Register the router in `app/main.py` if it's new (`app.include_router(<module>.router,
   prefix="/api/v1")`) — never remove or reorder an existing include.

# Add a new table

1. Add a new SQLAlchemy model in the appropriate `app/models/<area>.py`, mixing in
   `TimestampMixin` and (if soft-deletable) `SoftDeleteMixin` from `app/models/mixins.py` — see
   [App Core](/modules/app-core.md).
2. Add a new Alembic revision under `alembic/versions/`, numbered after the highest existing
   revision (currently `0052_add_user_credentials_and_refresh_tokens.py`). **Never edit or
   reorder an existing migration** — see [Migrations](/modules/migrations.md).
3. If the table needs reference/lookup seed data, write an idempotent insert (existence check
   first). Copy `app.repositories.settings_notifications.ensure_seeded`, the repo's only
   seeder — it reads the existing names once and skips the ones already present, so it is safe
   to call on every request.

# Send a notification from a new action

Call `app.services.notifications.dispatch` **after** your own `db.commit()`, passing one of the
`EVENT_*` constants. A new event also needs its name added to
`app.repositories.settings_notifications.EVENT_NAMES`, or the toggle lookup misses the row. See
[Notifications](/modules/notifications.md).

# Add a role check

All authorization goes through `app.auth.require_roles(*allowed)` as a FastAPI `Depends` on the
route — see [App Core](/modules/app-core.md). Do not write ad hoc role checks in services;
owner/assignment checks (not just role) belong in the service layer using the authenticated user
id via `current_user`/`current_tenant_id`, matching the "owner/assignment checks use the
caller's identity, not the role alone" rule. Authentication itself is a bearer JWT — see
[Auth](/modules/auth.md).

# Touch the login / token flow

Rules go in `app/services/auth.py` (credential check, deactivation, rotation, password change);
primitives go in `app/security.py` (bcrypt hashing, `password_violations`, JWT signing,
refresh-token digest/expiry). `app/routers/auth.py` stays a thin binding plus
`_set_refresh_cookie`. Never log or return a raw refresh token: only its SHA-256 digest is
stored and it reaches the browser only in the httpOnly cookie. Config knobs (`JWT_SECRET`,
`ACCESS_TOKEN_TTL_MINUTES`, `REFRESH_TOKEN_TTL_DAYS`, `REFRESH_COOKIE_NAME`,
`REFRESH_COOKIE_SECURE`) live in `app/config.py` and come from the environment. In tests, use
`auth_headers` from `tests/conftest.py` — see [Tests](/modules/tests.md).

# Add a new tracker tab

Follow the five existing `tracker_*` resources in [Tracker](/modules/tracker.md): new router +
service + repository + schema file, sharing `TrackerQueryParams` input shape and the
`{rows, isEmpty, emptyStateMessage, totalCount, page, pageSize}` paged response shape. Wire the
AI-suggested vs. overridden value pattern (`estimatedTurnaroundSource`, override endpoints
writing to `turnaround_override_log`) the same way `tracker_turnaround.py` does if the new tab
needs an override/audit trail.

# Diagnose a 401 vs 403 vs 404 in a module

* 401: `Authorization` header missing, or the bearer token invalid/expired/pointing at an
  unknown user — both raised in `app/auth.py` (`current_user`, `current_tenant_id`).
* 403: the user's `users` row has `is_active` false (`current_user`), role present but not in
  that endpoint's `require_roles(...)` list (coarse), or
  `app.errors.ForbiddenError` raised by a service for a fine-grained owner/assignment check.
* 404: `app.errors.NotFoundError`, typically from a `_get_contract_or_404`-style helper — see
  the hotspot note in [Contract Lifecycle](/modules/contract-lifecycle.md) and
  [Lifecycle Negotiation](/modules/lifecycle-negotiation.md) (each module keeps its own copy).

See [Conventions](/conventions.md) for the full verified rule set and
[Reference > Graph Queries](/reference/graph-queries.md) for how to explore further via the
live graph instead of grepping.
