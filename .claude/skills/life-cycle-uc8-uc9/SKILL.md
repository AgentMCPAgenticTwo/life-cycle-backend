---
name: life-cycle-uc8-uc9
description: Use when building, extending or fixing the 'life cycle uc8 uc9' backend module (life cycle uc8 uc9). Covers the 16 endpoint(s), 16 DTO(s) and 11 table(s) this module owns, plus its acceptance criteria. Do not use for other modules' endpoints.
---

# life cycle uc8 uc9 — implementation skill

This skill is generated from the module contract (`db_contract` / `api_contract`) and this epic's BRD stories. It governs WHAT this specific module contains; `CLAUDE.md` at the repo root still governs HOW to build (stack, layering, dependency and error-handling conventions) and wins on any disagreement about style or structure.

## Endpoints to implement (base path: `/api/v1/contracts`)

Implement exactly these paths, methods and role lists — the frontend calls them literally.

- `GET /api/v1/contracts` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `ContractSearchRequest`; response: `ContractListItemResponse` — Search, filter, sort and paginate contracts visible to the current user
- `GET /api/v1/contracts/{contractId}` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `—`; response: `ContractDetailResponse` — Get contract core metadata (Details tab) for an authorized contract, enforcing direct-link access control
- `GET /api/v1/contracts/{contractId}/document` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `—`; response: `ContractDocumentResponse` — Get document viewer metadata for the Document tab
- `GET /api/v1/contracts/{contractId}/document/download` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `—`; response: `DocumentDownloadResponse` — Download the current document file; returns error for corrupted/missing/oversized files
- `GET /api/v1/contracts/{contractId}/versions` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `—`; response: `ContractVersionResponse` — Get version history list (Versions tab)
- `GET /api/v1/contracts/{contractId}/activity-log` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `—`; response: `ActivityLogEntryResponse` — Get immutable, read-only Activity Log entries for the contract
- `POST /api/v1/contracts/{contractId}/folder-tags` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `AssignFolderTagRequest`; response: `ContractFolderTagResponse` — Assign one or more folders/tags to a contract via the Add Folder/Tag dialog
- `GET /api/v1/folder-tags` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `—`; response: `FolderTagOptionResponse` — List available folders/tags for the Folder/Tag Filter and Add Folder/Tag dialog
- `GET /api/v1/contracts/{contractId}/obligations` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER; request: `—`; response: `ObligationResponse` — List obligations for an Executed contract (Obligations & Renewal screen)
- `POST /api/v1/contracts/{contractId}/obligations` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `CreateObligationRequest`; response: `ObligationResponse` — Manually add an obligation when none were AI-extracted
- `PATCH /api/v1/contracts/{contractId}/obligations/{obligationId}` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `UpdateObligationRequest`; response: `ObligationResponse` — Edit obligation fields (Description, Type, Owner, Due Date, Status), transitioning Source label to Confirmed
- `POST /api/v1/contracts/{contractId}/obligations/{obligationId}/accept` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `—`; response: `ObligationResponse` — Accept an AI-suggested obligation, changing label from AI Suggested to Confirmed
- `GET /api/v1/contracts/{contractId}/renewal` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER; request: `—`; response: `RenewalPanelResponse` — Get renewal panel data (alert banner, end date, notice period, action button states)
- `POST /api/v1/contracts/{contractId}/renew` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `—`; response: `LinkedContractActionResponse` — Create a linked renewal contract and transition original to Renewed
- `POST /api/v1/contracts/{contractId}/amend` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `—`; response: `LinkedContractActionResponse` — Create a linked amendment contract and transition original to Amended
- `POST /api/v1/contracts/{contractId}/terminate` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `TerminateContractRequest`; response: `LinkedContractActionResponse` — Terminate the contract with a required Termination Reason and Effective Termination Date on or after today

Enforce the roles above at the framework's authorization layer **and** with the owner/assignment check in business logic. Missing auth header → 401, disallowed role → 403.


## DTOs — request/response types must match these exactly

