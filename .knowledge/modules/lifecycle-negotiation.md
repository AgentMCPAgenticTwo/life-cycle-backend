---
type: Module
title: lifecycle-negotiation
description: Contract metadata editing, ask-AI, negotiation routing/reviews, external-party negotiation links with OTP, version comparison, reminders and mark-agreed.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/lifecycle_negotiation.py
tags: [backend, lifecycle-uc4-uc5, negotiation]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-15T05:59:28Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ f6d064f5cca1e68e91dc3418c66298f233273401
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

# Auto-send to counterparty and the OTP

`GenerateExternalLinkResponse` no longer carries an `otp` field. The OTP is hashed into
`otp_hash` and emailed by `_issue_external_link` through
[Notifications](/modules/notifications.md) (`EVENT_SENT_TO_COUNTERPARTY`), so UC5-BR-016 holds:
it reaches the External Party's inbox and nothing else. `_generate_otp` is the seam a test
patches, since no response exposes the value.

The mail body is built by `notifications.external_review_invite_body`, not inline here, and
leads with the clickable `/negotiation/external/{linkToken}` URL — the secure link reference on
its own gave the counterparty nothing to open. `tests/test_lifecycle_negotiation.py`'s
`test_counterparty_invite_mail_carries_the_review_url` asserts the URL, the reference and the
OTP all appear in the no-SMTP log line.

`_issue_external_link` is shared by two paths: the explicit `POST .../negotiation/external-link`,
and `submit_review`, which calls it automatically the moment `internal_review_complete` holds
(every reviewer `Submitted` — the last one under Sequential routing, all of them under
Parallel). The link is committed before the mail attempt. `send_reminder` likewise emails the
overdue reviewer (`EVENT_REVIEW_REMINDER`); the daily automatic variant lives in
[Scheduled Notifications](/modules/scheduled-notifications.md), which reads
`repo.list_overdue_routings` and `repo.list_reminders_since` from this module's repository.

# Routing, Mark as Agreed and the approval request

`create_routing` moves the contract to `In Negotiation` through
`app.services.contract_status.transition` — see [Contract Status](/modules/contract-status.md).
It accepts two cases:

* **First routing** — the contract must be `Draft` with a completed AI clause-analysis pass
  (UC5-BR-023) and have no routing yet; `repo.insert_routing` creates one at version 1.
* **Re-send after a Send Back** (`resend_after_send_back`: already `In Negotiation` with a
  routing whose `negotiation_status` is `NEGOTIATION_SENT_BACK`) — the existing routing is
  reused so the version history continues: `repo.delete_reviewers` clears the old reviewer list,
  the routing fields are rewritten, `negotiation_status` returns to `With Internal` and
  `current_version_number` is incremented.

`mark_agreed` makes agreement and the approval request one unit: it calls
`app.services.approvals.start_approval` **before** committing, so a contract with no matching
approval rule stays `In Negotiation` and un-Agreed (the `ConflictError` surfaces as 409). On
success the routing becomes `Agreed`, the contract moves to `Pending Approval`, and
`approvals.notify_step_approver` emails Step 1's approver after the commit. `NEGOTIATION_AGREED`
and `NEGOTIATION_SENT_BACK` are re-exported from `contract_status` so both modules agree on the
spelling.

# Hotspot

`app.services.lifecycle_negotiation._get_contract_or_404` — fan-in 8, a local analogue of the
same-named helper in [Contract Lifecycle](/modules/contract-lifecycle.md); each module keeps its
own copy rather than sharing, consistent with the "don't refactor another module's code" rule.

# Relationships

Consumes contracts from [Contracts](/modules/contracts.md); works with clause state from
[Lifecycle Clauses](/modules/lifecycle-clauses.md); feeds contracts into
[Approvals](/modules/approvals.md) once negotiation is marked agreed.
