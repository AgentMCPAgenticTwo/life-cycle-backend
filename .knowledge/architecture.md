---
type: Architecture
title: life-cycle-backend architecture
description: Layered FastAPI architecture with a single authorization chokepoint and five incrementally-added use-case modules sharing one app skeleton.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app
tags: [backend, architecture, fastapi]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ f6503176d1f18e22902205491eb04e6059b7ca03
    title: Codebase knowledge graph
status: stable
---

# Layering

Confirmed by sampling `contracts` and `approvals` (router -> service -> repository -> schema):

* **Routers** (`app/routers/contracts.py`): 5 functions — `list_contracts`, `get_contract`,
  `create_contract`, each a thin binding that depends on `require_roles(...)` and delegates to
  the service module. No query-building or business rules in router bodies.
* **Services** (`app/services/contracts.py`): 15 functions including private helpers
  (`_validate_dates`, `_validate_notice_period`, `_resolve_counterparty`,
  `_has_permitted_access`) plus the public `list_contracts`/`get_contract_detail`/
  `create_contract`. This is where validation, owner/role checks and DTO mapping
  (`_to_response`, `_to_list_item`) live.
* **Repositories** (`app/repositories/contracts.py`): 10 functions, all data access —
  `get_by_id`, `list_by_tenant`, `insert_contract`, `get_counterparty`, etc. No business rules;
  `_SORTABLE_COLUMNS` is the only non-query logic, and it's query-shaping (sort allow-list), not
  a business rule.

Two services have no router above them and are reached only from another service:
`app/services/contract_documents.py` (called by `create_contract`, see
[Contract Documents](/modules/contract-documents.md)) and `app/services/notifications.py`. They
still obey the rule — they own rules and delegate every query to a repository, including
[Contract Lifecycle](/modules/contract-lifecycle.md)'s `insert_document`/
`insert_contract_version`, rather than opening their own.

