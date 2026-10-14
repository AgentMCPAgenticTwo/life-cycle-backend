---
type: Module
title: contract-documents
description: UC2 Version 1 document generation — merges a template body or adopts the uploaded third-party paper when a contract is saved; service only, no router.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/contract_documents.py
tags: [backend, uc123, contracts, documents]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T12:47:46Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ b0c64d78730b6ed271020fb3e7d89002e374f6da
    title: Codebase knowledge graph
status: stable
---

# Files

`app/services/contract_documents.py` only — there is no router, schema or model of its own; it
writes `ContractDocument` and `ContractVersion` from `app/models/contract_lifecycle.py` through
[Contract Lifecycle](/modules/contract-lifecycle.md)'s repository.

# Symbols

| Symbol | Role |
|---|---|
| `CREATED_MESSAGE` | The UC2 confirmation text returned in `ContractResponse.message`. |
| `_MERGE_FIELD_RE` | Matches `{{mergeField}}` placeholders in a template body. |
| `_merge_values` | Builds the merge dictionary from the contract, its counterparty and its owner. |
| `merge_template_body` | Substitutes every known placeholder; an unmapped one is left visible rather than blanked. |
| `generate_version_one` | Creates the `contract_documents` + `contract_versions` rows, writes the file, and returns the version number (always `1`). |
| `render_document_bytes` | The merged body as real bytes — a `PDF` template goes through [Export Files](/modules/export-files.md)' `build_pdf`, anything else is UTF-8 text, since no document library may be added. |
| `CONTENT_TYPES` | `PDF`/`DOCX` -> media type, used by the document-file endpoint. |
| `document_file_path` | Resolves a `contract_documents.storage_path` (`/documents/<id>/v1.<ext>`) under `settings.document_storage_dir`. |
| `write_document_bytes` / `read_document_bytes` | Write the file (creating the directory) and return its length; read it back, or `None` when nothing was stored. |
| `_read_upload` | Reads the third-party-paper bytes kept by [Files](/modules/files.md)' `upload_file_path`. |

# Behaviour

* **Template path** — `contracts_repo.get_template` supplies `template_body`, merged by
  `merge_template_body`; the file type comes from the template's `document_format`.
* **Third-party-paper path** — `contracts_repo.get_uploaded_file` supplies name/format/size and
  the file is adopted as-is, with no merge.
* Both paths write a deterministic `storage_path` of `/documents/{contract.id}/v1.<ext>` **and
  the bytes behind it**, under `settings.document_storage_dir` — a row with no file behind it is
  what made the document download fail. `file_size_bytes` is the written length; when the source
  bytes are unavailable (an upload recorded before they were kept) only the metadata is written
  with the previously recorded size, and the download reports the retrieval error.
* `generate_version_one` flushes but never commits — the caller owns the transaction, so the
  contract and its Version 1 are saved together.

# Relationships

* Called by `app.services.contracts.create_contract` — see [Contracts](/modules/contracts.md).
* The rows it writes are served by [Contract Lifecycle](/modules/contract-lifecycle.md)'s
  `GET .../document` and `GET .../versions`, via its new `insert_document` and
  `insert_contract_version` repository functions; the bytes are served by that module's
  `GET .../document/file`, which reads them back through `read_document_bytes`.
* Reads uploaded files persisted by [Files](/modules/files.md) and templates owned by
  [Templates / Clauses](/modules/templates-clauses.md).
* Covered by `tests/test_contract_documents.py` — see [Tests](/modules/tests.md).
