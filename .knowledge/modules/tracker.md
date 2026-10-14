---
type: Module
title: tracker
description: Management tracker with four reporting tabs (ownership, cycle-time, bottleneck, turnaround), export, turnaround overrides and tenant bottleneck thresholds.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/tracker_ownership.py
tags: [backend, lifecycle-uc10-uc11, tracker, reporting]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T12:47:46Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ b0c64d78730b6ed271020fb3e7d89002e374f6da
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
* `GET /tracker/exports/{fileId}` -> the file bytes (not a DTO)
* `PUT /tracker/turnaround/{contractId}/estimated-override` -> `TurnaroundRowResponse`
* `GET /tracker/bottleneck-thresholds` (TENANT_ADMIN only) -> `BottleneckThresholdResponse`
* `PUT /tracker/bottleneck-thresholds` (TENANT_ADMIN only) -> `BottleneckThresholdResponse`

# Bottleneck thresholds

Both threshold endpoints take and return a **bare JSON array** of `{stage, thresholdDays}`,
not a paged envelope. `get_bottleneck_thresholds` in
`app/services/tracker_bottleneck_thresholds.py` always emits one row per stage in `STAGE_ORDER`
(`Drafting`, `Negotiation`, `Approval`, `Signature`), falling back to
`tracker_bottleneck.DEFAULT_THRESHOLDS` where the tenant has no `tenant_bottleneck_thresholds`
row.

`update_bottleneck_thresholds` takes `list[UpdateBottleneckThresholdRequest]` and validates the
**whole array before writing anything**, so one bad row leaves the configuration untouched:
an unknown or empty stage fails with `STAGE_MESSAGE`, and `_coerce_days` rejects zero,
negatives, fractions, booleans and non-numbers with `THRESHOLD_DAYS_MESSAGE` (400) rather than
clamping — a clamped threshold would mis-flag every contract in the stage. It then upserts per
stage via `repo.find_threshold` / `repo.insert_threshold`, appends one `tenant_audit_log` row
(`log_entity = "Bottleneck Threshold"`, `log_action = "Updated"`, details listing each
`stage: old -> new`) only when something actually changed, and re-reads through
`get_bottleneck_thresholds` for the response. The Bottleneck tab derives `stuckFlag` from these
rows at request time rather than from a stored flag, so edits take effect on its next call.

# Export

`POST /tracker/export` produces a real file rather than a placeholder URL:

1. `_validate_enums` / `_validate_and_resolve_window` reject a bad `tab`, `format`, `period`
   or date window (`TAB_INVALID_MESSAGE`, `FORMAT_INVALID_MESSAGE`, `PERIOD_REQUIRED_MESSAGE`,
   `PERIOD_INVALID_MESSAGE`, `DATE_FORMAT_MESSAGE`, `DATE_ORDER_MESSAGE`).
2. `_has_any_entitled_contract` returns `success: false` with `NO_CONTRACT_DATA_MESSAGE`
   when the tenant/role sees no contracts at all (UC10-AF-001).
3. `_tab_rows` re-runs the selected tab's own service through `_ParamsShim`, so the export
   matches what the tab shows; zero rows still produce a file carrying `NO_ROWS_PLACEHOLDER`
   (UC10-AF-003). `_TAB_HEADERS` holds the column headers per tab and `_cell` formats values.
4. `export_files.build_file` renders the bytes — see [Export Files](/modules/export-files.md).
5. `_persist_export` writes them under `settings.export_storage_dir`, inserts an
   `uploaded_files` row via [Files](/modules/files.md)' `insert_uploaded_file`, and returns an
   **absolute** `fileUrl`: `{settings.api_base_url}/api/v1/tracker/exports/{fileId}?token=…`.
   The token is a short-lived `app.security.create_file_token` JWT pinned to that path, because
   the frontend opens the URL in a new tab and can attach neither the SPA origin nor the
   `Authorization` header — see [Auth](/modules/auth.md).

Any other failure rolls back and returns `success: false` with `EXPORT_FAILED_MESSAGE`
(UC10-AF-004) instead of a 500. `get_export_file` serves the download by id, 404ing when the
`uploaded_files` row or the file on disk is missing; `_SCOPED_ROLES` and
`_entitled_contract_ids` keep both endpoints tenant- and owner-scoped. `GET
/tracker/exports/{fileId}` authenticates with `file_access_user`/`file_access_tenant_id` rather
than `require_roles`, so its router checks the caller's role against `_EXPORT_ROLES` itself and
raises 403.

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

`app.repositories.tracker_bottleneck.STATUS_TO_STAGE` maps every contract status — including
the unified `Pending Signature` alongside the legacy `Ready For Signature`/`Sent` — onto the
four reporting stages; a status missing from it would drop the contract off the Bottleneck tab.
See [Contract Status](/modules/contract-status.md).

Reads stage/owner data written by [Contract Lifecycle](/modules/contract-lifecycle.md) actions
(stage transitions, ownership assignment) to compute cycle time and bottleneck flags. The
turnaround-override endpoint writes to `turnaround_override_log`, which feeds
[Settings](/modules/settings.md)'s audit log (`tenant_audit_log`) for traceability.
