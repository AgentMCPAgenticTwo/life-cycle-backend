---
type: Module
title: lifecycle-clauses
description: AI-assisted clause analysis, suggestion acceptance, manual editing and rejection for a contract in the drafting stage.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/lifecycle_clauses.py
tags: [backend, lifecycle-uc4-uc5, clauses]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/lifecycle_clauses.py`, `app/services/lifecycle_clauses.py`,
`app/repositories/lifecycle_clauses.py`, `app/schemas/lifecycle_clause.py`,
`app/models/lifecycle_clause.py`.

# Endpoints

* `GET /lifecycle/contracts/{contractId}/clause-analysis` -> `ClauseAnalysisResponse`
* `POST /lifecycle/contracts/{contractId}/clauses/{clauseId}/accept-suggestion`
* `PUT /lifecycle/contracts/{contractId}/clauses/{clauseId}` (`EditClauseRequest`)
* `POST /lifecycle/contracts/{contractId}/clauses/{clauseId}/reject` (`RejectClauseRequest`)

# Relationships

Operates on contracts owned by [Contracts](/modules/contracts.md) and clauses from
[Templates/Clauses](/modules/templates-clauses.md); feeds into
[Lifecycle Negotiation](/modules/lifecycle-negotiation.md)'s `proceed-to-negotiation` step.
