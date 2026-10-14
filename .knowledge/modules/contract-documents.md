---
type: Module
title: contract-documents
description: UC2 Version 1 document generation — merges a template body or adopts the uploaded third-party paper when a contract is saved; service only, no router.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/contract_documents.py
tags: [backend, uc123, contracts, documents]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ f6503176d1f18e22902205491eb04e6059b7ca03
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
| `generate_version_one` | Creates the `contract_documents` + `contract_versions` rows and returns the version number (always `1`). |

# Behaviour

* **Template path** — `contracts_repo.get_template` supplies `template_body`, merged by
  `merge_template_body`; the file type comes from the template's `document_format`.
* **Third-party-paper path** — `contracts_repo.get_uploaded_file` supplies name/format/size and
  the file is adopted as-is, with no merge.
* Both paths write a deterministic `storage_path` of `/documents/{contract.id}/v1.<ext>`; no
  blob store exists in this sandbox, so the rendered body itself is not persisted.
* `generate_version_one` flushes but never commits — the caller owns the transaction, so the
  contract and its Version 1 are saved together.

# Relationships

* Called by `app.services.contracts.create_contract` — see [Contracts](/modules/contracts.md).
* The rows it writes are served by [Contract Lifecycle](/modules/contract-lifecycle.md)'s
  `GET .../document` and `GET .../versions`, via its new `insert_document` and
  `insert_contract_version` repository functions.
* Reads uploaded files persisted by [Files](/modules/files.md) and templates owned by
  [Templates / Clauses](/modules/templates-clauses.md).
* Covered by `tests/test_contract_documents.py` — see [Tests](/modules/tests.md).
