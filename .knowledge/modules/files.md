---
type: Module
title: files
description: Uploaded-file persistence backing third-party-paper intake and contract document retrieval; service/repository only, no dedicated router.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/files.py
tags: [backend, files, uploads]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T12:47:46Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ b0c64d78730b6ed271020fb3e7d89002e374f6da
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

# Uploaded bytes are kept on disk

`upload_third_party_paper` decodes the base64 payload and writes it to `upload_file_path(file_id,
file_format)` — `{settings.document_storage_dir}/uploads/{file_id}.{ext}` — before inserting the
`uploaded_files` row. Without the bytes, a contract created from third-party paper had a document
row with nothing behind it and the download failed;
[Contract Documents](/modules/contract-documents.md)' `_read_upload` reads them back when it
generates Version 1.

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
