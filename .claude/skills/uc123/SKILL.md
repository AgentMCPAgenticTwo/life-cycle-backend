---
name: uc123
description: Use when building, extending or fixing the 'uc123' backend module (uc123). Covers the 23 endpoint(s), 31 DTO(s) and 10 table(s) this module owns, plus its acceptance criteria. Do not use for other modules' endpoints.
---

# uc123 — implementation skill

This skill is generated from the module contract (`db_contract` / `api_contract`) and this epic's BRD stories. It governs WHAT this specific module contains; `CLAUDE.md` at the repo root still governs HOW to build (stack, layering, dependency and error-handling conventions) and wins on any disagreement about style or structure.

## Endpoints to implement (base path: `/api/v1`)

Implement exactly these paths, methods and role lists — the frontend calls them literally.

- `GET /api/v1/dashboard/summary` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER, SIGNER; request: `—`; response: `DashboardSummaryResponse` — Returns tenant-scoped status card counts (Total, Draft, Negotiation, Pending Approval, Pending Signature, Executed, Expiring 30/60/90) for the applied filters
- `GET /api/v1/dashboard/my-tasks` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER, SIGNER; request: `—`; response: `MyTasksResponse` — Returns contracts awaiting the logged-in user's review, approval or signature for the current pending step
- `GET /api/v1/dashboard/high-risk-contracts` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `—`; response: `HighRiskContractsResponse` — Returns contracts whose AI risk score exceeds the tenant-configured threshold, ordered by risk score descending, scoped by role
- `GET /api/v1/dashboard/filters` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER, SIGNER; request: `—`; response: `DashboardFilterOptionsResponse` — Returns tenant-scoped options for Contract Type, Department, Counterparty and Owner filters
- `GET /api/v1/contracts` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER, SIGNER; request: `—`; response: `ContractListResponse` — Returns the Contract Repository list, filterable by status, Contract Type, Department, Counterparty, Owner and Date Range, enforcing tenant and role-based access
- `GET /api/v1/contracts/{id}` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER, SIGNER; request: `—`; response: `ContractResponse` — Returns full contract detail if the logged-in user's role has permitted actions on it, otherwise denies access
- `GET /api/v1/templates` — roles: TENANT_ADMIN, LEGAL_REVIEWER, CONTRACT_OWNER; request: `—`; response: `TemplateListResponse` — Returns templates filtered by Contract Type, Industry and/or Status; used both by Template Library listing and New Contract template selection
- `GET /api/v1/counterparties` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `—`; response: `CounterpartySearchResponse` — Searches existing counterparties by name, company or GST/Tax ID
- `POST /api/v1/counterparties` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `CreateCounterpartyRequest`; response: `CounterpartyResponse` — Creates a new counterparty, blocking duplicates on GST/Tax ID
- `GET /api/v1/users` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `—`; response: `UserOptionListResponse` — Returns tenant users filtered by role, used to populate Contract Owner dropdown
- `POST /api/v1/contracts/third-party-paper` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `UploadThirdPartyPaperRequest`; response: `FileUploadResponse` — Uploads a third party paper file (PDF/DOCX, max 25MB) as an alternative to Template selection
- `POST /api/v1/contracts` — roles: TENANT_ADMIN, CONTRACT_OWNER; request: `CreateContractRequest`; response: `ContractResponse` — Creates a new contract from a Template or uploaded third party paper, validates all mandatory and conditional fields, auto-fills merge fields, and saves as Draft
- `POST /api/v1/templates` — roles: TENANT_ADMIN, LEGAL_REVIEWER; request: `CreateTemplateRequest`; response: `TemplateResponse` — Creates a new template as Version 1; transitions to Active once mandatory fields are complete
- `PUT /api/v1/templates/{id}` — roles: TENANT_ADMIN, LEGAL_REVIEWER; request: `UpdateTemplateRequest`; response: `TemplateResponse` — Edits an existing template, creating a new version entry recording editor and timestamp; blocks concurrent conflicting saves
- `POST /api/v1/templates/{id}/deactivate` — roles: TENANT_ADMIN; request: `—`; response: `TemplateResponse` — Deactivates a template; blocked if attached to any active, unsigned contract
- `POST /api/v1/templates/{id}/reactivate` — roles: TENANT_ADMIN; request: `—`; response: `TemplateResponse` — Reactivates an Inactive template with no restrictions
- `GET /api/v1/templates/{id}/versions` — roles: TENANT_ADMIN, LEGAL_REVIEWER; request: `—`; response: `VersionHistoryResponse` — Returns the version history of a template including version number, editor and change summary
- `GET /api/v1/clauses` — roles: TENANT_ADMIN, LEGAL_REVIEWER, CONTRACT_OWNER; request: `—`; response: `ClauseListResponse` — Returns clause library entries, colour-coded by Risk Level
- `POST /api/v1/clauses` — roles: TENANT_ADMIN, LEGAL_REVIEWER; request: `CreateClauseRequest`; response: `ClauseResponse` — Creates a new clause as Version 1; transitions to Active once mandatory fields are complete
- `PUT /api/v1/clauses/{id}` — roles: TENANT_ADMIN, LEGAL_REVIEWER; request: `UpdateClauseRequest`; response: `ClauseResponse` — Edits an existing clause, creating a new version entry; blocks removal of Mandatory clauses from contracts and blocks concurrent conflicting saves
- `POST /api/v1/clauses/{id}/deactivate` — roles: TENANT_ADMIN; request: `—`; response: `ClauseResponse` — Deactivates a clause
- `POST /api/v1/clauses/{id}/reactivate` — roles: TENANT_ADMIN; request: `—`; response: `ClauseResponse` — Reactivates an Inactive clause with no restrictions
- `GET /api/v1/clauses/{id}/versions` — roles: TENANT_ADMIN, LEGAL_REVIEWER; request: `—`; response: `VersionHistoryResponse` — Returns the version history of a clause including version number, editor and change summary

