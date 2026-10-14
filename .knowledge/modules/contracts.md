---
type: Module
title: contracts
description: Contract listing, detail and creation including third-party-paper intake, the base resource most other modules extend.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/contracts.py
tags: [backend, uc123, contracts]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ f6503176d1f18e22902205491eb04e6059b7ca03
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/contracts.py`, `app/routers/contracts_third_party_paper.py`,
`app/services/contracts.py`, `app/repositories/contracts.py`, `app/schemas/contract.py`,
`app/models/contract.py`.

# Endpoints

* `GET /contracts` -> `ContractListResponse` (paged)
* `GET /contracts/{id}` -> `ContractResponse`
* `POST /contracts` -> `ContractResponse` (`CreateContractRequest`)
* `POST /contracts/third-party-paper` -> `FileUploadResponse` (`UploadThirdPartyPaperRequest`)

# Creation also generates Version 1 (UC2-BR-014/015)

`create_contract` calls `app.services.contract_documents.generate_version_one` before
`db.commit()`, so the contract and its Version 1 document are saved in one transaction. Two
additive fields on `ContractResponse` carry the result, both optional so a client that does not
read them is unaffected:

| Field | Meaning |
|---|---|
| `documentVersionNumber` | The version the save produced — always `1` on create. |
| `message` | `contract_documents.CREATED_MESSAGE`, UC2's confirmation text. |

See [Contract Documents](/modules/contract-documents.md) for the merge/third-party-paper split.

# Layering (reference sample for the whole repo)

This resource is the sample used to confirm CLAUDE.md's layering rule holds in practice — see
[Architecture > Layering](/architecture.md#layering) for the verified function list:

* Router (`app/routers/contracts.py`): `list_contracts`, `get_contract`, `create_contract` — 5
  symbols total, each a thin `Depends(require_roles(...))` + service call.
* Service (`app/services/contracts.py`): 15 functions. Validation helpers
  `_validate_template_and_paper_selection`, `_resolve_counterparty`, `_validate_contract_owner`,
  `_validate_dates`, `_validate_notice_period` run before `create_contract` persists anything.
  `_to_list_item`/`_to_response` are the explicit (no-mapper-library) DTO mapping functions.
* Repository (`app/repositories/contracts.py`): 10 pure-query functions — `get_by_id`,
  `list_by_tenant`, `insert_contract`, `get_user`, `get_counterparty`, `insert_counterparty`,
  `get_template`, `get_uploaded_file`, `get_current_task_for_assignee`.

# Relationships

* Read by [Dashboard/Lookups](/modules/dashboard-lookups.md) for dashboard queries.
* Depends on [Contract Documents](/modules/contract-documents.md) for the Version 1 document
  written during `create_contract`.
* Extended by [Contract Lifecycle](/modules/contract-lifecycle.md) (document/versions/
  obligations/renewal) and [Lifecycle Negotiation](/modules/lifecycle-negotiation.md) without
  modifying this module's own files, per CLAUDE.md's "add alongside, don't rewrite" rule.
* `insert_counterparty`/`get_counterparty` overlap with [Counterparties](/modules/counterparties.md)
  — both modules read/write the same `counterparties` table.
