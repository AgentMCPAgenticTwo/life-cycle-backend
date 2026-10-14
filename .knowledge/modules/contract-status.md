---
type: Module
title: contract-status
description: The one contract status flow — the shared `contracts.status` vocabulary, the `transition` helper that logs every change to the Activity Log, and the legacy-value readers.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/contract_status.py
tags: [backend, contracts, workflow, status]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T12:47:46Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ b0c64d78730b6ed271020fb3e7d89002e374f6da
    title: Codebase knowledge graph
status: stable
---

# Files

`app/services/contract_status.py` only — no router, schema or model of its own. It writes
`Contract.status` (`app/models/contract.py`) and appends `ActivityLogEntry`
(`app/models/contract_lifecycle.py`) through
[Contract Lifecycle](/modules/contract-lifecycle.md)'s `insert_activity_log`.
`alembic/versions/0053_unify_contract_status_flow.py` rewrites the rows written before it.

# The flow

```
Draft -> In Negotiation -> Pending Approval -> Pending Signature -> Executed
```

with `Rejected` (an approver rejects) and `Signature Declined` (a signer declines) as the other
outcomes — the constants `DRAFT`, `IN_NEGOTIATION`, `PENDING_APPROVAL`, `PENDING_SIGNATURE`,
`EXECUTED`, `REJECTED`, `SIGNATURE_DECLINED`.

`Ready For Signature` and `Sent` are **no longer contract statuses**: `Sent`, `Viewed`, `Signed`
and `Declined` are per-signer states only, owned by [Signing](/modules/signing.md).

# Symbols

| Symbol | Role |
|---|---|
| `transition` | The single place a workflow step changes the status; sets `status`/`updated_by`/`updated_at` and appends one Activity Log row (`ACTIVITY_ACTION_STATUS_CHANGE`, details `"Status changed from X to Y[: reason]"`). A no-op change logs nothing. Does **not** commit — the caller's unit of work decides. |
| `is_pending_signature` | True for `Pending Signature` or either value in `LEGACY_PENDING_SIGNATURE` (`Ready For Signature`, `Sent`). |
| `is_signature_declined` | True for `Signature Declined` or the legacy `SignatureDeclined`. |
| `NEGOTIATION_AGREED` / `NEGOTIATION_SENT_BACK` | The two `negotiation_routings.negotiation_status` values the approval flow reads or writes (`Agreed`, `Sent Back`). |

# Legacy values

Read paths still recognise `Ready For Signature`, `Sent` and `SignatureDeclined` through the two
`is_*` helpers, so a row migration 0053 has not reached behaves like its replacement. The same
three strings stay listed in `ContractStatus` in `app/schemas/contract.py` purely so such a row
cannot 500 a contract GET — nothing writes them any more.

# Migration 0053

`UnifyContractStatusFlow` (revision id `UnifyContractStatusFlow`, down-revision
`AddUserCredentialsAndRefreshTokens`) is **data-only** — no DDL. It folds the two legacy
signature statuses into `Pending Signature`, renames `SignatureDeclined`, rewrites an approval
left on `ReadyForSignature` to `Approved`, promotes a `Draft` contract that already has a
negotiation routing to `In Negotiation`, and closes an approval left open by an old Send Back
(`SentBack`, its routing re-opened to `Sent Back`). `downgrade` is intentionally empty: the fold
is lossy forward and the old values remain readable. See [Migrations](/modules/migrations.md).

# Callers

| Caller | Transition |
|---|---|
| `app.services.lifecycle_negotiation.create_routing` | -> `In Negotiation` when a contract is routed for review |
| `app.services.lifecycle_negotiation.mark_agreed` | -> `Pending Approval`, together with `approvals.start_approval` |
| `app.services.approvals.submit_action` | -> `Rejected`, back to `In Negotiation` on Send Back, or -> `Pending Signature` when the last step is approved |
| `app.services.signers.send_for_signature` | normalises a legacy row to `Pending Signature`; sending does not advance the status |
| `app.services.signing_sessions.decline_signature` | -> `Signature Declined` |

# Relationships

Shared by [Lifecycle Negotiation](/modules/lifecycle-negotiation.md),
[Approvals](/modules/approvals.md) and [Signing](/modules/signing.md); the values it writes are
the ones [Contracts](/modules/contracts.md) serialises (`ContractStatus`) and the ones
[Tracker](/modules/tracker.md)'s `STATUS_TO_STAGE` maps onto reporting stages.
