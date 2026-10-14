---
type: Module
title: contracts
description: Contract listing, detail and creation including third-party-paper intake, the base resource most other modules extend.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/contracts.py
tags: [backend, uc123, contracts]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T12:47:46Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ b0c64d78730b6ed271020fb3e7d89002e374f6da
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
* Repository (`app/repositories/contracts.py`): pure-query functions — `get_by_id`,
  `list_by_tenant`, `insert_contract`, `get_user`, `get_counterparty`, `insert_counterparty`,
  `get_template`, `get_uploaded_file`, `get_current_task_for_assignee`,
  `is_workflow_participant`.

# Workflow participants may open their contracts

`_has_permitted_access` first looks for a `contract_tasks` row assigning the caller this
contract's pending step. Failing that, a `LEGAL_REVIEWER`/`APPROVER` is still permitted when
`is_workflow_participant` finds them on the contract's negotiation routing
(`negotiation_reviewers`) or on one of its approval steps / delegations
(`approval_step_instances`, `approval_delegations`) — otherwise a reviewer lost access to a
contract the moment their step advanced. The same query backs
[Contract Lifecycle](/modules/contract-lifecycle.md)'s `_assert_viewable`.

# Relationships

* Read by [Dashboard/Lookups](/modules/dashboard-lookups.md) for dashboard queries.
* Depends on [Contract Documents](/modules/contract-documents.md) for the Version 1 document
  written during `create_contract`.
* Extended by [Contract Lifecycle](/modules/contract-lifecycle.md) (document/versions/
  obligations/renewal) and [Lifecycle Negotiation](/modules/lifecycle-negotiation.md) without
  modifying this module's own files, per CLAUDE.md's "add alongside, don't rewrite" rule.
* `insert_counterparty`/`get_counterparty` overlap with [Counterparties](/modules/counterparties.md)
  — both modules read/write the same `counterparties` table.
