---
type: Module
title: dashboard-lookups
description: Dashboard summary/tasks/high-risk-contracts/filters and the shared users/counterparties/contracts lookup queries that back them, from the uc123 batch.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/lookups.py
tags: [backend, uc123, dashboard, lookups]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/lookups.py`, `app/services/lookups.py`, `app/repositories/lookups.py`,
`app/schemas/lookup.py`.

Note: there is no `dashboard.py` router file — all `/api/v1/dashboard/*` endpoints and
`GET /api/v1/users` are implemented in `lookups.py` despite the "dashboard" naming in the
module contract. See [Architecture](/architecture.md#module-to-code-mapping-verified-not-assumed).

# Endpoints (uc123 batch)

* `GET /dashboard/summary` -> `DashboardSummaryResponse`
* `GET /dashboard/my-tasks` -> `MyTasksResponse`
* `GET /dashboard/high-risk-contracts` -> `HighRiskContractsResponse`
* `GET /dashboard/filters` -> `DashboardFilterOptionsResponse`
* `GET /users` -> `UserOptionListResponse`

# Repository functions

`app/repositories/lookups.py`: `count_tenant_contracts`, `list_filtered_contracts`,
`list_current_tasks_for_assignee`, `list_owned_open_contracts`, `get_tenant`,
`get_counterparty`, `list_counterparties`, `list_distinct_departments`, `list_users_by_role`,
plus the private `_apply_contract_filters` query-shaping helper.

# Relationships

Reads the same `contracts`/`counterparties`/`users` tables that
[Contracts](/modules/contracts.md) and [Counterparties](/modules/counterparties.md) own —
this module only queries, it does not own the `contracts`/`counterparties` tables.
