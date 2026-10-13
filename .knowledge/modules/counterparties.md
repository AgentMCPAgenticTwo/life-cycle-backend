---
type: Module
title: counterparties
description: Counterparty directory used by contract creation and dashboard filters.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/counterparties.py
tags: [backend, uc123, counterparties]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/counterparties.py`, `app/services/counterparties.py`,
`app/repositories/counterparties.py`, `app/schemas/counterparty.py`,
`app/models/counterparty.py`.

# Endpoints

* `GET /counterparties` -> `CounterpartySearchResponse`
* `POST /counterparties` -> `CounterpartyResponse` (`CreateCounterpartyRequest`)

# Relationships

Read by [Contracts](/modules/contracts.md) (`get_counterparty`/`insert_counterparty` in
`app/repositories/contracts.py` duplicate narrow lookups against the same `counterparties`
table) and by [Dashboard/Lookups](/modules/dashboard-lookups.md) for dashboard filter options.
