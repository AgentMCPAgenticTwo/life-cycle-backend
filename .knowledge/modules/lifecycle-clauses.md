---
type: Module
title: lifecycle-clauses
description: AI-assisted clause analysis, suggestion acceptance, manual editing and rejection for a contract in the drafting stage.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/lifecycle_clauses.py
tags: [backend, lifecycle-uc4-uc5, clauses]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ f6503176d1f18e22902205491eb04e6059b7ca03
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

# Relationships

Operates on contracts owned by [Contracts](/modules/contracts.md) and clauses from
[Templates/Clauses](/modules/templates-clauses.md); feeds into
[Lifecycle Negotiation](/modules/lifecycle-negotiation.md)'s `proceed-to-negotiation` step and,
through `apply_external_redlines`, into its `external_submit` handler. Re-check behaviour is
covered by `tests/test_lifecycle_uc5_recheck.py` — see [Tests](/modules/tests.md).
