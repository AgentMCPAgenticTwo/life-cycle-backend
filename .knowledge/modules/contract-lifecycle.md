---
type: Module
title: contract-lifecycle
description: Executed-contract detail, document retrieval, version history, activity log, folder tags, obligations, and renewal/amendment/termination actions.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/contract_lifecycle.py
tags: [backend, life-cycle-uc8-uc9, contract-lifecycle, obligations]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T12:47:46Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ b0c64d78730b6ed271020fb3e7d89002e374f6da
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/contract_lifecycle.py` (registers `router`, prefix `/contracts`, and
`folder_tags_router`, prefix `/folder-tags`), `app/services/contract_lifecycle.py`,
`app/repositories/contract_lifecycle.py`, `app/schemas/contract_lifecycle.py`,
`app/models/contract_lifecycle.py`.

# Endpoints

* `GET /contracts`, `GET /contracts/{contractId}` (detail), `GET .../document`,
  `GET .../document/download`, `GET .../document/file` (raw bytes),
  `GET .../versions`, `GET .../activity-log`
* `POST .../folder-tags`, `GET /folder-tags`
* `GET/POST .../obligations`, `PATCH .../obligations/{obligationId}`,
  `POST .../obligations/{obligationId}/accept`
* `GET .../renewal`, `POST .../renew`, `POST .../amend`, `POST .../terminate`

# Document download is two endpoints

`download_document` (`GET .../document/download`) returns JSON: a
`DocumentDownloadResponse` whose `fileUrl` is now an **absolute** URL on this API —
`{settings.api_base_url}/api/v1/contracts/{id}/document/file?token=…` — because the browser
follows it directly and a relative path would resolve against the SPA origin. The token is a
short-lived `app.security.create_file_token` JWT pinned to that exact path; see
[Auth](/modules/auth.md). When the `contract_documents` row exists but no bytes were ever
written (`contract_documents.read_document_bytes` returns `None`) it returns
`success: false` with the same retrieval-error message as AF-005, instead of a URL that 404s.

`get_document_file` (`GET .../document/file`) serves the bytes themselves: `Response` with the
file's content type (`contract_documents.CONTENT_TYPES`, else `application/octet-stream`) and a
`Content-Disposition` attachment header. It authenticates with `app.auth.file_access_user` /
`file_access_tenant_id` (bearer token or the signed `token`) and then re-checks the role against
`_ALL_ROLES` in the router, because a `Depends(require_roles(...))` cannot see a file-token
caller. Missing, corrupted, oversized (`OVERSIZED_FILE_BYTES`) or byte-less documents are 404.

# Who may view a contract

`_assert_viewable` accepts a `LEGAL_REVIEWER`/`APPROVER` who has a `contract_assignments` row
(`repo.get_assignment`) **or** who is linked through the workflow —
`app.repositories.contracts.is_workflow_participant`, see [Contracts](/modules/contracts.md).
Without it, a reviewer or approver who had acted on the contract could not open the documents
they had just worked on.

# Hotspots

`app.services.contract_lifecycle._get_contract_or_404` — fan-in 13, the single most-reused
helper outside `app/auth.py`. `app.services.contract_lifecycle._user_uuid` — fan-in 9.

# Write helpers used by other modules

`app/repositories/contract_lifecycle.py` exposes `insert_document` and
`insert_contract_version` (add + flush, no commit) alongside its read queries. They are the
only writers of `contract_documents`/`contract_versions` outside this module's own services,
and exist so [Contract Documents](/modules/contract-documents.md) can create a contract's
Version 1 inside the caller's transaction without duplicating this module's models.

# Relationships

Operates on contracts created via [Contracts](/modules/contracts.md); delegates document
storage to [Files](/modules/files.md); `renew`/`amend` actions create linked contracts that
re-enter the same lifecycle. Stage transitions recorded here are the source of the
`contract_lifecycle_stage_history` and `contract_owners` tables that
[Tracker](/modules/tracker.md) reports on.
