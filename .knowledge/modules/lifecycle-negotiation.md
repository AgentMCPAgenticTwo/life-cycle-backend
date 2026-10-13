---
type: Module
title: lifecycle-negotiation
description: Contract metadata editing, ask-AI, negotiation routing/reviews, external-party negotiation links with OTP, version comparison, reminders and mark-agreed.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/lifecycle_negotiation.py
tags: [backend, lifecycle-uc4-uc5, negotiation]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
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

External (`external_router`, token-based, no `X-User-Role`/`X-User-Id`):
`POST /negotiation/external/{linkToken}/verify-otp`,
`POST /negotiation/external/{linkToken}/submit`.

# Hotspot

`app.services.lifecycle_negotiation._get_contract_or_404` — fan-in 8, a local analogue of the
same-named helper in [Contract Lifecycle](/modules/contract-lifecycle.md); each module keeps its
own copy rather than sharing, consistent with the "don't refactor another module's code" rule.

# Relationships

Consumes contracts from [Contracts](/modules/contracts.md); works with clause state from
[Lifecycle Clauses](/modules/lifecycle-clauses.md); feeds contracts into
[Approvals](/modules/approvals.md) once negotiation is marked agreed.