- **ContractSearchRequest** (request): `{ searchText?: string, status?: string, startDateFrom?: date, startDateTo?: date, endDateFrom?: date, endDateTo?: date, valueMin?: number, valueMax?: number, folderTagIds?: array, sortBy?: string, sortDirection?: string, page?: integer, pageSize?: integer }`
- **ContractListItemResponse** (response): `{ contractId: uuid, contractName: string, counterparty: string, status: string, value?: number, startDate?: date, endDate?: date, owner: string, lastModified: datetime, folderTags?: array, indexingInProgress: boolean }`
- **ContractDetailResponse** (response): `{ contractId: uuid, contractName: string, counterparty: string, status: string, value?: number, startDate?: date, endDate?: date, owner: string, lastModified: datetime, folderTags?: array, availableTabs: array }`
- **ContractDocumentResponse** (response): `{ contractId: uuid, documentUrl?: string, fileName: string, fileType: string, fileSizeBytes: integer, isOversized: boolean, isCorruptedOrMissing: boolean, downloadEnabled: boolean, unavailableComment?: string }`
- **DocumentDownloadResponse** (response): `{ success: boolean, fileUrl?: string, errorMessage?: string }`
- **ContractVersionResponse** (response): `{ versionId: uuid, versionNumber: integer, createdAt: datetime, createdBy: string, changeSummary?: string }`
- **ActivityLogEntryResponse** (response): `{ entryId: uuid, contractId: uuid, actionType: string, performedBy: string, performedAt: datetime, details?: string }`
- **AssignFolderTagRequest** (request): `{ folderTagIds: array }`
- **ContractFolderTagResponse** (response): `{ contractId: uuid, folderTags: array }`
- **FolderTagOptionResponse** (response): `{ id: uuid, name: string, kind: string }`
- **ObligationResponse** (response): `{ obligationId: uuid, contractId: uuid, obligationDescription: string, obligationType: string, owner?: string, dueDate?: date, status: string, source: string, confirmationLabel: string, evidenceReference?: string, readOnly: boolean }`
- **CreateObligationRequest** (request): `{ obligationDescription: string, obligationType: string, owner: string, dueDate: date, status: string }`
- **UpdateObligationRequest** (request): `{ obligationDescription?: string, obligationType?: string, owner?: string, dueDate?: date, status?: string, evidenceReference?: string }`
- **RenewalPanelResponse** (response): `{ contractId: uuid, renewalAlertBanner?: string, contractEndDate?: date, noticePeriod?: string, alertThresholdDays?: integer, renewEnabled: boolean, amendEnabled: boolean, terminateEnabled: boolean, actionInProgress: boolean, linkedContractId?: uuid, linkedContractRelation?: string, obligations?: array, terminationReason?: string, effectiveTerminationDate?: date }`
- **TerminateContractRequest** (request): `{ terminationReason: string, effectiveTerminationDate: date }`
- **LinkedContractActionResponse** (response): `{ originalContractId: uuid, originalContractStatus: string, linkedContractId: uuid, linkedContractReference: uuid, terminationReason?: string, effectiveTerminationDate?: date, contractEndDate?: date, noticePeriod?: string, renewalAlertBanner?: string, obligations?: array }`

## Tables (models mirror these)

