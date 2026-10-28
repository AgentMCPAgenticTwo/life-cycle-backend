---
type: Module
title: contracts
description: Contract listing, detail and creation including third-party-paper intake, the base resource most other modules extend.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/contracts.py
tags: [backend, uc123, contracts]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T05:40:14Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-28T06:00:32Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 1662028280ad8faf6e454761554a23922060e1bd
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

# ContractResponse also feeds the Contract Detail page

`GET /contracts/{id}` is the one detail endpoint both uc123 and life-cycle-uc8-uc9 read, so
`_to_response` fills four further additive fields for the Detail page's Details tab. All are
optional, so uc123 consumers are unaffected:

| Field | Source in `_to_response` |
|---|---|
| `contractId` | `contract.id` — the same UUID as `id`; the Details tab renders a Contract ID row. |
| `lastModified` | `contract.updated_at`, duplicated from `updatedAt` under the page's own name. |
| `folderTags` | `_folder_tags` -> `app.repositories.contract_lifecycle.list_contract_folder_tags`, mapped to `FolderTagOptionResponse`. |
| `availableTabs` | `_available_tabs(contract.status)`. |

`_available_tabs` starts from `_BASE_TABS` (`Details`, `Document`, `Versions`, `Clauses`,
`Activity Log`) and splices `Approvals`/`Signatures`/`Obligations` in *before* `Activity Log`
rather than appending, because the frontend renders the list in order and matches each label
character-for-character. Which extras appear is keyed off the contract status through
`_APPROVAL_STATUSES`, `_SIGNATURE_STATUSES` and `_OBLIGATION_STATUSES` — a Draft contract gets
the five base tabs only. The status vocabulary is [Contract Status](/modules/contract-status.md)'s;
the sets also carry the legacy spellings (`SignatureDeclined` beside `Signature Declined`).

This is the one place `app/services/contracts.py` imports from the lifecycle module
(`app.repositories.contract_lifecycle`, `app.schemas.contract_lifecycle`) — see
[Contract Lifecycle](/modules/contract-lifecycle.md), which owns the folder-tag tables and the
tabs' own endpoints. Covered by `test_contract_detail_carries_detail_page_fields` in
`tests/test_contracts.py`.

# Layering (reference sample for the whole repo)

This resource is the sample used to confirm CLAUDE.md's layering rule holds in practice — see
[Architecture > Layering](/architecture.md#layering) for the verified function list:

* Router (`app/routers/contracts.py`): `list_contracts`, `get_contract`, `create_contract` — 5
  symbols total, each a thin `Depends(require_roles(...))` + service call.
* Service (`app/services/contracts.py`): 17 functions (the Detail-page helpers `_available_tabs`
  and `_folder_tags` are the two most recent). Validation helpers
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