The same router -> service -> repository split holds for `approvals`
(`app/routers/approvals.py` -> `app/services/approvals.py`, 21 functions including
`_get_or_create_step_instance`, `_resolve_approver_for_step`, `_write_audit_log` -> repository).
The CLAUDE.md layering rule ("HTTP layer binds/validates, services own rules, repositories own
queries") holds as written across the sampled resources.

# Authorization chokepoint

`app/auth.py`'s `require_roles` dependency has **fan-in 93** — the single highest-fan-in symbol
in the graph (`get_architecture(aspects=["hotspots"])`). Every router wires it via
`Depends(require_roles("ROLE_A", "ROLE_B", ...))` using the exact role list from that endpoint's
module contract. `current_user` now resolves an `Authorization: Bearer <JWT>` into a
`CurrentUser` dataclass by decoding the token and loading the `users` row (role, tenant, name,
email, `must_change_password`) — it replaced the `X-User-Role`/`X-User-Id` header stub without
changing the dependency's signature, so no router was touched; see [Auth](/modules/auth.md).
`current_tenant_id` additionally joins the authenticated user id against the `users` table to
resolve a tenant scope, and is itself the join point every tenant-scoped resource relies on
instead of re-querying `users`. See [Conventions](/conventions.md) for the status-code contract
this enforces.

# Module clusters (from graph community detection)

12 clusters total; 6 are source clusters, 6 are test clusters. Source clusters align with the
five CLAUDE.md-documented generation batches plus one that spans two of them:

| Cluster | Members | Top symbols | Maps to |
|---|---|---|---|
| 13 | 178 | `require_roles`, `ConflictError`, `NotFoundError`, `create_routing`, `submit_review` | Core app infra (auth/errors) fanning into negotiation + approvals, which depend on it most |
| 1 | 113 | `ValidationFailedError`, `get_ownership_tab`, `get_bottleneck_tab`, `get_turnaround_tab` | `lifecycle-uc10-uc11` tracker tabs |
| 22 | 87 | `connect_integration`, `update_user_status`, `create_user`, `disconnect_integration` | `lifecycle-uc10-uc11` settings resources |
| 0 | 70 | `_get_contract_or_404`, `update_obligation`, `assign_folder_tags`, `create_obligation` | `life-cycle-uc8-uc9` contract lifecycle/obligations |
| 19 | 57 | `ForbiddenError`, `add_signer`, `verify_otp`, `apply_signature`, `update_signer` | `uc6-uc7-combined` signing |
| 10 | 40 | `submit_action`, `submit_delegation`, `get_approval_detail`, `get_history` | `uc6-uc7-combined` approval matrix |

The remaining 6 clusters (`_seed_tenant_and_user`, `_headers`, `_setup_basic`, etc.) are test
helper clusters in `tests/`.

# Hotspots (fan-in)

| Symbol | Fan-in |
|---|---|
| `app.auth.require_roles` | 93 |
| `builtins.len` | 40 |
| `builtins.str.lower` | 19 |
| `app.services.contract_lifecycle._get_contract_or_404` | 13 |
| `app.repositories.templates.list_by_tenant` | 9 |
| `app.services.contract_lifecycle._user_uuid` | 9 |
| `app.services.lifecycle_negotiation._get_contract_or_404` | 8 |
| `app.repositories.signing_sessions.list_by_contract` | 8 |

`_get_contract_or_404` is duplicated per-module (`contract_lifecycle`, `lifecycle_negotiation`)
rather than shared — consistent with CLAUDE.md's rule to add code alongside existing modules
rather than refactor shared helpers out from under them.

# Module-to-code mapping (verified, not assumed)

Verified by reading `app/main.py`'s router includes and router file contents, not just inferred
from CLAUDE.md's batch descriptions:

* **cross-cutting (not from a module contract)**: `app/routers/auth.py` — the `/auth/*` login
  surface added by correction trace `7d6ad1406e1b`, the one router `app/main.py` includes twice
  (with and without the `/api/v1` prefix). It follows the same router -> service -> repository
  split as the contract modules (`app/services/auth.py`, `app/repositories/auth.py`), with token
  and password primitives factored into `app/security.py`. See [Auth](/modules/auth.md).
* **uc123**: dashboard endpoints (`/dashboard/summary`, `/dashboard/my-tasks`,
  `/dashboard/high-risk-contracts`, `/dashboard/filters`) and `/users` live in
  `app/routers/lookups.py` (not a `dashboard.py` router — there isn't one). `contracts.py`,
  `templates.py`, `clauses.py`, `counterparties.py`, `contracts_third_party_paper.py` are
  separate router files for the rest of this batch.
* **lifecycle-uc4-uc5**: `lifecycle_clauses.py` (clause analysis/accept/edit/reject) and
  `lifecycle_negotiation.py` (metadata, ask-ai, routing, reviews, external link/otp/submit,
  compare, reminder, mark-agreed, comments) — the latter registers two routers,
  `lifecycle_negotiation.router` and `lifecycle_negotiation.external_router`.
* **uc6-uc7-combined**: `approvals.py`, `approval_matrix.py`, `signers.py`,
  `signing_sessions.py`, `esignature_settings.py`.
* **life-cycle-uc8-uc9**: `contract_lifecycle.py` registers two routers —
  `contract_lifecycle.router` (prefix `/contracts`, covers document/versions/activity-log/
  folder-tags/obligations/renewal/renew/amend/terminate) and
  `contract_lifecycle.folder_tags_router` (prefix `/folder-tags`) — plus `files.py` at the
  service/repository layer (no dedicated router; file endpoints are served from
  `contracts_third_party_paper.py` / `contract_lifecycle.py`).
* **lifecycle-uc10-uc11**: the six `tracker_*.py` router files (`tracker_ownership`,
  `tracker_cycle_time`, `tracker_bottleneck`, `tracker_bottleneck_thresholds`,
  `tracker_turnaround`, `tracker_export`) and the six `settings_*.py` router files
  (`settings_users`, `settings_approval_rules`, `settings_integrations`,
  `settings_notifications`, `settings_audit_log`).

See [modules/index.md](/modules/index.md) for a concept file per resource area.
