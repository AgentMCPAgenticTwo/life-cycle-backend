---
type: Module
title: approvals
description: Approval queue, step-by-step approve/reject/request-changes actions, delegation and history, the second layering-verification sample for this repo.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/approvals.py
tags: [backend, uc6-uc7-combined, approvals]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-15T05:15:24Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 24c451af17fc14c47102e38019b754771e026556
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

# Where an approval comes from

There is still no endpoint that creates an `Approval`; `start_approval` is called in-process by
`app.services.lifecycle_negotiation.mark_agreed` (UC5) and opens Step 1:

* `_matching_matrix_config` picks the UC6 Approval Matrix config for the contract's type whose
  value — and, when a risk score exists, risk — band contains it and that has steps; the
  narrowest value band wins. Configs with `archived_at` set are skipped: they are superseded
  rows kept only so the approvals already pointing at them still resolve their steps — see
  [Approval Matrix](/modules/approval-matrix.md). Its steps resolve lazily through `_get_or_create_step_instance`.
* With no matrix config, `_matching_settings_rules` falls back to the UC11
  `approval_matrix_rules` rows (see [Settings](/modules/settings.md)) whose `value_threshold`
  the contract meets, lowest first, one step each; `_approver_for_role` maps the rule's display
  role (`_RULE_ROLE_TO_USER_ROLE`) to a live user, never the Contract Owner (UC6-BR-011), and
  raises `ConflictError` when none holds the role.
* No rule at all raises `ConflictError` with `NO_MATCHING_RULE_MESSAGE` before anything is
  written, so the negotiation stays un-Agreed.
* Any approval still `PendingApproval` is superseded (`SentBack`) rather than reused — history
  keeps it and the new request restarts at Step 1.

`notify_step_approver` then emails the current step's approver (`EVENT_SENT_FOR_APPROVAL`), and
is called again by `submit_action` whenever an Approve advances to a further step.

# Statuses

Approval statuses are the module-local constants `APPROVAL_PENDING`, `APPROVAL_APPROVED`,
`APPROVAL_REJECTED`, `APPROVAL_SENT_BACK` (`ReadyForSignature` is gone — migration 0053 rewrites
it to `Approved`). Contract statuses are no longer assigned here: `submit_action` goes through
`app.services.contract_status.transition`, so every change lands in the Activity Log — see
[Contract Status](/modules/contract-status.md).

| Action | Approval | Contract |
|---|---|---|
| Reject | `Rejected` | `Rejected` |
| SendBack | `SentBack` (closed, kept for history) | `In Negotiation`, routing back to `Sent Back` |
| Approve, more steps | `PendingApproval`, next step instance created | unchanged (`Pending Approval`) |
| Approve, last step | `Approved` | `Pending Signature` |

A Send Back no longer deletes the prior step instances and resets the sequence (UC6-BR-005 is
now satisfied by closing the request); the next Mark as Agreed opens a fresh one.

# Layering (second reference sample)

Router (`app/routers/approvals.py`): 7 symbols, each a thin binding
(`list_approvals`, `get_approval`, `submit_action`, `submit_delegation`, `get_history`).

Service (`app/services/approvals.py`): the largest service file sampled.
Business rules live in `start_approval`, `_resolve_approver_for_step`, `_get_or_create_step_instance`,
`_active_delegation_for`, and the big `submit_action`/`submit_delegation` functions
(each 100+ lines); `_write_audit_log` centralizes audit-trail writes for this resource.
`_ACTION_EVENTS` maps each wire action (`Approve`/`Reject`/`SendBack`) to a notification event,
and `_notify_action` fires it — plus the ready-for-signature event when the final step clears —
through [Notifications](/modules/notifications.md), after `submit_action` has committed.
See [Architecture > Layering](/architecture.md#layering) for the evidence this confirms the
CLAUDE.md layering rule.

# Relationships

Consumes contracts from [Contracts](/modules/contracts.md) once routed for approval by
[Lifecycle Negotiation](/modules/lifecycle-negotiation.md), which calls `start_approval`
directly; approved contracts move to [Signers/Signing](/modules/signing.md) as
`Pending Signature`. Status changes go through [Contract Status](/modules/contract-status.md). Approval thresholds/roles are configured via
[Approval Matrix](/modules/approval-matrix.md) and (per-tenant) via
[Tracker/Settings](/modules/settings.md)'s `approval-rules` endpoints — two separate
approval-configuration surfaces from two different generation batches (see
`approval_matrix_configs`/`approval_matrix_steps` tables vs. the newer
`approval_matrix_rules` table).
