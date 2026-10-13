---
type: Module
title: templates-clauses
description: Reusable contract template and clause library with versioning, activation lifecycle, and the version-history endpoints shared by both resources.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/templates.py
tags: [backend, uc123, templates, clauses]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/templates.py`, `app/routers/clauses.py`, `app/services/templates.py`,
`app/services/clauses.py`, `app/repositories/templates.py`, `app/repositories/clauses.py`,
`app/schemas/template.py`, `app/schemas/clause.py`, `app/models/template.py`,
`app/models/clause.py`.

# Endpoints

* `GET /templates`, `POST /templates`, `PUT /templates/{id}`,
  `POST /templates/{id}/deactivate`, `POST /templates/{id}/reactivate`,
  `GET /templates/{id}/versions`
* `GET /clauses`, `POST /clauses`, `PUT /clauses/{id}`, `POST /clauses/{id}/deactivate`,
  `POST /clauses/{id}/reactivate`, `GET /clauses/{id}/versions`

Both resources share the same lifecycle shape (create -> edit creates a version -> deactivate/
reactivate) and the same `VersionHistoryResponse` DTO shape.

# Hotspot

`app.repositories.templates.list_by_tenant` has fan-in 9 — read from multiple places beyond its
own router (e.g. contract creation's `_validate_template_and_paper_selection` in
[Contracts](/modules/contracts.md) looks up templates via this module's repository).

# Relationships

* Depended on by [Contracts](/modules/contracts.md) (template selection at contract creation)
  and [Lifecycle Clauses](/modules/lifecycle-clauses.md) (clause analysis against a contract's
  selected clauses).
