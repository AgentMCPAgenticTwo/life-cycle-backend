---
type: Module
title: tracker
description: Management tracker with four reporting tabs (ownership, cycle-time, bottleneck, turnaround), export, turnaround overrides and tenant bottleneck thresholds.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/tracker_ownership.py
tags: [backend, lifecycle-uc10-uc11, tracker, reporting]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

Six router files, each with matching service/repository/schema:
`tracker_ownership.py`, `tracker_cycle_time.py`, `tracker_bottleneck.py`,
`tracker_bottleneck_thresholds.py`, `tracker_turnaround.py`, `tracker_export.py` under
`app/routers/`, `app/services/`, `app/schemas/`
(`app/repositories/` has all but `tracker_export.py`, which has no dedicated repository file —
export reuses the other five tabs' repositories). Models live in `app/models/tracker.py`.

# Endpoints

* `GET /tracker/ownership` -> `OwnershipTabResponse` (paged)
* `GET /tracker/cycle-time` -> `CycleTimeTabResponse` (paged)
* `GET /tracker/bottleneck` -> `BottleneckTabResponse` (paged)
* `GET /tracker/turnaround` -> `TurnaroundTabResponse` (paged)
* `POST /tracker/export` -> `TrackerExportResponse`
* `PUT /tracker/turnaround/{contractId}/estimated-override` -> `TurnaroundRowResponse`
* `GET /tracker/bottleneck-thresholds` (TENANT_ADMIN only) -> `BottleneckThresholdResponse`

All four tab GETs share `TrackerQueryParams` (period/contractTypeFilter/ownerFilter/
dateRangeFrom/dateRangeTo/page/pageSize) and the `{rows, isEmpty, emptyStateMessage, totalCount,
page, pageSize}` paged shape.

# Cluster evidence

Graph cluster 1 (113 members, cohesion 0.70) groups `ValidationFailedError`,
`get_ownership_tab`, `get_bottleneck_tab`, `get_turnaround_tab` — confirming these four tab
services form one cohesive unit distinct from [Settings](/modules/settings.md) (cluster 22).

# Tables

`contract_lifecycle_stage_history`, `contract_owners`, `contract_turnaround_metrics`,
`turnaround_override_log`, `tenant_bottleneck_thresholds` (migrations 0042-0046).

# Relationships

Reads stage/owner data written by [Contract Lifecycle](/modules/contract-lifecycle.md) actions
(stage transitions, ownership assignment) to compute cycle time and bottleneck flags. The
turnaround-override endpoint writes to `turnaround_override_log`, which feeds
[Settings](/modules/settings.md)'s audit log (`tenant_audit_log`) for traceability.
