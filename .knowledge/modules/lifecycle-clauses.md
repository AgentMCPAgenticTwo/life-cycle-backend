---
type: Module
title: lifecycle-clauses
description: AI-assisted clause analysis, suggestion acceptance, manual editing and rejection for a contract in the drafting stage.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/lifecycle_clauses.py
tags: [backend, lifecycle-uc4-uc5, clauses]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-15T05:59:28Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ f6d064f5cca1e68e91dc3418c66298f233273401
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

# UC5 risk re-check after a counterparty submission

`app/services/lifecycle_clauses.py` owns the re-check that runs when an external party submits
redlines. There is no AI pipeline in this sandbox, so re-scoring is a deterministic keyword
pass (`_HIGH_RISK_TERMS` / `_MEDIUM_RISK_TERMS` / `_score_clause_text`); the behaviour around
it is what UC5 specifies.

| Symbol | Role |
|---|---|
| `apply_external_redlines` | Applies the submission and returns the ids of the clauses it changed. |
| `reanalyze_clauses` | Re-scores exactly those clauses and recomputes the overall risk. |
| `pending_reanalysis_failure` | The outstanding failure, if the latest attempt failed and was not retried. |
| `_record_reanalysis_failure` | Writes the `Re-analysis Failed` audit row, storing the unscored clause ids. |
| `_clause_ids_from_failure` | Parses those ids back out so Retry re-analyses exactly them. |

Two submission shapes are accepted: structured `clauseId`/`clauseText` pairs replace the named
clauses, while a plain redline document — all the external-submit contract guarantees — marks a
clause changed when its current text no longer appears verbatim in the document. A failure
leaves the saved version intact with a retryable `Failed` status rather than rolling back.
`app/repositories/lifecycle_clauses.py` adds `get_latest_audit_entry` (newest
`ClauseAuditLog` row for an action-type set and optional `field_name`) to support this.

# Proceed to Negotiation once the contract is already routed

Both `_build_analysis_response` and `proceed_to_negotiation` ask
`app.repositories.lifecycle_negotiation.get_routing_by_contract` whether a routing exists — this
module's only dependency on the negotiation repository.

| Without a routing | With a routing |
|---|---|
| `proceedToNegotiationEnabled` is false while any clause carries the Missing-Mandatory flag (UC4-BR-005/AF-006) | the flag no longer blocks: the screen stores no "already proceeded" state, so a false here would strand the Legal Reviewer on a reload with no way back into a negotiation they are already in |
| `proceed_to_negotiation` raises `ConflictError` (409) on a mandatory flag | calling it again is idempotent and reports where the negotiation stands — `negotiationStatus` from `routing.negotiation_status`, `routedAt` from `routing.created_at`, instead of the fixed `Ready for Negotiation`/`null` |

A `pending_reanalysis_failure` still disables the button in both cases — unlike a mandatory
flag, a retry can clear it. Covered by
`test_already_routed_contract_still_offers_proceed_to_negotiation` in
`tests/test_lifecycle_negotiation.py`.

# Relationships

Operates on contracts owned by [Contracts](/modules/contracts.md) and clauses from
[Templates/Clauses](/modules/templates-clauses.md); feeds into
[Lifecycle Negotiation](/modules/lifecycle-negotiation.md)'s `proceed-to-negotiation` step and,
through `apply_external_redlines`, into its `external_submit` handler. Re-check behaviour is
covered by `tests/test_lifecycle_uc5_recheck.py` — see [Tests](/modules/tests.md).