Enforce the roles above at the framework's authorization layer **and** with the owner/assignment check in business logic. Missing auth header → 401, disallowed role → 403.


## DTOs — request/response types must match these exactly

- **DashboardSummaryResponse** (response): `{ totalContractsCount: integer, inDraftCount: integer, inNegotiationCount: integer, pendingApprovalCount: integer, pendingSignatureCount: integer, executedCount: integer, expiring30DaysCount: integer, expiring60DaysCount: integer, expiring90DaysCount: integer, noContractsMessage?: string, noMatchMessage?: string }`
- **MyTaskItemResponse** (response): `{ contractId: uuid, contractName: string, counterparty: string, status: string, dueDate: date }`
- **MyTasksResponse** (response): `{ items: array, emptyMessage?: string }`
- **HighRiskContractResponse** (response): `{ contractId: uuid, contractName: string, counterparty: string, riskScore: integer }`
- **HighRiskContractsResponse** (response): `{ items: array, emptyMessage?: string }`
- **CounterpartyOptionResponse** (response): `{ id: uuid, name: string }`
- **OwnerOptionResponse** (response): `{ id: uuid, name: string }`
- **DashboardFilterOptionsResponse** (response): `{ contractTypes: array, departments: array, counterparties: array, owners: array }`
- **ContractListItemResponse** (response): `{ id: uuid, contractName: string, contractType: string, department?: string, counterpartyName: string, contractOwnerName: string, status: string, startDate: date, endDate: date, contractValue: number, currency: string, riskScore?: integer }`
- **ContractListResponse** (response): `{ items: array, page: integer, pageSize: integer, totalCount: integer, noMatchMessage?: string }`
- **ContractResponse** (response): `{ id: uuid, contractName: string, contractType: string, industry: string, department?: string, templateId?: uuid, thirdPartyPaperFileId?: uuid, counterpartyId: uuid, counterpartyName: string, counterpartyEmail: string, counterpartyCompany: string, counterpartyAddress?: string, counterpartyGstTaxId?: string, contractOwnerId: uuid, contractOwnerName: string, contractValue: number, currency: string, startDate: date, endDate: date, renewalType: string, noticePeriod?: integer, assignedDate: date, dueDate: date, status: string, riskScore?: integer, createdAt: datetime, updatedAt: datetime }`
- **CreateContractRequest** (request): `{ contractType: string, industry: string, templateId?: uuid, thirdPartyPaperFileId?: uuid, counterpartySearch?: string, counterpartyId?: uuid, counterpartyName?: string, counterpartyEmail?: string, counterpartyCompany?: string, counterpartyAddress?: string, counterpartyGstTaxId?: string, contractOwnerId: uuid, contractValue: number, currency: string, startDate: date, endDate: date, renewalType: string, noticePeriod?: integer, dueDate: date }`
- **UploadThirdPartyPaperRequest** (request): `{ fileName: string, fileContentBase64: string, fileSize: integer, fileFormat: string }`
- **FileUploadResponse** (response): `{ fileId: uuid, fileName: string, fileSize: integer, fileFormat: string, storageUrl: string }`
- **CounterpartyResponse** (response): `{ id: uuid, name: string, email: string, company: string, address?: string, gstTaxId?: string }`
- **CounterpartySearchResponse** (response): `{ items: array, duplicateWarning?: string }`
- **CreateCounterpartyRequest** (request): `{ name: string, email: string, company: string, address?: string, gstTaxId?: string }`
- **UserOptionResponse** (response): `{ id: uuid, name: string, email: string, role: string }`
- **UserOptionListResponse** (response): `{ items: array }`
- **TemplateResponse** (response): `{ id: uuid, templateName: string, templateCategory: string, documentFormat: string, templateBody: string, status: string, lastModifiedBy: string, lastModifiedDate: datetime }`
- **TemplateListResponse** (response): `{ items: array }`
- **CreateTemplateRequest** (request): `{ templateName: string, templateCategory: string, documentFormat: string, templateBody: string }`
- **UpdateTemplateRequest** (request): `{ templateName: string, templateCategory: string, documentFormat: string, templateBody: string }`
- **ClauseResponse** (response): `{ id: uuid, clauseName: string, clauseCategory: string, standardText: string, fallbackText1?: string, fallbackText2?: string, riskLevel: string, mandatory: boolean, status: string, lastModifiedBy: string, lastModifiedDate: datetime }`
- **ClauseListResponse** (response): `{ items: array }`
- **CreateClauseRequest** (request): `{ clauseName: string, clauseCategory: string, standardText: string, fallbackText1?: string, fallbackText2?: string, riskLevel: string, mandatory: boolean }`
- **UpdateClauseRequest** (request): `{ clauseName: string, clauseCategory: string, standardText: string, fallbackText1?: string, fallbackText2?: string, riskLevel: string, mandatory: boolean }`
- **VersionHistoryItemResponse** (response): `{ versionNumber: integer, changedBy: string, dateChanged: datetime, changeSummary?: string }`
- **VersionHistoryResponse** (response): `{ items: array }`
- **ErrorResponse** (response): `{ code: string, message: string, fieldErrors?: array }`
- **FieldErrorResponse** (response): `{ field: string, message: string }`

## Tables (models mirror these)

### `tenants` — Stores tenant accounts and tenant-level configuration such as the high risk threshold
- `id`: UUID (not null)
- `name`: VARCHAR(255) (not null)
- `high_risk_threshold`: INTEGER (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)

### `users` — Stores tenant users and their assigned role used for Contract Owner, Legal Reviewer, Approver and Signer scoping
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `name`: VARCHAR(255) (not null)
- `email`: VARCHAR(255) (not null)
- `role`: VARCHAR(50) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_users_tenant_role

