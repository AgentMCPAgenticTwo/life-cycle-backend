---
type: Module
title: files
description: Uploaded-file persistence backing third-party-paper intake and contract document retrieval; service/repository only, no dedicated router.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/files.py
tags: [backend, files, uploads]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T06:30:03Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 086ad0dd7cfe1a9581dd2f87de143759ef781634
    title: Codebase knowledge graph
status: stable
---

# Files

`app/services/files.py`, `app/repositories/files.py`, `app/schemas/file_upload.py`,
`app/models/uploaded_file.py`.

No `app/routers/files.py` exists — file upload/download is exposed through
[Contracts](/modules/contracts.md)' `POST /contracts/third-party-paper` and
[Contract Lifecycle](/modules/contract-lifecycle.md)'s `GET /contracts/{contractId}/document`
and `.../document/download` endpoints, which call into this service/repository pair.

# Repository

`app/repositories/files.py` holds the two writers/readers the rest of the app shares:

* `insert_uploaded_file` — adds an `UploadedFile` row.
* `get_uploaded_file` — loads one by `(tenant_id, id)`, skipping soft-deleted rows; the
  tenant predicate is what keeps generated files from leaking across tenants.

# Relationships

Depended on by `contracts_third_party_paper.py` (upload) and `contract_lifecycle.py`
(document/download) routers, and by [Tracker](/modules/tracker.md)'s
`app/services/tracker_export.py`, which registers each generated tracker export in
`uploaded_files` so `GET /tracker/exports/{fileId}` can resolve it.
