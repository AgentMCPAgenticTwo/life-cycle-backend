---
type: Playbook
title: common-tasks
description: Where to go in life-cycle-backend to add an endpoint, a migration, a role check, or a new tracker tab without breaking an existing module.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app
tags: [backend, playbook]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
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
   revision (currently `0051_create_tenant_audit_log.py`). **Never edit or reorder an existing
   migration** — see [Migrations](/modules/migrations.md).
3. If the table needs reference/lookup seed data, write an idempotent insert (existence check
   first) — note that no such seeding code exists anywhere yet in this repo (see
   [Conventions > Deviation](/conventions.md#deviation-found-no-idempotent-reference-data-seeding-in-code)),
   so there is no existing pattern to copy; write it from CLAUDE.md's rule directly.

# Add a role check

All authorization goes through `app.auth.require_roles(*allowed)` as a FastAPI `Depends` on the
route — see [App Core](/modules/app-core.md). Do not write ad hoc role checks in services;
owner/assignment checks (not just role) belong in the service layer using `X-User-Id` via
`current_user`/`current_tenant_id`, matching the "Owner/assignment checks use X-User-Id, not the
role alone" rule.

# Add a new tracker tab

Follow the five existing `tracker_*` resources in [Tracker](/modules/tracker.md): new router +
service + repository + schema file, sharing `TrackerQueryParams` input shape and the
`{rows, isEmpty, emptyStateMessage, totalCount, page, pageSize}` paged response shape. Wire the
AI-suggested vs. overridden value pattern (`estimatedTurnaroundSource`, override endpoints
writing to `turnaround_override_log`) the same way `tracker_turnaround.py` does if the new tab
needs an override/audit trail.

# Diagnose a 401 vs 403 vs 404 in a module

* 401: `X-User-Role` missing, or `X-User-Id` missing/unparseable/unknown — both raised in
  `app/auth.py` (`current_user`, `current_tenant_id`).
* 403: role present but not in that endpoint's `require_roles(...)` list (coarse), or
  `app.errors.ForbiddenError` raised by a service for a fine-grained owner/assignment check.
* 404: `app.errors.NotFoundError`, typically from a `_get_contract_or_404`-style helper — see
  the hotspot note in [Contract Lifecycle](/modules/contract-lifecycle.md) and
  [Lifecycle Negotiation](/modules/lifecycle-negotiation.md) (each module keeps its own copy).

See [Conventions](/conventions.md) for the full verified rule set and
[Reference > Graph Queries](/reference/graph-queries.md) for how to explore further via the
live graph instead of grepping.
