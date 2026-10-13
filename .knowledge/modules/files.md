---
type: Module
title: files
description: Uploaded-file persistence backing third-party-paper intake and contract document retrieval; service/repository only, no dedicated router.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/files.py
tags: [backend, files, uploads]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
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

# Relationships

Depended on by `contracts_third_party_paper.py` (upload) and `contract_lifecycle.py`
(document/download) routers.