### `counterparties` — Stores counterparty records for contracts, scoped per tenant
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `name`: VARCHAR(255) (not null)
- `email`: VARCHAR(255) (not null)
- `company`: VARCHAR(255) (not null)
- `address`: TEXT (nullable)
- `gst_tax_id`: VARCHAR(100) (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_counterparties_tenant_gst

### `uploaded_files` — Stores metadata for uploaded third party paper files and other binary attachments
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `file_name`: VARCHAR(255) (not null)
- `file_size`: INTEGER (not null)
- `file_format`: VARCHAR(10) (not null)
- `storage_url`: TEXT (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)

### `templates` — Stores current state of templates used for contract generation
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `template_name`: VARCHAR(150) (not null)
- `template_category`: VARCHAR(100) (not null)
- `document_format`: VARCHAR(10) (not null)
- `template_body`: TEXT (not null)
- `status`: VARCHAR(20) (not null)
- `current_version`: INTEGER (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_templates_tenant_type_industry_status

### `template_versions` — Stores immutable snapshots of each saved template version with editor and timestamp
- `id`: UUID (not null)
- `template_id`: UUID (not null)
- `version_number`: INTEGER (not null)
- `changed_by`: UUID (not null)
- `date_changed`: TIMESTAMPTZ (not null)
- `change_summary`: TEXT (nullable)
- `template_name`: VARCHAR(150) (not null)
- `template_category`: VARCHAR(100) (not null)
- `document_format`: VARCHAR(10) (not null)
- `template_body`: TEXT (not null)
- `status`: VARCHAR(20) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_template_versions_template

### `clauses` — Stores current state of clauses used within templates and contracts
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `clause_name`: VARCHAR(150) (not null)
- `clause_category`: VARCHAR(100) (not null)
- `standard_text`: TEXT (not null)
- `fallback_text_1`: TEXT (nullable)
- `fallback_text_2`: TEXT (nullable)
- `risk_level`: VARCHAR(10) (not null)
- `mandatory`: BOOLEAN (not null)
- `status`: VARCHAR(20) (not null)
- `current_version`: INTEGER (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_clauses_tenant_status

### `clause_versions` — Stores immutable snapshots of each saved clause version with editor and timestamp
- `id`: UUID (not null)
- `clause_id`: UUID (not null)
- `version_number`: INTEGER (not null)
- `changed_by`: UUID (not null)
- `date_changed`: TIMESTAMPTZ (not null)
- `change_summary`: TEXT (nullable)
- `clause_name`: VARCHAR(150) (not null)
- `clause_category`: VARCHAR(100) (not null)
- `standard_text`: TEXT (not null)
- `fallback_text_1`: TEXT (nullable)
- `fallback_text_2`: TEXT (nullable)
- `risk_level`: VARCHAR(10) (not null)
- `mandatory`: BOOLEAN (not null)
- `status`: VARCHAR(20) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_clause_versions_clause

### `contracts` — Stores core contract records including type, counterparty, owner, financial, scheduling and status data
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `contract_name`: VARCHAR(255) (not null)
- `contract_type`: VARCHAR(50) (not null)
- `industry`: VARCHAR(20) (not null)
- `department`: VARCHAR(100) (nullable)
- `template_id`: UUID (nullable)
- `third_party_paper_file_id`: UUID (nullable)
- `counterparty_id`: UUID (not null)
- `contract_owner_id`: UUID (not null)
- `contract_value`: NUMERIC(18,2) (not null)
- `currency`: VARCHAR(10) (not null)
- `start_date`: DATE (not null)
- `end_date`: DATE (not null)
- `renewal_type`: VARCHAR(10) (not null)
- `notice_period`: INTEGER (nullable)
- `assigned_date`: DATE (not null)
- `due_date`: DATE (not null)
- `status`: VARCHAR(30) (not null)
- `risk_score`: INTEGER (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_contracts_tenant_status, idx_contracts_tenant_enddate, idx_contracts_tenant_owner

### `contract_tasks` — Tracks the current pending assignment (reviewer, approver, or signer) per contract used to populate My Tasks panel
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `assignee_user_id`: UUID (not null)
- `assignment_role`: VARCHAR(20) (not null)
- `due_date`: DATE (not null)
- `is_current`: BOOLEAN (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_contract_tasks_assignee_current

## Migrations

Create these with exactly these names, in this order:

- `CreateTenants`
- `CreateUsers`
- `CreateCounterparties`
- `CreateUploadedFiles`
- `CreateTemplates`
- `CreateTemplateVersions`
- `CreateClauses`
- `CreateClauseVersions`
- `CreateContracts`
- `CreateContractTasks`

Never edit or re-order a migration that already exists — add a new one.


## Acceptance criteria to satisfy

### View and Filter Dashboard Status Cards and Task Panels (`UC1-MF-001`)
- Given I am logged in with a valid tenant account and at least one contract exists in the tenant, When I land on the Dashboard, Then I see the following status cards each showing a count: Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card.
- Given contracts exist with end dates falling within multiple expiry windows, When the Dashboard loads, Then a contract expiring in 20 days is counted in the Expiring in 30 Days Card, the Expiring in 60 Days Card, and the Expiring in 90 Days Card.
- Given I am viewing the Dashboard, When I view the My Tasks panel, Then it lists contracts awaiting my review, approval or signature showing Contract Name, Counterparty, Status and Due Date.
- Given AI clause analysis (UC4) has run on at least one contract, When I view the High Risk Contracts panel, Then it lists AI-flagged contracts with Contract Name, Counterparty and Risk Score ordered by highest risk score first.
- Given I am on the Dashboard, When I select values in the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter and Date Range Filter and click Apply, Then all status cards, the My Tasks panel and the High Risk Contracts panel refresh to reflect only matching contracts.
- Given I have applied filters, When I click a status card such as the Pending Approval Card, Then the Contract Repository list opens pre-filtered to that status plus any currently active Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter and Date Range Filter values.
- Given I am viewing My Tasks or High Risk Contracts, When I click a row in either panel, Then that contract's detail screen opens.
- Given data is scoped per tenant, When any card, panel or filter is displayed or applied, Then only data belonging to my logged-in tenant is shown, never data from other tenants.

### Display empty-state dashboard when no contracts exist (`UC1-AF-001`)
- Given no contracts exist yet for the tenant, When the dashboard loads, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card all display a count of 0.
- Given no contracts exist yet for the tenant, When the dashboard loads, Then the message 'No contracts yet. Click New Contract to get started.' is shown.
- Given no contracts exist yet for the tenant, When the user views the filter options, Then the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter are still displayed and available for interaction even though no data exists to filter.
- Given no contracts exist yet for the tenant, When the user views the dashboard, Then the New Contract Button is visible and enabled to allow the user to click it to get started.
- Given no contracts exist yet for the tenant, When the dashboard loads, Then the My Tasks Panel and High Risk Contracts Panel display as empty consistent with zero contracts existing.

### Display empty state in My Tasks panel when no tasks are assigned (`UC1-AF-002`)
- Given a logged-in Legal Reviewer with no contracts awaiting their review, approval or signature, when the dashboard loads, then the My Tasks Panel displays the message 'You have no pending tasks' instead of a list.
- Given the My Tasks Panel is showing 'You have no pending tasks', when the dashboard is viewed, then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card and Expiring in 90 Days Card continue to display their counts independently of the empty My Tasks state.
- Given the My Tasks Panel is empty, when the user applies the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter or Date Range Filter, then the dashboard recalculates and the My Tasks Panel either continues to show 'You have no pending tasks' or displays newly matching tasks per BR-3.
- Given the My Tasks Panel shows no tasks, when tasks are subsequently assigned to the logged-in user, then the panel refreshes on next load to show the assigned contracts instead of the no-tasks message.

### Display empty-state message when no high risk contracts exist (`UC1-AF-003`)
- Given the Legal Reviewer is logged in with a valid tenant account and the dashboard has loaded, When no contract in the tenant has an AI risk score above the tenant-configured high risk threshold, Then the High Risk Contracts Panel displays the message 'No high risk contracts found' instead of a contract list.
- Given the High Risk Contracts Panel is showing the 'No high risk contracts found' message, When the Legal Reviewer views the rest of the dashboard, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card continue to display their respective counts unaffected by the empty high risk state.
- Given the High Risk Contracts Panel is displaying the 'No high risk contracts found' message, When the Legal Reviewer applies the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, Then the dashboard recalculates and the High Risk Contracts Panel either continues to show the 'No high risk contracts found' message or displays newly matching high risk contracts based on the applied filters.
- Given AI clause analysis (UC4) has not yet flagged any contract above the threshold for the tenant, When the dashboard loads or refreshes, Then the 'No high risk contracts found' message is shown instead of an empty list with no explanation.

### Display No-Match Message When Filters Return No Contracts (`UC1-AF-004`)
- Given I am on the Dashboard with at least one filter set among Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, When I click the Apply Filters Button and no contracts match the selected filter combination, Then the system displays the message 'No contracts match the selected filters'.
- Given no contracts match the selected filters, When the dashboard refreshes, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card all display a count of 0.
- Given the no-match message is displayed, When I inspect the filter controls, Then the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter retain the values I selected that produced no results.
- Given the no-match state is displayed, When I click the Clear Filters Button, Then the filters reset and the cards and panels refresh to show unfiltered data for my tenant and role.

### Redirect User to Login on Session Expiry (`UC1-AF-005`)
- Given I am viewing the Dashboard with the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card populated, When my session expires, Then I am redirected to the Login screen and shown the message 'Your session has expired. Please log in again.'
- Given I have applied values in the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter before my session expires, When the session expiry redirect occurs, Then none of these filter selections are retained or exposed after redirection to the Login screen
- Given my session has expired and I am redirected to the Login screen, When I view the screen, Then no dashboard data (Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, Expiring in 90 Days Card, Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, Date Range Filter) remains visible or accessible
- Given I successfully log back in after the session expiry redirect, When the Dashboard reloads, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card are refreshed with current data and all filters (Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, Date Range Filter) default to their reset state

### Block access to unauthorized contract detail screen (`UC1-AF-006`)
- Given the dashboard is loaded with the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, Expiring in 90 Days Card, Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter and Date Range Filter all rendered and populated per the user's tenant and role scope, When the logged-in user's role has no permitted actions on a specific listed contract (e.g. an Approver clicks a contract not assigned to them), Then the message 'You do not have access to this contract' is displayed and navigation to that contract's detail screen is blocked.
- Given the message 'You do not have access to this contract' has been displayed after a blocked click, When the user dismisses the message, Then the user remains on the Dashboard with the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, Expiring in 90 Days Card, Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter and Date Range Filter unchanged from their prior state.
- Given a user without permitted actions on a contract attempts to click into its detail screen, When the access check fails, Then no navigation occurs to the detail screen and the underlying card counts and filter selections (Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, Date Range Filter) remain unaffected by the blocked attempt.

### Display accurate real-time status card counts (`UC1-BR-001`)
- Given contracts exist in the tenant across various statuses, when the dashboard loads, then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, and Executed Card each display a count reflecting only contracts currently in that exact status at load time.
- Given the dashboard is already displayed, when the user triggers a refresh (manually or via Apply Filters Button), then the In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, and Executed Card counts are recalculated to reflect the current status of each contract at that moment.
- Given contracts with upcoming expiry dates exist, when the dashboard loads or refreshes, then the Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card counts are recalculated based on current date comparisons.
- Given the user applies the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, when the dashboard refreshes, then all status card counts reflect only contracts matching the exact status and the currently applied filter values.
- Given a contract transitions from one status to another after the dashboard was last loaded, when the dashboard has not been refreshed, then the status card counts do not reflect the new status until the next load or refresh.
- Given no filters are applied, when the dashboard loads, then the status card counts reflect the full unfiltered set of contracts in each exact status for the tenant.

### Calculate overlapping expiring-contract counts across 30/60/90 day windows (`UC1-BR-002`)
- Given the dashboard loads, When the system calculates expiring-contract counts, Then it computes each contract's remaining days as the contract's end date minus today's date.
- Given a contract expires in 20 days, When the Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card are calculated, Then that contract is counted in all three cards.
- Given a contract expires in 45 days, When the dashboard cards are calculated, Then that contract is counted in the Expiring in 60 Days Card and the Expiring in 90 Days Card but not the Expiring in 30 Days Card.
- Given a contract expires in 85 days, When the dashboard cards are calculated, Then that contract is counted only in the Expiring in 90 Days Card.
- Given the dashboard displays contract status counts, When it renders, Then it also shows the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, and Executed Card alongside the expiring-contract cards.
- Given the user applies the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, When filters are applied, Then the Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card recalculate counts using the same overlapping-window logic against the filtered contract set.

### Restrict My Tasks Panel to Current User's Pending Assignments (`UC1-BR-003`)
- Given I am logged in as a Legal Reviewer, Approver or Signer, When the dashboard loads, Then the My Tasks panel shows only contracts where I am the assigned reviewer, approver or signer for the current pending step.
- Given a contract's pending step is assigned to another user, When I view the My Tasks panel, Then that contract does not appear in my My Tasks panel.
- Given the dashboard applies filters such as Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter and Date Range Filter, When these filters are applied alongside the My Tasks restriction, Then the My Tasks panel still only shows contracts assigned to me for the current pending step within the filtered scope.
- Given the dashboard cards Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card and Expiring in 90 Days Card are displayed, When the dashboard loads, Then these cards reflect tenant-wide counts independently of the My Tasks panel's user-specific restriction.
- Given my role changes from reviewer to approver for a contract's step, When the dashboard refreshes, Then the My Tasks panel updates to reflect my current assignment role for that contract.

### Filter High Risk Contracts Panel by Tenant-Configured Risk Threshold (`UC1-BR-004`)
- Given the tenant has not customized the high risk threshold, when the dashboard loads, then the High Risk Contracts panel displays only contracts with an AI risk score above the default threshold of 70 out of 100.
- Given the tenant admin has configured a custom high risk threshold, when the dashboard loads or refreshes, then the High Risk Contracts panel displays only contracts with an AI risk score above that tenant-configured threshold.
- Given a contract's AI risk score is equal to or below the applicable threshold, when the dashboard loads, then that contract is excluded from the High Risk Contracts panel.
- Given filters are applied via the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, when the user clicks Apply Filters, then the High Risk Contracts panel recalculates alongside the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card, using only contracts whose risk score exceeds the threshold.
- Given the user has applied one or more of the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, when the user clicks Clear Filters, then all filters reset to default and the High Risk Contracts panel, Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card refresh to reflect the tenant-wide threshold-based view.

### View AI Risk Scores as Read-Only Suggestions (`UC1-BR-005`)
- Given the dashboard is displaying the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card, When the High Risk Contracts panel renders AI-generated risk scores, Then no accept or reject control is present anywhere on the dashboard for those scores.
- Given a Legal Reviewer has applied the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter to narrow the view, When the filtered High Risk Contracts panel displays, Then the risk scores remain labeled as AI-generated suggestions with no accept or reject action available.
- Given a user attempts to interact with a risk score shown in the High Risk Contracts panel, When they click or tap on the score, Then no state change occurs on the dashboard and the user is directed to UC4 to accept or reject the AI finding.
- Given the dashboard cards (Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, Expiring in 90 Days Card) and filters (Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, Date Range Filter) refresh after a filter change, When the High Risk Contracts panel reloads, Then risk scores continue to display as read-only suggestions without accept/reject actions.

### Scope Dashboard Data to Logged-in User's Tenant (`UC1-BR-006`)
- Given a user is logged in with a valid tenant account, when the dashboard loads, then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card and Expiring in 90 Days Card display counts computed only from contracts belonging to the logged-in user's tenant.
- Given a user is logged in, when the dashboard populates filter options, then the Contract Type Filter, Department Filter, Counterparty Filter and Owner Filter display only values configured for or associated with the logged-in user's tenant, excluding values from any other tenant.
- Given a user applies the Date Range Filter, when the dashboard recalculates results, then only contracts belonging to the logged-in user's tenant within the selected range are reflected across all cards and panels.
- Given a user attempts to access or manipulate dashboard data via direct URL manipulation or API calls, when the request targets a different tenant's data, then the system denies access and returns no cross-tenant data.
- Given multiple tenants exist in the system, when any card, panel or filter is rendered, then no data, counts, or values originating from another tenant are included or visible to the logged-in user.

### Open Filtered Contract Repository List from Status Card (`UC1-BR-007`)
- Given no dashboard filters are applied, When the user clicks the In Draft Card, Then the Contract Repository list opens filtered to show only contracts in Draft status.
- Given no dashboard filters are applied, When the user clicks the In Negotiation Card, Then the Contract Repository list opens filtered to show only contracts in Negotiation status.
- Given no dashboard filters are applied, When the user clicks the Pending Approval Card, Then the Contract Repository list opens filtered to show only contracts in Pending Approval status.
- Given no dashboard filters are applied, When the user clicks the Pending Signature Card, Then the Contract Repository list opens filtered to show only contracts in Pending Signature status.
- Given no dashboard filters are applied, When the user clicks the Executed Card, Then the Contract Repository list opens filtered to show only contracts in Executed status.
- Given no dashboard filters are applied, When the user clicks the Expiring in 30 Days Card, Then the Contract Repository list opens filtered to show only contracts expiring within 30 days.
- Given no dashboard filters are applied, When the user clicks the Expiring in 60 Days Card, Then the Contract Repository list opens filtered to show only contracts expiring within 60 days.
- Given no dashboard filters are applied, When the user clicks the Expiring in 90 Days Card, Then the Contract Repository list opens filtered to show only contracts expiring within 90 days.
- Given the user clicks the Total Contracts Card, When no other filters are applied, Then the Contract Repository list opens unfiltered showing all contracts in the tenant.
- Given the user has applied the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter and Date Range Filter on the dashboard, When the user clicks any status card, Then the Contract Repository list opens filtered to that card's status combined with the currently applied Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter and Date Range Filter values.

### Recalculate Dashboard Cards and Panels on Date Range Filter Application (`UC1-BR-008`)
- Given I am on the Dashboard with no filters applied, When I set a value in the Date Range Filter and click Apply Filters, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, and Executed Card all recalculate to show only contracts matching the selected date range.
- Given I have applied a Date Range Filter, When the dashboard refreshes, Then the Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card recalculate their counts to only include contracts matching the applied date range.
- Given I have applied a Date Range Filter, When the dashboard refreshes, Then the My Tasks Panel and High Risk Contracts Panel contents are limited to contracts matching the applied date range, subject to the user's role-based visibility rules.
- Given I have applied a Date Range Filter, When I also have the Contract Type Filter, Department Filter, Counterparty Filter, or Owner Filter set, Then the Date Range Filter is combined with those filters and all cards and panels reflect the intersection of all applied filters.
- Given a Date Range Filter has been applied and cards/panels have recalculated, When I click Clear Filters, Then the Date Range Filter resets to default and all cards and panels revert to showing unfiltered tenant-wide data.
- Given I enter a Date Range Filter value, When the date does not conform to DD/MM/YYYY format, Then the system prevents the Apply Filters action from recalculating cards and panels until a valid date range is provided.

### View Tenant-Wide Dashboard as Tenant Admin (`UC1-BR-009`)
- Given I am logged in as a Tenant Admin, When the dashboard loads, Then I see the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, and Executed Card populated with counts scoped to my tenant only.
- Given I am logged in as a Tenant Admin, When the dashboard loads, Then I see the Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card populated with counts scoped to my tenant only.
- Given I am logged in as a Tenant Admin, When no tasks in the tenant are assigned to me, Then the My Tasks panel is empty.
- Given I am logged in as a Tenant Admin, When one or more tasks in the tenant are assigned to me as reviewer, approver, or signer, Then those contracts appear in the My Tasks panel.
- Given I am logged in as a Tenant Admin, When the dashboard loads, Then the High Risk Contracts panel shows all contracts across the tenant whose AI risk score exceeds the configured threshold.
- Given I am logged in as a Tenant Admin, When I use the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter, Then the cards and panels refresh using values scoped only to my tenant.
- Given I am logged in as a Tenant Admin, When I attempt to access another tenant's dashboard data, Then the system prevents access and shows no data belonging to other tenants.

### Scope Dashboard Visibility for Legal Reviewer Role (`UC1-BR-010`)
- Given I am logged in as a Legal Reviewer, When the dashboard loads, Then I can view the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card with no values hidden or restricted.
- Given I am logged in as a Legal Reviewer, When the dashboard loads, Then I can access and use the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter without restriction.
- Given I am logged in as a Legal Reviewer, When I view the My Tasks panel, Then only contracts where I am the assigned reviewer for the current pending step are displayed.
- Given I am logged in as a Legal Reviewer, When I view the High Risk Contracts panel, Then it displays all contracts across the tenant whose AI risk score is above the configured high risk threshold, regardless of contract ownership or assignment.
- Given I am logged in as a Legal Reviewer, When I apply the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card recalculate accordingly, while My Tasks remains scoped to my assigned reviews and High Risk Contracts panel remains scoped to all contracts.

### View scoped dashboard data as Contract Owner (`UC1-BR-011`)
- Given I am logged in as a Contract Owner, When the dashboard loads, Then I can view all status cards including Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card.
- Given I am logged in as a Contract Owner, When the dashboard loads, Then I can access and use all filters including Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter.
- Given I am logged in as a Contract Owner, When I view the My Tasks panel, Then it shows only contracts I own that are awaiting any action, regardless of the specific pending step.
- Given I am logged in as a Contract Owner, When I view the High Risk Contracts panel, Then it shows only contracts that I own with an AI risk score above the tenant-configured high risk threshold.
- Given I am logged in as a Contract Owner, When I apply any combination of the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, Then the cards and panels refresh accordingly while remaining scoped to contracts I own for My Tasks and High Risk panels.

### View Role-Scoped Dashboard as Approver (`UC1-BR-012`)
- Given I am logged in as an Approver, When the dashboard loads, Then I can view the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card.
- Given I am logged in as an Approver, When the dashboard loads, Then I can view and use the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter.
- Given I am logged in as an Approver, When I view the My Tasks panel, Then it shows only contracts currently awaiting my approval.
- Given I am logged in as an Approver, When I view the High Risk Contracts panel, Then it shows all contracts in the tenant whose AI risk score exceeds the configured high risk threshold, regardless of who owns or approves them.
- Given I am logged in as an Approver, When I apply any combination of the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter, Then the cards, My Tasks panel, and High Risk Contracts panel refresh accordingly without exposing data from other tenants.

### Restrict Signer Dashboard View to Signature Tasks and Hide High Risk Panel (`UC1-BR-013`)
- Given I am logged in as a Signer, When the dashboard loads, Then I can view the following cards: Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card.
- Given I am logged in as a Signer, When the dashboard loads, Then I can access and use the following filters: Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter.
- Given I am logged in as a Signer, When the My Tasks panel loads, Then it shows only contracts where I am the assigned signer for the current pending step.
- Given I am logged in as a Signer, When the dashboard loads, Then the High Risk Contracts panel is not displayed to me.
- Given I am logged in as a Signer, When no contracts are awaiting my signature, Then the My Tasks panel displays as empty rather than showing contracts assigned to other roles.
- Given I am logged in as a Signer, When I apply the Date Range Filter along with any of the Contract Type Filter, Department Filter, Counterparty Filter, or Owner Filter, Then the cards and My Tasks panel refresh accordingly while the High Risk Contracts panel remains hidden.

### View Read-Only Contract Status Summary Without Local State Transitions (`UC1-BR-014`)
- Given the dashboard is loaded, When I view the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, and Executed Card, Then each displays a count sourced from the current contract statuses without any control on the dashboard to change those statuses.
- Given the dashboard is loaded, When I view the Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card, Then each displays a read-only count with no mechanism to alter contract status or expiry data from the dashboard.
- Given the dashboard is loaded, When I apply the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, Then the cards and panels re-display filtered counts and lists without triggering any contract status transition.
- Given a contract's status changes in UC2 (Draft), UC5 (In Negotiation/Pending Approval), UC6 (Pending Approval/Pending Signature), or UC7 (Pending Signature/Executed), When the dashboard is next loaded or refreshed, Then the updated status is reflected in the relevant status card but the dashboard itself performed no part of that transition.
- Given I am viewing the dashboard, When I attempt to find an action to directly change a contract's status (Draft, In Negotiation, Pending Approval, Pending Signature, Executed) from any card or filter, Then no such action exists on this screen.
- Given the dashboard is loaded, When status card counts are computed, Then the underlying state machine logic resides exclusively in UC2, UC5, UC6, and UC7, and the dashboard only reads and displays the resulting status values.

### View status cards and apply filters on the dashboard (`UC1-FV-001`)
- Given at least one contract exists in the tenant, When the dashboard loads, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card each display a non-mandatory count label reflecting current contract data scoped to the logged-in user's tenant.
- Given the dashboard has loaded, When no filters are applied, Then the Contract Type Filter, Department Filter, Counterparty Filter, and Owner Filter display their default unselected state with values drawn from the tenant's configured data.
- Given the user selects values in the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and/or Date Range Filter, When the user clicks Apply Filters, Then all status cards (Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, Expiring in 90 Days Card) recalculate their counts based on the selected filter criteria.
- Given a contract's end date falls within 20 days of today, When the Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card are calculated, Then that contract is counted in all three cards.
- Given the Date Range Filter is set using DD/MM/YYYY format, When Apply Filters is clicked, Then card counts and panel contents are recalculated to match only contracts within that date range.
- Given the user clicks the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, or Executed Card, When the click is registered, Then the Contract Repository list opens filtered to that status plus any currently applied Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter values.
- Given filters have been applied, When the user clicks Clear Filters, Then the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter all reset to default and all status cards refresh to unfiltered counts.

### View My Tasks Panel Listing Contracts Awaiting Review, Approval or Signature (`UC1-FV-002`)
- Given I am logged in with a valid tenant account and an assigned role, When the dashboard loads, Then the My Tasks Panel displays only contracts where I am the assigned reviewer, approver or signer for the current pending step.
- Given the dashboard is displayed with the My Tasks Panel, When I review the surrounding status cards, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card are all shown alongside the My Tasks Panel reflecting tenant-scoped counts.
- Given I am a Legal Reviewer, When the dashboard loads, Then the My Tasks Panel shows only contracts assigned to me for review, and the High Risk Contracts Panel shows all contracts in the tenant per BR-10.
- Given I have access to filter controls on the dashboard, When I inspect the available filters, Then the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter are all present and usable to refine the My Tasks Panel contents.
- Given I apply the Date Range Filter using DD/MM/YYYY format and click Apply Filters, When the dashboard refreshes, Then the My Tasks Panel and all status cards recalculate to reflect only contracts matching the selected date range.
- Given data is scoped to my tenant, When the My Tasks Panel renders, Then no contracts from other tenants appear in the list.

### View High Risk Contracts Panel with AI Risk Scores (`UC1-FV-003`)
- Given AI clause analysis (UC4) has run on at least one contract in the tenant, when the dashboard loads, then the High Risk Contracts Panel displays only contracts whose AI risk score is above the tenant-configured high risk threshold (default 70 out of 100), each labeled with its risk score.
- Given the logged-in user is a Legal Reviewer, Tenant Admin, or Approver, when the dashboard loads, then the High Risk Contracts Panel shows all qualifying high-risk contracts across the tenant.
- Given the logged-in user is a Contract Owner, when the dashboard loads, then the High Risk Contracts Panel shows only high-risk contracts owned by that user.
- Given the logged-in user is a Signer, when the dashboard loads, then the High Risk Contracts Panel is not displayed.
- Given the user applies the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and/or Date Range Filter and clicks the Apply Filters Button, when the dashboard refreshes, then the High Risk Contracts Panel contents are recalculated to match the selected filter values alongside the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card.
- Given the user views the dashboard, when risk scores are displayed in the High Risk Contracts Panel, then no accept or reject action controls are shown, as these actions are performed only in UC4.
- Given the logged-in user belongs to Tenant A, when the High Risk Contracts Panel is displayed, then it shows only contracts scoped to Tenant A and never contracts from another tenant.

### Filter Dashboard Cards and Panels Using Filters Panel Controls (`UC1-FV-004`)
- Given the dashboard filters panel is displayed, When it loads, Then it presents the Contract Type Filter populated with values from the tenant's configured contract types, the Department Filter populated with values from the tenant's configured departments, the Counterparty Filter populated with values from counterparties on existing contracts, the Owner Filter populated with values from tenant users with Contract Owner role, and the Date Range Filter with start and end date pickers in DD/MM/YYYY format applied to contract creation or expiry date.
- Given the user has selected values in one or more of Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, or Date Range Filter, When the user clicks Apply Filters Button, Then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card all refresh to reflect only contracts matching the selected filter values.
- Given the user enters a start date and end date in the Date Range Filter in DD/MM/YYYY format, When the user clicks Apply Filters Button, Then the date range is applied to contract creation or expiry date and all cards and panels recalculate accordingly.
- Given one or more filters have been applied and cards have refreshed, When the user clicks Clear Filters Button, Then the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter all reset to their default unselected state and the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card refresh to show unfiltered counts.
- Given the user selects an invalid or out-of-order date range in the Date Range Filter (end date before start date), When the user clicks Apply Filters Button, Then the system prevents the filter from being applied and displays a validation message without refreshing the cards.

### Open New Contract Creation from Dashboard Button (`UC1-FV-005`)
- Given I am logged in with a valid tenant account and assigned role and viewing the Dashboard, When the Dashboard loads, Then the New Contract Button [F-19] is visible and enabled regardless of the current state of the Total Contracts Card [DP-UC1-001], In Draft Card [DP-UC1-002], In Negotiation Card [DP-UC1-003], Pending Approval Card [DP-UC1-004], Pending Signature Card [DP-UC1-005], Executed Card [DP-UC1-006], Expiring in 30 Days Card [DP-UC1-007], Expiring in 60 Days Card [DP-UC1-008], and Expiring in 90 Days Card [DP-UC1-009].
- Given I am on the Dashboard with any combination of the Contract Type Filter [DP-UC1-012], Department Filter [DP-UC1-013], Counterparty Filter [DP-UC1-014], Owner Filter [DP-UC1-015], and Date Range Filter [DP-UC1-016] applied, When I click the New Contract Button [F-19], Then New Contract Creation (UC2) opens without requiring the filters to be cleared or reset.
- Given I click the New Contract Button [F-19], When New Contract Creation (UC2) opens, Then the Dashboard's card counts (Total Contracts Card [DP-UC1-001], In Draft Card [DP-UC1-002], In Negotiation Card [DP-UC1-003], Pending Approval Card [DP-UC1-004], Pending Signature Card [DP-UC1-005], Executed Card [DP-UC1-006], Expiring in 30 Days Card [DP-UC1-007], Expiring in 60 Days Card [DP-UC1-008], Expiring in 90 Days Card [DP-UC1-009]) and applied filters (Contract Type Filter [DP-UC1-012], Department Filter [DP-UC1-013], Counterparty Filter [DP-UC1-014], Owner Filter [DP-UC1-015], Date Range Filter [DP-UC1-016]) remain unchanged in the background Dashboard state.
- Given I am logged in as Tenant Admin, Legal Reviewer, Contract Owner, Approver, or Signer, When I click the New Contract Button [F-19], Then New Contract Creation (UC2) opens for my tenant only, consistent with tenant-scoped data shown across Total Contracts Card [DP-UC1-001], In Draft Card [DP-UC1-002], In Negotiation Card [DP-UC1-003], Pending Approval Card [DP-UC1-004], Pending Signature Card [DP-UC1-005], Executed Card [DP-UC1-006], Expiring in 30 Days Card [DP-UC1-007], Expiring in 60 Days Card [DP-UC1-008], Expiring in 90 Days Card [DP-UC1-009], Contract Type Filter [DP-UC1-012], Department Filter [DP-UC1-013], Counterparty Filter [DP-UC1-014], Owner Filter [DP-UC1-015], and Date Range Filter [DP-UC1-016].

### Display My Tasks Panel List Columns (`UC1-GC-001`)
- Given I am logged in as a Legal Reviewer, Contract Owner, Approver, or Signer with at least one contract assigned to me for the current pending step, When the Dashboard loads, Then the My Tasks panel list displays the columns Contract Name, Counterparty, Status, and Due Date for each assigned contract.
- Given the My Tasks panel is displayed alongside the rest of the Dashboard, When the page renders, Then the dashboard also exposes the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card as separate elements from the My Tasks panel list.
- Given the Dashboard filters are present on the same screen as the My Tasks panel, When I view the filter controls, Then the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter are available and, when applied via Apply Filters, recalculate the My Tasks panel list contents in addition to the cards.
- Given no contracts are currently assigned to the logged-in user for the current pending step, When the Dashboard loads, Then the My Tasks panel list displays with the Contract Name, Counterparty, Status, and Due Date column headers but with no rows.
- Given I am a Signer with a contract awaiting my signature, When the My Tasks panel list renders, Then the Status column shows the contract's current status value (e.g. Pending Signature) and the Due Date column shows the date by which action is required.

### Display High Risk Contracts Panel Ranked by Risk Score (`UC1-GC-002`)
- Given at least one contract has an AI risk score above the tenant-configured high risk threshold, when the dashboard loads, then the High Risk Contracts panel displays the columns Contract Name, Counterparty, and Risk Score for each flagged contract.
- Given multiple contracts appear in the High Risk Contracts panel, when the panel renders, then the list is ordered by Risk Score descending, with the highest risk score shown first.
- Given the dashboard includes other summary elements, when the page loads or refreshes, then the Total Contracts Card, In Draft Card, In Negotiation Card, Pending Approval Card, Pending Signature Card, Executed Card, Expiring in 30 Days Card, Expiring in 60 Days Card, and Expiring in 90 Days Card are displayed alongside the High Risk Contracts panel.
- Given the available filters on the dashboard, when the user views the filter bar, then the Contract Type Filter, Department Filter, Counterparty Filter, Owner Filter, and Date Range Filter are all present and available for use in conjunction with the High Risk Contracts panel.
- Given the logged-in user is a Legal Reviewer, when the High Risk Contracts panel loads, then it shows all high risk contracts across the tenant, per BR-10.
- Given no contracts exceed the high risk threshold, when the dashboard loads, then the High Risk Contracts panel displays no rows.

## Rules

- Do not invent endpoints, routes, DTO fields or table columns beyond what is listed above -- treat this file as the contract for this module.
- Implement every endpoint against the real database via this module's tables/migrations -- no mock/in-memory data (see CLAUDE.md's conventions).
- If a change here would affect another module's existing files, stop and extend shared code instead of rewriting it.
