---
type: Module
title: approval-matrix
description: Tenant-level approval matrix configuration (steps/thresholds) that approvals routing reads to decide who must approve.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/approval_matrix.py
tags: [backend, uc6-uc7-combined, approval-matrix]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-15T05:15:24Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 24c451af17fc14c47102e38019b754771e026556
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/approval_matrix.py`, `app/services/approval_matrix.py`,
`app/repositories/approval_matrix.py`, `app/schemas/approval_matrix.py` (models live in
`app/models/approval.py` alongside the `approvals` tables).

# Endpoints

* `GET /approval-matrix-config` -> `ApprovalMatrixConfigListResponse`
* `PUT /approval-matrix-config` -> `ApprovalMatrixConfigResponse`

# Saving the matrix archives, it does not delete

`PUT /approval-matrix-config` replaces the tenant's whole matrix, so `repo.delete_all` runs
first. A config an existing `approvals.config_id` still points at cannot be deleted — the
foreign key rejects it, and dropping it would strip that approval of its step names and
approvers. `delete_all` therefore splits the tenant's configs:

* configs referenced by an `Approval` get `archived_at` stamped (`ApprovalMatrixConfig.archived_at`,
  added by `alembic/versions/0054_archive_approval_matrix_configs.py`, revision
  `ArchiveApprovalMatrixConfigs`) and keep their steps;
* unreferenced configs and their `approval_matrix_steps` rows are deleted outright.

`list_by_tenant` and [Approvals](/modules/approvals.md)' `_matching_matrix_config` both filter
`archived_at IS NULL`, so an archived config is invisible to the matrix screen and to rule
matching while staying readable for the approvals that reference it.
`tests/test_approval_matrix.py::test_put_keeps_configs_that_approvals_still_reference` pins
this.

# Relationships

Read by [Approvals](/modules/approvals.md)' `_resolve_approver_for_step` and
`_get_or_create_step_instance` to determine step configuration. Distinct from the newer,
simpler per-contract-type `approval_matrix_rules` table owned by
[Settings](/modules/settings.md) (`settings_approval_rules`) — two approval-configuration
surfaces coexist because they were added in different batches (`uc6-uc7-combined` vs.
`lifecycle-uc10-uc11`) and CLAUDE.md requires adding beside rather than replacing.