### `contracts` — Core contract record with lifecycle status, value, dates, and ownership
- `id`: UUID (not null)
- `contract_name`: VARCHAR(255) (not null)
- `counterparty`: VARCHAR(255) (not null)
- `status`: VARCHAR(30) (not null)
- `value`: NUMERIC(18,2) (nullable)
- `start_date`: DATE (nullable)
- `end_date`: DATE (nullable)
- `notice_period`: VARCHAR(100) (nullable)
- `owner_id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `document_index_status`: VARCHAR(20) (nullable)
- `linked_contract_id`: UUID (nullable)
- `linked_relation_type`: VARCHAR(20) (nullable)
- `renewal_action_in_progress`: BOOLEAN (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_contracts_tenant_status, idx_contracts_owner

### `contract_assignments` — Maps users to contracts as Legal Reviewer or Approver for visibility/access control
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `user_id`: UUID (not null)
- `role`: VARCHAR(30) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_contract_assignments_user

### `contract_documents` — Stores document file metadata for a contract (current document)
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `file_name`: VARCHAR(255) (not null)
- `file_type`: VARCHAR(10) (not null)
- `file_size_bytes`: BIGINT (not null)
- `storage_path`: VARCHAR(500) (nullable)
- `is_corrupted_or_missing`: BOOLEAN (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_contract_documents_contract

### `contract_versions` — Version history entries for a contract document
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `version_number`: INTEGER (not null)
- `change_summary`: TEXT (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_contract_versions_contract

### `folder_tags` — Tenant-level folder or tag definitions
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `name`: VARCHAR(100) (not null)
- `kind`: VARCHAR(10) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_folder_tags_tenant

### `contract_folder_tags` — Many-to-many mapping of contracts to folders/tags
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `folder_tag_id`: UUID (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_contract_folder_tags_contract, idx_contract_folder_tags_folder_tag

### `activity_log_entries` — Immutable, append-only log of create/edit/approve/reject/sign/tag actions on a contract
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `action_type`: VARCHAR(20) (not null)
- `performed_by`: UUID (not null)
- `performed_at`: TIMESTAMPTZ (not null)
- `details`: TEXT (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
  indexes: idx_activity_log_contract

### `obligations` — Obligation records extracted (AI) or manually added for Executed contracts
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `obligation_description`: TEXT (not null)
- `obligation_type`: VARCHAR(30) (not null)
- `owner_id`: UUID (nullable)
- `due_date`: DATE (nullable)
- `status`: VARCHAR(20) (not null)
- `source`: VARCHAR(20) (not null)
- `confirmation_label`: VARCHAR(20) (not null)
- `evidence_reference`: VARCHAR(500) (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_obligations_contract, idx_obligations_status_due

### `renewal_alerts` — Computed/recorded renewal alert threshold events per contract (90/60/30 day) for End Date and Notice Period
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `threshold_days`: INTEGER (not null)
- `alert_basis`: VARCHAR(20) (not null)
- `triggered_at`: TIMESTAMPTZ (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_renewal_alerts_contract

### `contract_lifecycle_actions` — Records Renew/Amend/Terminate actions, their in-progress state, termination details, and snapshot context (Contract End Date, Notice Period, Renewal Alert Banner) at time of action for audit purposes
- `id`: UUID (not null)
- `original_contract_id`: UUID (not null)
- `linked_contract_id`: UUID (nullable)
- `action_type`: VARCHAR(20) (not null)
- `status`: VARCHAR(20) (not null)
- `termination_reason`: TEXT (nullable)
- `effective_termination_date`: DATE (nullable)
- `contract_end_date_snapshot`: DATE (nullable)
- `notice_period_snapshot`: VARCHAR(100) (nullable)
- `renewal_alert_banner_snapshot`: VARCHAR(255) (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_lifecycle_actions_original

### `obligation_audit_log` — Immutable audit log of accept/edit actions on obligations and renew/amend/terminate contract lifecycle actions
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `obligation_id`: UUID (nullable)
- `action_type`: VARCHAR(30) (not null)
- `field_name`: VARCHAR(100) (nullable)
- `before_value`: TEXT (nullable)
- `after_value`: TEXT (nullable)
- `performed_by`: UUID (not null)
- `performed_at`: TIMESTAMPTZ (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
  indexes: idx_obligation_audit_contract, idx_obligation_audit_obligation

## Migrations

Create these with exactly these names, in this order:

- `CreateContracts`
- `CreateContractAssignments`
- `CreateContractDocuments`
- `CreateContractVersions`
- `CreateFolderTags`
- `CreateContractFolderTags`
- `CreateActivityLogEntries`
- `CreateObligations`
- `CreateRenewalAlerts`
- `CreateContractLifecycleActions`
- `CreateObligationAuditLog`

Never edit or re-order a migration that already exists — add a new one.


## Acceptance criteria to satisfy

### Search, filter, sort and navigate contracts in the repository (`UC8-MF-001`)
- Given I am logged in with an authorized role and navigate to the Contract Repository, When the page loads, Then the Contract List Table displays the contracts I am authorized to see.
- Given I enter a term in the Search Box and click Search, When the search executes, Then the Contract List Table updates to show only contracts matching the term against contract name, counterparty, or clause text.
- Given I click a column header on the Contract List Table, When the sort is applied, Then the rows reorder ascending or descending by that column.
- Given I apply values via the Status Filter, Date Range Filter, Value Filter, and/or Folder/Tag Filter, When I click Search, Then the Contract List Table displays only contracts matching the selected Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter criteria.
- Given I click a contract row in the Contract List Table, When the contract opens, Then I can navigate between the Document, Versions and Activity log tabs for that contract.
- Given I click the Add Folder/Tag button on a contract I am authorized to tag, When the dialog opens and I assign a folder or tag, Then the folder/tag is saved and associated with the contract.

### Display no-results message for non-matching search (`UC8-AF-001`)
- Given I am on the Contract Repository screen with the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter available, When I enter a search term in the Search Box that does not match any contract visible to me and trigger the search, Then the system displays the message 'No contracts found matching your search.' and the Contract List Table shows no rows
- Given I have applied a combination of Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter values along with a Search Box term that together match no contracts, When the search executes, Then the Contract List Table remains empty and the message 'No contracts found matching your search.' is displayed instead of any contract rows
- Given the message 'No contracts found matching your search.' is displayed, When I clear the Search Box and remove all filter values (Status Filter, Date Range Filter, Value Filter, Folder/Tag Filter) and search again, Then the Contract List Table repopulates with contracts matching my access rights and the no-results message is removed

### Display empty-state message when user has no owned or assigned contracts (`UC8-AF-002`)
- Given a Contract Owner, Legal Reviewer, or Approver logs in with no contracts owned by or assigned to them, When they open the Contract Repository, Then the system displays the message "You have no contracts to display." instead of a Contract List Table   [DP-UC8-007].
- Given the empty-state message is displayed, When the screen renders, Then the Search Box   [DP-UC8-001], Status Filter   [DP-UC8-002], Date Range Filter   [DP-UC8-003], Value Filter   [DP-UC8-004], and Folder/Tag Filter   [DP-UC8-005] are still shown but disabled or inactive since there is no data to search or filter.
- Given the user attempts to use the Search Box   [DP-UC8-001], Status Filter   [DP-UC8-002], Date Range Filter   [DP-UC8-003], Value Filter   [DP-UC8-004], or Folder/Tag Filter   [DP-UC8-005] while no contracts exist for them, When no matching contracts can be found, Then the Contract List Table   [DP-UC8-007] remains empty and the "You have no contracts to display." message persists.
- Given a contract later becomes visible to the user because they are made Contract Owner, Legal Reviewer, or Approver on it, When the user reopens or refreshes the Contract Repository, Then the empty-state message is replaced by the Contract List Table   [DP-UC8-007] populated with that contract.

### Block unauthorized direct-link access to a contract (`UC8-AF-003`)
- Given a user is logged in as Contract Owner, Legal Reviewer, or Approver, When they attempt to open a contract via a direct link to a contract they do not own and are not assigned to as Legal Reviewer or Approver, Then the system blocks access and displays the message 'You do not have permission to view this contract.'
- Given access to the contract is blocked, When the user is redirected away from the contract detail view, Then the Contract Repository list screen remains accessible and still displays the Search Box, Status Filter, Date Range Filter, Value Filter, Folder/Tag Filter, and Contract List Table for contracts the user is authorized to view
- Given the blocked contract is not visible to the user, When the user performs a search or applies filters using the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then the Contract List Table never includes the unauthorized contract in the results
- Given the user does not own or is not assigned to the contract, When they attempt the direct link access repeatedly, Then the system consistently denies access and displays the same permission-denied message without exposing any contract data

### Exclude unindexed documents from full text search results (`UC8-AF-004`)
- Given the Contract Repository screen with the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter available, when a user enters free text into the Search Box and triggers a search, then the system matches text against contract name, counterparty, and clause text for contracts whose document index has finished processing.
- Given a contract's document index is still processing at the time a full text search is executed, when the search is run, then that contract is excluded from the text-match results shown in the Contract List Table.
- Given one or more contracts were excluded from text-match results due to in-progress indexing, when the search results are displayed, then the system shows the message 'Some documents are still being indexed and may not appear in search results.'
- Given a search combines the Search Box with the Status Filter, Date Range Filter, Value Filter, and/or Folder/Tag Filter, when a contract with a processing document index would otherwise match the filters, then it is still excluded only from the text-match portion of the results and the indexing message is displayed.
- Given the document index for a previously excluded contract has finished processing, when the user re-runs the same search, then that contract appears in the Contract List Table if it matches the search criteria and the indexing message is no longer shown for it.

### Display error message when downloading a corrupted or missing document (`UC8-AF-005`)
- Given a Contract Owner has used the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter to locate a contract, and the resulting Contract List Table shows the contract with its document file corrupted or missing, When the Contract Owner clicks the Download Button for that contract, Then the system displays the message 'This document could not be retrieved. Please contact your administrator.'
- Given the document file associated with a contract shown in the Contract List Table is missing from storage, When any of Tenant Admin, Contract Owner, Legal Reviewer, or Approver clicks Download on that contract's document, Then the system displays 'This document could not be retrieved. Please contact your administrator.' instead of attempting the download
- Given the document file associated with a contract is corrupted, When the user clicks Download, Then no file is transferred to the user's device and the error message is shown without altering the contract's Status or other fields in the Contract List Table
- Given the error message has been displayed for a corrupted or missing document, When the user navigates away and returns to the repository using the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then the contract still appears in the Contract List Table and the Download Button remains available for retry

### Restrict contract list visibility by role and assignment (`UC8-BR-001`)
- Given a logged-in user is a Contract Owner, Legal Reviewer, or Approver, When they open the Contract Repository, Then the Contract List Table only displays contracts where they are the Contract Owner, or are assigned as Legal Reviewer or Approver on that contract.
- Given a logged-in user is a Tenant Admin, When they open the Contract Repository, Then the Contract List Table displays all contracts in the tenant regardless of ownership or assignment.
- Given a user's visible contract set has been determined by their role and assignments, When they use the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then results are restricted to only the contracts already permitted for that user, filtered further by the applied criteria.
- Given a Legal Reviewer or Approver is not assigned to a given contract and is not its Contract Owner and is not Tenant Admin, When they search or filter via the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then that contract does not appear in the Contract List Table under any combination of filters.
- Given the visibility rule is enforced, When the Contract List Table is rendered, Then no row for a contract outside the user's permitted set is included, even if returned by an underlying unfiltered query.

### Search contract document text content (`UC8-BR-002`)
- Given a contract whose uploaded PDF or DOCX document contains a term not present in any metadata field, When the user enters that term in the Search Box and triggers the search, Then the Contract List Table includes the matching contract in its results.
- Given the repository screen is displayed, When the user reviews the available filtering controls, Then the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter are all present and usable together to refine results.
- Given a search term matches only the extracted document text and not the Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter values, When the search is executed via the Search Box, Then the Contract List Table still returns the contract as a match.
- Given a search term matches both metadata and extracted document text, When the search is executed, Then the Contract List Table returns the contract only once without duplication.
- Given the Search Box is empty, When the Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter are applied alone, Then the Contract List Table filters results based on those criteria without requiring any full text match.

### View Immutable Activity Log of Contract Actions (`UC8-BR-003`)
- Given a contract that has had create, edit, approve, reject, sign and tag actions performed on it, When any authorized user opens the Activity Log Tab for that contract, Then every one of those create, edit, approve, reject, sign and tag actions is listed in the log with no omissions.
- Given the Activity Log Tab is displayed, When a Tenant Admin, Contract Owner, Legal Reviewer or Approver attempts to edit or delete any entry in the log, Then the system prevents the edit or deletion for all of these roles without exception.
- Given a contract with an Activity Log, When the user also uses the Search Box, Status Filter, Date Range Filter, Value Filter, Folder/Tag Filter, or reviews the Contract List Table on the repository screen, Then these controls operate independently of the Activity Log and none of them provide a mechanism to alter or remove Activity Log entries.
- Given a new action is performed on the contract (create, edit, approve, reject, sign or tag), When the action completes, Then a corresponding new entry is automatically appended to the Activity Log and no existing entry is modified.

### Filter contracts by multiple folders and tags (`UC8-BR-004`)
- Given a contract has been assigned to more than one folder and tagged with more than one tag, When I view that contract in the Contract List Table, Then it correctly displays all folders and tags associated with it without restriction to a single value.
- Given I am on the Contract Repository screen with the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter available, When I select two or more values in the Folder/Tag Filter and trigger the search, Then the Contract List Table returns every contract matching any one of the selected folder or tag values, not only contracts matching all of them.
- Given multiple folders/tags are selected in the Folder/Tag Filter along with criteria entered in the Search Box, Status Filter, Date Range Filter, or Value Filter, When the search is executed, Then the Folder/Tag Filter condition is applied as an OR across the selected folder/tag values while still combining with the other active filters.
- Given no folder or tag is selected in the Folder/Tag Filter, When I perform a search using the Search Box, Status Filter, Date Range Filter, or Value Filter alone, Then the Contract List Table returns results without applying any folder/tag restriction.

### Display read-only workflow status in repository (`UC8-BR-005`)
- Given a contract exists whose current workflow state was set by UC5, UC6 or UC7, When the Contract Repository screen renders the Contract List Table, Then the Status column for that contract displays the current workflow state value exactly as set by the originating use case.
- Given a contract is displayed in the Contract List Table, When a user attempts to click or edit the Status value directly from the repository, Then the system prevents any direct edit and the Status remains controlled solely by UC5, UC6 or UC7 transitions.
- Given the repository screen, When a user interacts with the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then these controls only filter the Contract List Table view and do not alter the underlying Status value of any contract.
- Given the Status Filter dropdown is used to filter by a specific workflow state, When the filter is applied, Then only contracts whose Status column matches the selected state from the Contract List Table are displayed, without modifying any contract's stored status.

### Disable Download for Oversized Documents (`UC8-BR-006`)
- Given a contract's document exceeds the system's supported upload size from UC2, When the user searches for it using the Search Box, filters it using the Status Filter, Date Range Filter, Value Filter or Folder/Tag Filter, and locates it in the Contract List Table, Then the Download Button is shown as disabled on that contract's Document tab.
- Given a document exceeds the supported upload size, When the user views the Download button, Then the comment 'File unavailable' is displayed alongside the disabled Download Button.
- Given a document is within the supported upload size, When the user views the Document tab, Then the Download Button is enabled and functions normally.
- Given the Contract List Table is displayed, When a contract with an oversized document is included in the results returned via the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then that contract still appears in the table but its associated Download Button remains disabled with the 'File unavailable' comment when its Document tab is opened.

### View and manage all tenant contracts as Tenant Admin (`UC8-BR-007`)
- Given I am logged in as Tenant Admin, When I open the Contract Repository, Then I see all contracts in the tenant regardless of ownership in the Contract List Table.
- Given I am on the Contract Repository, When I use the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then the results update to reflect contracts matching the applied criteria across all contracts in the tenant, not just ones I own.
- Given I select any contract in the Contract List Table, When I open any tab including Details, Document, Versions, Clauses, Approvals, Signatures, Obligations, or Activity Log, Then I am able to view the tab's contents regardless of whether I own the contract.
- Given I am viewing any contract, When I use the Add Folder/Tag Button, Then I can add or remove folders/tags on that contract even if I am not its owner.
- Given I am viewing the Activity Log Tab on any contract, When I attempt to edit or delete an entry, Then the system prevents the action and the Activity Log remains read-only.

### Restrict Contract Owner visibility and actions to owned contracts (`UC8-BR-008`)
- Given a Contract Owner is logged in, When they open the Contract Repository, Then the Contract List Table displays only contracts for which they are the Contract Owner.
- Given a Contract Owner uses the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter, When they execute a search or apply filters, Then results are restricted to only contracts they own, even if other contracts match the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter criteria.
- Given a Contract Owner attempts to search for a contract they do not own, When the search is executed via the Search Box and other filters, Then that contract does not appear in the Contract List Table.
- Given a Contract Owner opens one of their own contracts, When they navigate between tabs, Then all tabs are accessible.
- Given a Contract Owner opens one of their own contracts, When they use the Add Folder/Tag Button, Then they can add or remove folders/tags on that contract.
- Given a Contract Owner attempts to open or modify folders/tags on a contract they do not own, When they try to access it directly, Then the system prevents viewing details and prevents adding or removing folders/tags.

### Restrict Legal Reviewer repository access to assigned review contracts (`UC8-BR-009`)
- Given I am logged in as a Legal Reviewer, When I open the Contract Repository, Then the Contract List Table displays only contracts on which I am assigned as Legal Reviewer.
- Given I am logged in as a Legal Reviewer, When I use the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter to search or filter contracts, Then only contracts assigned to me for review are returned by any combination of these filters.
- Given a contract is assigned to me for review, When I open it, Then I can open all of its tabs including Details, Document, Versions, Clauses, Approvals, Signatures, Obligations and Activity Log.
- Given a contract is not assigned to me for review, When I search for it via the Search Box or attempt to filter it in via the Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then it does not appear in the Contract List Table.
- Given I am viewing a contract assigned to me for review, When I look for folder/tag management controls, Then the Add Folder/Tag Button is not available or is disabled, preventing me from adding or removing folders/tags.

### Restrict Approver repository access to assigned contracts without folder/tag management (`UC8-BR-010`)
- Given I am logged in as an Approver, When I open the Contract Repository, Then the Contract List Table displays only contracts on which I am assigned as an approver.
- Given I am an Approver, When I use the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then the results returned are restricted to contracts I am assigned to approve, filtered accordingly.
- Given I am an Approver viewing a contract I am assigned to approve, When I open any of its tabs, Then I can access all tabs including Details, Document, Versions, Clauses, Approvals, Signatures, Obligations and Activity Log.
- Given I am an Approver viewing a contract I am assigned to approve, When I look for an option to add or remove folders or tags, Then no Add Folder/Tag control is available to me and I cannot modify folder or tag assignments.
- Given I am an Approver, When I attempt to search for or filter a contract I am not assigned to approve using the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, Then that contract does not appear in the Contract List Table results.

### Display contract lifecycle status without triggering transitions (`UC8-BR-011`)
- Given a contract exists with a lifecycle state of Draft, In Negotiation, In Approval, In Signature, Executed, Expired, or Terminated as set by UC2, UC5, UC6 or UC7, When the contract is displayed in the Contract Repository, Then its current status is shown as read-only and cannot be changed from this screen.
- Given the Contract Repository screen, When a user interacts with the Search Box, Status Filter, Date Range Filter, Value Filter, Folder/Tag Filter, and Contract List Table, Then these controls only search, filter, and display contracts and never initiate or alter any lifecycle state transition.
- Given the Status Filter is used to select a lifecycle state value, When the search is executed, Then the Contract List Table returns only contracts whose current status, as set externally by UC2, UC5, UC6 or UC7, matches the selected value.
- Given a user attempts to modify the Status column value shown in the Contract List Table, When no edit control is available for status, Then the system prevents any direct status change from the Contract Repository screen.

### Search and Filter Contracts Using the Repository Panel (`UC8-FV-001`)
- Given I am on the Contract Repository screen, When I view the Search and Filter panel, Then I see the following controls: Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter.
- Given I enter free text into the Search Box, When I click the Search Button, Then contracts matching the text against contract name, counterparty, or clause text are returned, respecting my role-based visibility.
- Given I select a value in the Status Filter dropdown (Draft, In Negotiation, In Approval, In Signature, Executed, Expired, Terminated), When I click the Search Button, Then only contracts with that status are shown in the Contract List Table.
- Given I set a Date Range Filter using the date picker, When I click the Search Button, Then only contracts whose start or end date falls within the selected range are shown in the Contract List Table.
- Given I set a min and/or max value in the Value Filter, When I click the Search Button, Then only contracts with a contract value within the specified range are shown in the Contract List Table.
- Given I select one or more values in the Folder/Tag Filter, When I click the Search Button, Then contracts matching any of the selected folders or tags are shown in the Contract List Table.
- Given no search text or filters are set, When I click the Search Button, Then all contracts visible to my role are displayed in the Contract List Table with no filtering applied.

### View contract list with search and filter controls (`UC8-FV-002`)
- Given I am logged in as a Tenant Admin, Contract Owner, Legal Reviewer or Approver with access to at least one contract, When I open the Contract Repository screen, Then the Contract List Table is displayed showing Contract Name, Counterparty, Status, Value, Start Date, End Date, Owner, and Last Modified for each visible contract.
- Given the Contract Repository screen is open, When I view the filter controls area, Then the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter are all present and available for use.
- Given I enter free text into the Search Box, When I trigger the search, Then the Contract List Table results are matched against contract name, counterparty, and clause text as applicable.
- Given I select a value in the Status Filter, When the filter is applied, Then the Contract List Table displays only contracts whose current workflow state matches the selected status (Draft, In Negotiation, In Approval, In Signature, Executed, Expired, Terminated).
- Given I set a Date Range Filter, When the filter is applied, Then the Contract List Table displays only contracts whose start or end date falls within the specified range.
- Given I set minimum and/or maximum values in the Value Filter, When the filter is applied, Then the Contract List Table displays only contracts whose contract value falls within the specified range.
- Given I select one or more values in the Folder/Tag Filter, When the filter is applied, Then the Contract List Table displays contracts matching any of the selected folder or tag values.
- Given I have applied no filters, When the Contract Repository screen loads, Then the Contract List Table displays only contracts the logged-in user is permitted to view per their role (BR-1).

### Filter and search contracts using repository list controls (`UC8-FV-003`)
- Given I am on the Contract Repository screen, When the page loads, Then the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter are all displayed above the Contract List Table.
- Given I enter free text in the Search Box, When I trigger a search, Then contracts are matched against contract name, counterparty, and clause text as applicable.
- Given I select a value in the Status Filter, When I trigger a search, Then only contracts matching that status (Draft, In Negotiation, In Approval, In Signature, Executed, Expired, Terminated) are returned in the Contract List Table.
- Given I set a range in the Date Range Filter, When I trigger a search, Then only contracts whose start or end date falls within the selected range are returned in the Contract List Table.
- Given I enter a min and/or max value in the Value Filter, When I trigger a search, Then only contracts whose contract value falls within that range are returned in the Contract List Table.
- Given I select one or more values in the Folder/Tag Filter, When I trigger a search, Then only contracts matching any of the selected folders or tags are returned in the Contract List Table, consistent with BR-4.
- Given no criteria are entered in the Search Box, Status Filter, Date Range Filter, Value Filter, or Folder/Tag Filter, When I view the Contract List Table, Then it displays all contracts visible to me per BR-1 and BR-8.

### Assign Folder or Tag to a Contract via Dialog (`UC8-FV-004`)
- Given a Contract Owner is viewing the Contract List Table and the contract rows are filtered or populated using the Search Box, Status Filter, Date Range Filter, Value Filter, and Folder/Tag Filter, when the Contract Owner selects a contract they own and clicks the Add Folder/Tag Button, then a dialog opens allowing them to assign a folder or tag to that contract.
- Given the Add Folder/Tag dialog is open for a contract the Contract Owner owns, when they select one or more folders or tags and confirm, then the contract is updated to carry those folders/tags and the dialog closes.
- Given a contract has been assigned a folder or tag, when the Contract Owner uses the Folder/Tag Filter on the repository screen, then the Contract List Table returns that contract along with any other contracts matching the selected folder or tag.
- Given the Contract Owner wants to locate a contract before tagging it, when they enter text in the Search Box, set the Status Filter, Date Range Filter, or Value Filter, and click the Search Button, then the Contract List Table updates to show only matching contracts from which the Add Folder/Tag Button can be used.
- Given a contract is owned by another user, when the Contract Owner views the Contract List Table, then that contract is not shown and the Add Folder/Tag Button cannot be invoked on it.

### View contract list with key metadata columns and filters (`UC8-GC-001`)
- Given at least one contract exists in the tenant and is visible to the logged-in user per BR-1, When the user opens the Contract Repository screen, Then the Contract List Table displays the columns Contract Name, Counterparty, Status, Value, Start Date, End Date, Owner, and Last Modified for each visible contract row.
- Given the Contract Repository screen is displayed, When the user inspects the available search and filter controls, Then the screen presents a Search Box, a Status Filter, a Date Range Filter, a Value Filter, and a Folder/Tag Filter.
- Given the user enters free text into the Search Box, When the Search Button is triggered, Then the Contract List Table results are filtered according to the entered text matched against contract name, counterparty, and clause text per BR-2.
- Given the user selects a value in the Status Filter, When the filter is applied, Then only contracts whose Status column matches the selected workflow state (Draft, In Negotiation, In Approval, In Signature, Executed, Expired, Terminated) are displayed in the Contract List Table.
- Given the user sets values in the Date Range Filter, When the filter is applied, Then the Contract List Table displays only contracts whose Start Date or End Date falls within the specified range.
- Given the user sets minimum and/or maximum values in the Value Filter, When the filter is applied, Then the Contract List Table displays only contracts whose Value falls within the specified range.
- Given the user selects one or more values in the Folder/Tag Filter, When the filter is applied, Then the Contract List Table displays contracts matching any of the selected folder or tag values per BR-4.

## Rules

- Do not invent endpoints, routes, DTO fields or table columns beyond what is listed above -- treat this file as the contract for this module.
- Implement every endpoint against the real database via this module's tables/migrations -- no mock/in-memory data (see CLAUDE.md's conventions).
- If a change here would affect another module's existing files, stop and extend shared code instead of rewriting it.
