---
type: Module
title: approval-matrix
description: Tenant-level approval matrix configuration (steps/thresholds) that approvals routing reads to decide who must approve.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/approval_matrix.py
tags: [backend, uc6-uc7-combined, approval-matrix]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
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

# Relationships

Read by [Approvals](/modules/approvals.md)' `_resolve_approver_for_step` and
`_get_or_create_step_instance` to determine step configuration. Distinct from the newer,
simpler per-contract-type `approval_matrix_rules` table owned by
[Settings](/modules/settings.md) (`settings_approval_rules`) — two approval-configuration
surfaces coexist because they were added in different batches (`uc6-uc7-combined` vs.
`lifecycle-uc10-uc11`) and CLAUDE.md requires adding beside rather than replacing.
