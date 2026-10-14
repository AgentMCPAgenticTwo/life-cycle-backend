---
type: Module
title: approvals
description: Approval queue, step-by-step approve/reject/request-changes actions, delegation and history, the second layering-verification sample for this repo.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/approvals.py
tags: [backend, uc6-uc7-combined, approvals]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/approvals.py`, `app/services/approvals.py`, `app/repositories/approvals.py`,
`app/schemas/approval.py`, `app/models/approval.py`.

# Endpoints

* `GET /approvals` -> `ApprovalListResponse` (paged)
* `GET /approvals/{approvalId}` -> `ApprovalResponse`
* `POST /approvals/{approvalId}/actions` -> `ApprovalActionResponse`
* `POST /approvals/{approvalId}/delegate` -> `DelegateResponse`
* `GET /approvals/{approvalId}/history` -> `ApprovalHistoryListResponse`

# Layering (second reference sample)

Router (`app/routers/approvals.py`): 7 symbols, each a thin binding
(`list_approvals`, `get_approval`, `submit_action`, `submit_delegation`, `get_history`).

Service (`app/services/approvals.py`): 21 functions — the largest service file sampled.
Business rules live in `_resolve_approver_for_step`, `_get_or_create_step_instance`,
`_active_delegation_for`, and the big `submit_action`/`submit_delegation` functions
(each 100+ lines); `_write_audit_log` centralizes audit-trail writes for this resource.
`_ACTION_EVENTS` maps each wire action (`Approve`/`Reject`/`SendBack`) to a notification event,
and `_notify_action` fires it — plus the ready-for-signature event when the final step clears —
through [Notifications](/modules/notifications.md), after `submit_action` has committed.
See [Architecture > Layering](/architecture.md#layering) for the evidence this confirms the
CLAUDE.md layering rule.

# Relationships

Consumes contracts from [Contracts](/modules/contracts.md) once routed for approval by
[Lifecycle Negotiation](/modules/lifecycle-negotiation.md); approved contracts move to
[Signers/Signing](/modules/signing.md). Approval thresholds/roles are configured via
[Approval Matrix](/modules/approval-matrix.md) and (per-tenant) via
[Tracker/Settings](/modules/settings.md)'s `approval-rules` endpoints — two separate
approval-configuration surfaces from two different generation batches (see
`approval_matrix_configs`/`approval_matrix_steps` tables vs. the newer
`approval_matrix_rules` table).
