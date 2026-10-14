---
type: Module
title: lifecycle-negotiation
description: Contract metadata editing, ask-AI, negotiation routing/reviews, external-party negotiation links with OTP, version comparison, reminders and mark-agreed.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/lifecycle_negotiation.py
tags: [backend, lifecycle-uc4-uc5, negotiation]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ f6503176d1f18e22902205491eb04e6059b7ca03
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/lifecycle_negotiation.py` (registers two routers: `router` and
`external_router`, both included in `app/main.py`), `app/services/lifecycle_negotiation.py`,
`app/repositories/lifecycle_negotiation.py`, `app/schemas/lifecycle_negotiation.py`,
`app/models/lifecycle_negotiation.py`.

# Endpoints

Internal (`router`): `PUT .../metadata`, `POST .../ask-ai`, `POST .../proceed-to-negotiation`,
`POST .../retry-extraction`, `GET .../audit-log`, `POST .../negotiation/routing`,
`GET .../negotiation`, `POST .../negotiation/reviews`, `POST .../negotiation/external-link`,
`GET .../negotiation/compare`, `POST .../negotiation/reminder`,
`POST .../negotiation/mark-agreed`, `POST .../negotiation/comments`.

External (`external_router`, link-token based, no `Authorization` bearer token):
`POST /negotiation/external/{linkToken}/verify-otp`,
`POST /negotiation/external/{linkToken}/submit`.

# Version source casing

`VersionSummaryResponse.source` is `Internal`/`External` on the wire — the frontend compares it
literally — and the same strings are persisted, per the "store enum-like values as their string
names" rule in [Conventions](/conventions.md). `_SOURCE_INTERNAL`/`_SOURCE_EXTERNAL` are the
constants `create_routing` and `submit_review` write; `_normalize_source` keeps rows written
before the casing was corrected readable in `get_tracker`.

# External submit and the UC5 re-check

`ExternalSubmitRequest` gained an optional `clauseRedlines` list (`ClauseRedlineRequest`:
`clauseId` + `clauseText`), which is not in the frontend's type — a caller sending only
`redlineText` still works. `external_submit` passes it to
`app.services.lifecycle_clauses.apply_external_redlines` *before* snapshotting the new version,
so Compare Versions shows the real diff and the re-check knows which clauses to re-score. See
[Lifecycle Clauses](/modules/lifecycle-clauses.md).

# Hotspot

`app.services.lifecycle_negotiation._get_contract_or_404` — fan-in 8, a local analogue of the
same-named helper in [Contract Lifecycle](/modules/contract-lifecycle.md); each module keeps its
own copy rather than sharing, consistent with the "don't refactor another module's code" rule.

# Relationships

Consumes contracts from [Contracts](/modules/contracts.md); works with clause state from
[Lifecycle Clauses](/modules/lifecycle-clauses.md); feeds contracts into
[Approvals](/modules/approvals.md) once negotiation is marked agreed.
