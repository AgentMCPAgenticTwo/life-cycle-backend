---
type: Module
title: contract-lifecycle
description: Executed-contract detail, document retrieval, version history, activity log, folder tags, obligations, and renewal/amendment/termination actions.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/contract_lifecycle.py
tags: [backend, life-cycle-uc8-uc9, contract-lifecycle, obligations]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ f6503176d1f18e22902205491eb04e6059b7ca03
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/contract_lifecycle.py` (registers `router`, prefix `/contracts`, and
`folder_tags_router`, prefix `/folder-tags`), `app/services/contract_lifecycle.py`,
`app/repositories/contract_lifecycle.py`, `app/schemas/contract_lifecycle.py`,
`app/models/contract_lifecycle.py`.

# Endpoints

* `GET /contracts`, `GET /contracts/{contractId}` (detail), `GET .../document`,
  `GET .../document/download`, `GET .../versions`, `GET .../activity-log`
* `POST .../folder-tags`, `GET /folder-tags`
* `GET/POST .../obligations`, `PATCH .../obligations/{obligationId}`,
  `POST .../obligations/{obligationId}/accept`
* `GET .../renewal`, `POST .../renew`, `POST .../amend`, `POST .../terminate`

# Hotspots

`app.services.contract_lifecycle._get_contract_or_404` — fan-in 13, the single most-reused
helper outside `app/auth.py`. `app.services.contract_lifecycle._user_uuid` — fan-in 9.

# Write helpers used by other modules

`app/repositories/contract_lifecycle.py` exposes `insert_document` and
`insert_contract_version` (add + flush, no commit) alongside its read queries. They are the
only writers of `contract_documents`/`contract_versions` outside this module's own services,
and exist so [Contract Documents](/modules/contract-documents.md) can create a contract's
Version 1 inside the caller's transaction without duplicating this module's models.

# Relationships

Operates on contracts created via [Contracts](/modules/contracts.md); delegates document
storage to [Files](/modules/files.md); `renew`/`amend` actions create linked contracts that
re-enter the same lifecycle. Stage transitions recorded here are the source of the
`contract_lifecycle_stage_history` and `contract_owners` tables that
[Tracker](/modules/tracker.md) reports on.
