---
name: lifecycle-uc10-uc11
description: Use when building, extending or fixing the 'lifecycle uc10 uc11' backend module (lifecycle uc10 uc11). Covers the 18 endpoint(s), 24 DTO(s) and 10 table(s) this module owns, plus its acceptance criteria. Do not use for other modules' endpoints.
---

# lifecycle uc10 uc11 — implementation skill

This skill is generated from the module contract (`db_contract` / `api_contract`) and this epic's BRD stories. It governs WHAT this specific module contains; `CLAUDE.md` at the repo root still governs HOW to build (stack, layering, dependency and error-handling conventions) and wins on any disagreement about style or structure.

## Endpoints to implement (base path: `/api/v1`)

Implement exactly these paths, methods and role lists — the frontend calls them literally.

- `GET /api/v1/tracker/ownership` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `TrackerQueryParams`; response: `OwnershipTabResponse` — Get Ownership tab data (Contracts by Owner) with period/filters
- `GET /api/v1/tracker/cycle-time` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `TrackerQueryParams`; response: `CycleTimeTabResponse` — Get Cycle Time tab data (avg cycle time per stage grouped by user/contract type)
- `GET /api/v1/tracker/bottleneck` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `TrackerQueryParams`; response: `BottleneckTabResponse` — Get Bottleneck tab data (current stage, days in stage, stuck flag)
- `GET /api/v1/tracker/turnaround` (paged) — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `TrackerQueryParams`; response: `TurnaroundTabResponse` — Get Turnaround tab data (estimated vs actual turnaround, variance)
- `POST /api/v1/tracker/export` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `TrackerExportRequest`; response: `TrackerExportResponse` — Export currently selected tab data for selected period/filters to Excel or PDF
- `PUT /api/v1/tracker/turnaround/{contractId}/estimated-override` — roles: TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `EstimatedTurnaroundOverrideRequest`; response: `TurnaroundRowResponse` — Override AI-suggested Estimated Turnaround value and log audit entry
- `GET /api/v1/tracker/bottleneck-thresholds` — roles: TENANT_ADMIN; request: `—`; response: `BottleneckThresholdResponse` — Get tenant-configured stuck-flag thresholds per stage
- `GET /api/v1/settings/users` (paged) — roles: TENANT_ADMIN; request: `—`; response: `UserListItemResponse` — List tenant users table (Name/Email/Role/Status/Last Login)
- `POST /api/v1/settings/users` — roles: TENANT_ADMIN; request: `CreateUserRequest`; response: `UserListItemResponse` — Add a new user with Name/Email/Role, validate uniqueness
- `PATCH /api/v1/settings/users/{userId}/status` — roles: TENANT_ADMIN; request: `UpdateUserStatusRequest`; response: `UserListItemResponse` — Deactivate, reactivate, or auto-activate a user; blocks removing last active Tenant Admin
- `GET /api/v1/settings/approval-rules` (paged) — roles: TENANT_ADMIN; request: `—`; response: `ApprovalRuleResponse` — List approval matrix rules (Contract Type/Value Threshold/Approver Role)
- `POST /api/v1/settings/approval-rules` — roles: TENANT_ADMIN; request: `CreateApprovalRuleRequest`; response: `ApprovalRuleResponse` — Add approval rule, validate required fields and duplicate combination
- `GET /api/v1/settings/integrations` — roles: TENANT_ADMIN; request: `—`; response: `IntegrationResponse` — List integration cards (Integration Name/Connection Status)
- `POST /api/v1/settings/integrations/{integrationName}/connect` — roles: TENANT_ADMIN; request: `ConnectIntegrationRequest`; response: `IntegrationResponse` — Submit credentials and authorize integration connection, masks credentials on success
- `POST /api/v1/settings/integrations/{integrationName}/disconnect` — roles: TENANT_ADMIN; request: `—`; response: `IntegrationResponse` — Manually disconnect an integration
- `GET /api/v1/settings/notifications` — roles: TENANT_ADMIN; request: `—`; response: `NotificationEventResponse` — List notification events with Email/In-App toggles
- `PUT /api/v1/settings/notifications/{eventName}` — roles: TENANT_ADMIN; request: `UpdateNotificationEventRequest`; response: `NotificationEventResponse` — Update Email Toggle and/or In-App Toggle for a notification event
- `GET /api/v1/settings/audit-log` (paged) — roles: TENANT_ADMIN; request: `AuditLogQueryParams`; response: `AuditLogEntryResponse` — Get read-only audit log entries sorted newest first with Filter Date Range

Enforce the roles above at the framework's authorization layer **and** with the owner/assignment check in business logic. Missing auth header → 401, disallowed role → 403.


## DTOs — request/response types must match these exactly

- **TrackerQueryParams** (request): `{ period?: string, contractTypeFilter?: string, ownerFilter?: string, dateRangeFrom?: date, dateRangeTo?: date, page?: integer, pageSize?: integer }`
- **OwnershipRowResponse** (response): `{ ownerName: string, contractsOwned: integer, inDraftCount: integer, inNegotiationCount: integer, inApprovalCount: integer, inSignatureCount: integer, completedCount: integer, averageCycleTime?: number }`
- **OwnershipTabResponse** (response): `{ rows: array, isEmpty: boolean, emptyStateMessage?: string, totalCount: integer, page: integer, pageSize: integer }`
- **CycleTimeRowResponse** (response): `{ stage: string, ownerName?: string, contractType?: string, contractsOwned?: integer, averageCycleTime?: number }`
- **CycleTimeTabResponse** (response): `{ rows: array, isEmpty: boolean, emptyStateMessage?: string, totalCount: integer, page: integer, pageSize: integer }`
- **BottleneckRowResponse** (response): `{ contractId: uuid, contractName: string, ownerName?: string, currentStage: string, daysInCurrentStage: integer, stuckFlag: string }`
- **BottleneckTabResponse** (response): `{ rows: array, isEmpty: boolean, emptyStateMessage?: string, totalCount: integer, page: integer, pageSize: integer }`
- **TurnaroundRowResponse** (response): `{ contractId: uuid, contractName: string, contractType: string, estimatedTurnaround?: number, estimatedTurnaroundNotSet: boolean, estimatedTurnaroundSource?: string, actualTurnaround?: number, variance?: number, varianceColor?: string, excludedFromAverages: boolean }`
- **TurnaroundTabResponse** (response): `{ rows: array, isEmpty: boolean, emptyStateMessage?: string, totalCount: integer, page: integer, pageSize: integer }`
- **TrackerExportRequest** (request): `{ tab: string, format: string, period?: string, contractTypeFilter?: string, ownerFilter?: string, dateRangeFrom?: date, dateRangeTo?: date }`
- **TrackerExportResponse** (response): `{ success: boolean, fileUrl?: string, failureMessage?: string }`
- **EstimatedTurnaroundOverrideRequest** (request): `{ newEstimatedTurnaround: number, overrideReason?: string, originalAiSuggestedValue?: number, overriddenBy: uuid, overrideTimestamp: datetime }`
- **BottleneckThresholdResponse** (response): `{ stage: string, thresholdDays: integer }`
- **UserListItemResponse** (response): `{ id: uuid, name: string, email: string, role: string, status: string, lastLogin?: datetime }`
- **CreateUserRequest** (request): `{ name: string, email: string, role: string }`
- **UpdateUserStatusRequest** (request): `{ status: string }`
- **ApprovalRuleResponse** (response): `{ id: uuid, contractType: string, valueThreshold: number, approverRole: string }`
- **CreateApprovalRuleRequest** (request): `{ contractType: string, valueThreshold: number, approverRole: string }`
- **IntegrationResponse** (response): `{ integrationName: string, connectionStatus: string, maskedCredential?: string }`
- **ConnectIntegrationRequest** (request): `{ credentials: object }`
- **NotificationEventResponse** (response): `{ eventName: string, emailToggle: boolean, inAppToggle: boolean }`
- **UpdateNotificationEventRequest** (request): `{ emailToggle?: boolean, inAppToggle?: boolean }`
- **AuditLogQueryParams** (request): `{ filterDateRangeFrom?: date, filterDateRangeTo?: date, userFilter?: string, actionTypeFilter?: string, page?: integer, pageSize?: integer }`
- **AuditLogEntryResponse** (response): `{ id: uuid, logDateTime: datetime, logUser: string, logAction: string, logEntity: string, details?: string }`

## Tables (models mirror these)

### `contract_lifecycle_stage_history` — Stores stage start/end timestamps per contract to power cycle time and bottleneck calculations, with denormalized contracts-owned snapshot for cycle time grouping
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `stage`: VARCHAR (not null)
- `stage_start_date`: TIMESTAMPTZ (not null)
- `stage_end_date`: TIMESTAMPTZ (nullable)
- `contracts_owned_snapshot`: INTEGER (nullable)
- `tenant_id`: UUID (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_stage_history_contract

### `contract_owners` — Maps contracts to owners, legal reviewers and approvers for role-scoped tracker visibility
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `user_id`: UUID (not null)
- `role`: VARCHAR (not null)
- `tenant_id`: UUID (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_contract_owners_user

### `contract_turnaround_metrics` — Stores estimated/actual turnaround source and values per contract
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `estimated_turnaround_days`: NUMERIC (nullable)
- `estimated_turnaround_source`: VARCHAR (nullable)
- `actual_turnaround_days`: NUMERIC (nullable)
- `excluded_from_averages`: BOOLEAN (not null)
- `tenant_id`: UUID (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: idx_turnaround_contract

### `turnaround_override_log` — Audit log of overrides to AI-suggested Estimated Turnaround values, capturing original AI-suggested value, new user-entered value, overriding user, and timestamp
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `original_ai_value`: NUMERIC (nullable)
- `new_value`: NUMERIC (not null)
- `override_user_id`: UUID (not null)
- `override_timestamp`: TIMESTAMPTZ (not null)
- `decision`: VARCHAR (not null)
- `tenant_id`: UUID (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)

### `tenant_bottleneck_thresholds` — Tenant-configured Days-in-Stage thresholds for Stuck Flag per stage
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `stage`: VARCHAR (not null)
- `threshold_days`: INTEGER (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_threshold_tenant_stage

### `tenant_users` — Stores tenant user records for User Management tab
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `name`: VARCHAR (not null)
- `email`: VARCHAR (not null)
- `role`: VARCHAR (not null)
- `status`: VARCHAR (not null)
- `last_login`: TIMESTAMPTZ (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: uq_tenant_user_email

### `approval_matrix_rules` — Stores Routing & Approval matrix rules per tenant
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `contract_type`: VARCHAR (not null)
- `value_threshold`: NUMERIC (not null)
- `approver_role`: VARCHAR (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: uq_rule_type_threshold

### `tenant_integrations` — Stores integration connection records with masked credentials
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `integration_name`: VARCHAR (not null)
- `connection_status`: VARCHAR (not null)
- `credential_ciphertext`: TEXT (nullable)
- `credential_masked_display`: VARCHAR (nullable)
- `token_expires_at`: TIMESTAMPTZ (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: uq_tenant_integration_name

### `tenant_notification_settings` — Stores notification event preferences per tenant
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `event_name`: VARCHAR (not null)
- `email_toggle`: BOOLEAN (not null)
- `in_app_toggle`: BOOLEAN (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: uq_tenant_event_name

### `tenant_audit_log` — Immutable, system-generated audit log for all Settings/Admin actions and AI clause decisions
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `log_date_time`: TIMESTAMPTZ (not null)
- `log_user`: VARCHAR (not null)
- `log_action`: VARCHAR (not null)
- `log_entity`: VARCHAR (not null)
- `details`: TEXT (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: idx_audit_log_date

## Migrations

Create these with exactly these names, in this order:

- `CreateContractLifecycleStageHistory`
- `CreateContractOwners`
- `CreateContractTurnaroundMetrics`
- `CreateTurnaroundOverrideLog`
- `CreateTenantBottleneckThresholds`
- `CreateTenantUsers`
- `CreateApprovalMatrixRules`
- `CreateTenantIntegrations`
- `CreateTenantNotificationSettings`
- `CreateTenantAuditLog`

Never edit or re-order a migration that already exists — add a new one.


## Acceptance criteria to satisfy

### View contract tracking data across Ownership, Cycle Time, Bottleneck and Turnaround tabs (`UC10-MF-001`)
- Given the user navigates Home Page -> CLM Hub -> Tracker, When the Tracker loads, Then the system displays the Ownership tab showing Owner Name and Contracts Owned columns alongside In Draft, In Negotiation, In Approval, In Signature and Completed counts.
- Given the user clicks the Cycle Time tab, When the tab loads, Then the system displays Average Cycle Time per stage grouped by user and contract type in a table and bar chart.
- Given the user clicks the Bottleneck tab, When the tab loads, Then the system displays Current Stage, Days in Current Stage and Stuck Flag (Yes/No) for each contract.
- Given the user clicks the Turnaround tab, When the tab loads, Then the system displays Contract Name, Contract Type, Estimated Turnaround, Actual Turnaround and Variance for each contract.
- Given the user selects a value in the Period dropdown (Daily, Weekly, Monthly), When the selection is made, Then all tabs refresh to show data for the selected period.
- Given the user applies the Contract Type Filter, Owner Filter, Date Range From and Date Range To filters, When the filters are applied, Then the visible tab refreshes with filtered results and Date Range From must be earlier than Date Range To.
- Given the user clicks Export and selects Excel or PDF, When export completes, Then the system downloads the report file for the currently selected tab and period.
- Given this story's required data points, When the Tracker tabs and controls are evaluated, Then the following named data points are all present and correctly labeled: Period, Contract Type Filter, Owner Filter, Date Range From, Date Range To, Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, Variance, and the field previously governed by BR-4 (Estimated Turnaround Days source) reflecting the Change UC10 BR4 update.

### Display empty-state message when no contracts exist in tenant (`UC10-AF-001`)
- Given a tenant with no contracts in the system, when any permitted user (Tenant Admin, Contract Owner, Legal Reviewer, or Approver) opens the Tracker, then the system displays the message "No contract data available to display." instead of any tab content.
- Given the empty-state message is displayed, when the screen renders, then the Period [DP-UC10-001] dropdown, Contract Type Filter [DP-UC10-002], Owner Filter [DP-UC10-003], Date Range From [DP-UC10-004], and Date Range To [DP-UC10-005] controls are still shown but yield no results when applied, since no contracts exist.
- Given the empty-state message is displayed, when the user inspects the Ownership tab, then no rows are shown for Owner Name [DP-UC10-010], Contracts Owned [DP-UC10-011], or Average Cycle Time [DP-UC10-012], and the empty-state message is shown in place of the table.
- Given the empty-state message is displayed, when the user inspects the Bottleneck tab, then no rows are shown for Current Stage [DP-UC10-013], Days in Current Stage [DP-UC10-014], or Stuck Flag [DP-UC10-015], and the empty-state message is shown in place of the table.
- Given the empty-state message is displayed, when the user inspects the Turnaround tab, then no rows are shown for Estimated Turnaround [DP-UC10-016], Actual Turnaround [DP-UC10-017], or Variance [DP-UC10-018], and the empty-state message is shown in place of the table.
- Given BR-4 is updated per the reviewer-supplied change [DP-UC10-020], when Estimated Turnaround would otherwise be calculated, then the empty-state message takes precedence over any turnaround calculation display since no contracts exist to evaluate.
- Given the empty-state message is displayed, when the user attempts to use the Export Button, then no export is available since there is no contract data to export.

### Block unauthorized direct-link access to Tracker (`UC10-AF-002`)
- Given a user who is not a Tenant Admin, Contract Owner (Sales/Procurement), Legal Reviewer, or Approver, when they attempt to access the Tracker screen via a direct link, then the system displays the message 'You do not have permission to view this page.' and redirects the user to the Dashboard without rendering any Tracker content.
- Given the access attempt is blocked, then none of the Tracker's filter controls or data fields are exposed to the user, including Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To.
- Given the access attempt is blocked, then none of the Ownership tab data is exposed to the user, including Owner Name and Contracts Owned.
- Given the access attempt is blocked, then none of the Cycle Time tab data is exposed to the user, including Average Cycle Time.
- Given the access attempt is blocked, then none of the Bottleneck tab data is exposed to the user, including Current Stage, Days in Current Stage, and Stuck Flag.
- Given the access attempt is blocked, then none of the Turnaround tab data is exposed to the user, including Estimated Turnaround, Actual Turnaround, and Variance.
- Given BR-4 governs Estimated Turnaround Days behavior when no target completion date was set, when the business rule change referenced as 'Change UC10 BR4 to' is applied, then the updated rule is enforced consistently and does not alter the access-denial behavior defined in this alternate flow for unauthorized users.

### Display no-records message for empty date range selection (`UC10-AF-003`)
- Given I am on the Tracker screen with Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To all available as filter inputs, When I select a Date Range From and Date Range To spanning a period in which no contracts exist, Then the system displays the message "No records found for the selected period." instead of any tab data.
- Given the no-records message is displayed, When I view the Ownership Tab, Cycle Time Tab, Bottleneck Tab, or Turnaround Tab, Then none of the following data points are populated with values: Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, Variance.
- Given the selected Date Range From is earlier than the selected Date Range To and overrides the Period dropdown per BR-6, When no contracts fall within that range, Then the Period, Contract Type Filter, and Owner Filter selections remain visible on screen but yield no matching records and the no-records message is shown.
- Given Estimated Turnaround is not set for a contract, When BR-4 is applied so that Estimated Turnaround displays 'Not Set' and the contract is excluded from turnaround averages, Then the Change UC10 BR4 to data point reflects this exclusion rule consistently with the no-records scenario when such exclusions result in zero remaining contracts for the selected period.
- Given the no-records message is displayed, When I attempt to trigger an export via the Export Button, Then the export produces a file indicating no records for the selected period rather than an empty or malformed report.

### Display export failure message and retain current view (`UC10-AF-004`)
- Given a user on the Tracker screen with the on-screen view configured using Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To, When the user clicks the Export Button and report generation fails, Then the system displays the message "Export failed. Please try again."
- Given the export has failed, When the failure message is displayed, Then the on-screen view remains unchanged, including the current selections for Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To, and the currently active tab is not switched or reset
- Given the export failure occurs while viewing the Ownership tab, When the failure message is shown, Then the Owner Name and Contracts Owned values displayed in the table rows remain unchanged
- Given the export failure occurs while viewing the Cycle Time tab, When the failure message is shown, Then the Average Cycle Time values remain unchanged
- Given the export failure occurs while viewing the Bottleneck tab, When the failure message is shown, Then the Current Stage, Days in Current Stage, and Stuck Flag values remain unchanged
- Given the export failure occurs while viewing the Turnaround tab, When the failure message is shown, Then the Estimated Turnaround, Actual Turnaround, and Variance values remain unchanged
- Given Estimated Turnaround for a contract was not set at Contract Creation, When Change UC10 BR4 to is applied as the updated business rule governing turnaround averages, Then the export failure handling behaves consistently with that updated rule without altering displayed field values after the failed export

### Display empty table when conflicting filters are applied (`UC10-AF-005`)
- Given the Tracker screen is open with Period [DP-UC10-001] selected, When the user sets a Contract Type Filter [DP-UC10-002] value that has no contracts owned by the selected Owner Filter [DP-UC10-003] value, Then the system displays an empty table with the message "No records match the selected filters."
- Given a Date Range From [DP-UC10-004] and Date Range To [DP-UC10-005] combination is applied together with a conflicting Contract Type Filter [DP-UC10-002] and Owner Filter [DP-UC10-003], When no contracts satisfy all selected filter conditions, Then the system suppresses the data table rows and columns including Owner Name [DP-UC10-010], Contracts Owned [DP-UC10-011], Average Cycle Time [DP-UC10-012], Current Stage [DP-UC10-013], Days in Current Stage [DP-UC10-014], Stuck Flag [DP-UC10-015], Estimated Turnaround [DP-UC10-016], Actual Turnaround [DP-UC10-017], and Variance [DP-UC10-018], and shows only the empty-state message.
- Given the empty-state message "No records match the selected filters." is displayed, When the user adjusts the Contract Type Filter [DP-UC10-002], Owner Filter [DP-UC10-003], Date Range From [DP-UC10-004], or Date Range To [DP-UC10-005] to a non-conflicting combination, Then the table repopulates with matching records and the empty-state message is removed.
- Given the updated turnaround-exclusion rule referenced as Change UC10 BR4 to [DP-UC10-020], When Estimated Turnaround [DP-UC10-016] is Not Set for all contracts matching the applied filters, Then those contracts are excluded from turnaround averages and, if no contracts remain, the empty-state message "No records match the selected filters." is shown instead of a turnaround table.

### Calculate average cycle time per stage from completed stage durations (`UC10-BR-001`)
- Given a selected Period of Daily, Weekly, or Monthly, When the Cycle Time Tab is opened, Then the Average Cycle Time per stage is computed as the mean of (stage end date - stage start date) across all contracts matching the applied Contract Type Filter and/or Owner Filter that have completed that stage within the selected Period.
- Given a custom Date Range is applied using Date Range From and Date Range To, When the Cycle Time Tab is viewed, Then the Average Cycle Time calculation uses only contracts that completed the stage within that Date Range instead of the selected Period.
- Given the Tracker screen with its Period dropdown, Contract Type Filter, Owner Filter, Date Range From, Date Range To, Ownership Tab, Cycle Time Tab, Bottleneck Tab, and Turnaround Tab, When data is displayed across tabs, Then the following data points are shown and correctly populated: Period, Contract Type Filter, Owner Filter, Date Range From, Date Range To, Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance.
- Given BR-4 defines Estimated Turnaround Days exclusion rules, When 'Change UC10 BR4 to' update is reviewed, Then the updated BR-4 behavior is reflected consistently wherever Estimated Turnaround and Variance calculations are derived from it.
- Given no contracts have completed a given stage in the selected period or date range, When the Cycle Time Tab is rendered, Then the Average Cycle Time for that stage displays as not available rather than an erroneous value.

### Flag Contracts as Bottlenecks Based on Stage Threshold (`UC10-BR-002`)
- Given the Bottleneck Tab is selected with Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To applied, When the Tracker loads contract data, Then the Bottleneck tab table displays Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance for each applicable contract.
- Given a contract is in the Drafting or Negotiation stage, When Days in Current Stage exceeds the tenant-configured threshold (default 5 days), Then the Stuck Flag is set to Yes.
- Given a contract is in the Approval or Signature stage, When Days in Current Stage exceeds the tenant-configured threshold (default 3 days), Then the Stuck Flag is set to Yes.
- Given a contract's Days in Current Stage does not exceed the applicable tenant-configured threshold for its Current Stage, When the Bottleneck tab is rendered, Then the Stuck Flag is set to No.
- Given a Tenant Admin has overridden the default thresholds for Drafting, Negotiation, Approval, or Signature stages, When the Bottleneck flag is evaluated, Then the Stuck Flag calculation uses the tenant-configured threshold instead of the default value (Change UC10 BR4 to reflect tenant-specific configuration is applied where set).
- Given the Tracker screen is reopened, When the Bottleneck tab is viewed again, Then Period and Tab selections reset per BR-13 while Stuck Flag values are recalculated fresh based on current Days in Current Stage data.

### Display Turnaround Variance with Delay or On-Time Color Coding (`UC10-BR-003`)
- Given a contract has both an Estimated Turnaround and an Actual Turnaround value, when the Turnaround Tab is displayed, then the Variance is calculated as Actual Turnaround minus Estimated Turnaround and shown numerically in the Variance column.
- Given the calculated Variance is a positive value, when the Turnaround Tab renders the row, then the Variance is displayed in red to indicate a delay.
- Given the calculated Variance is negative or equal to zero, when the Turnaround Tab renders the row, then the Variance is displayed in green to indicate on-time or early completion.
- Given the viewing role is Tenant Admin, when the Tracker screen is opened, then the following data points are available for review and configuration as applicable: Period, Contract Type Filter, Owner Filter, Date Range From, Date Range To, Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, Variance, and Change UC10 BR4 to.
- Given a Period, Contract Type Filter, Owner Filter, Date Range From, or Date Range To is applied, when the Turnaround Tab data is refreshed, then the Variance values recalculate for all contracts within the filtered scope.
- Given the Tenant Admin exports the Turnaround Tab, when the export is generated, then the Variance column retains its red or green color coding in the exported Excel or PDF file.

### Derive Estimated Turnaround from Contract Creation target completion date (`UC10-BR-004`)
- Given a contract that had a target completion date set during Contract Creation (UC2), When the Tracker's Turnaround Tab [F-9] is viewed for the selected Period [F-1] (optionally narrowed by Contract Type Filter [F-2], Owner Filter [F-3], Date Range From [F-4] and Date Range To [F-5]), Then the Estimated Turnaround [F-16] value is populated directly from that UC2 target completion date and the Actual Turnaround [F-17] and Variance [F-18] are calculated and displayed alongside it.
- Given a contract that did not have a target completion date set at Contract Creation (UC2), When that contract's row is displayed in the Turnaround Tab [F-9], Then the Estimated Turnaround [F-16] field displays "Not Set" instead of a numeric value, and Variance [F-18] is not computed for that row.
- Given a contract whose Estimated Turnaround [F-16] displays "Not Set", When tenant-wide or filtered turnaround averages are calculated, Then that contract is excluded from the average Estimated Turnaround and average Variance [F-18] calculations across the Tracker.
- Given the Tracker screen is open, Then the following data points remain available and correctly rendered per their respective tabs and filters: Period [DP-UC10-001], Contract Type Filter [DP-UC10-002], Owner Filter [DP-UC10-003], Date Range From [DP-UC10-004], Date Range To [DP-UC10-005], Owner Name [DP-UC10-010], Contracts Owned [DP-UC10-011], Average Cycle Time [DP-UC10-012], Current Stage [DP-UC10-013], Days in Current Stage [DP-UC10-014], Stuck Flag [DP-UC10-015], Estimated Turnaround [DP-UC10-016], Actual Turnaround [DP-UC10-017], and Variance [DP-UC10-018], consistent with the revised BR-4 source-of-truth behaviour noted in Change UC10 BR4 to [DP-UC10-020].
- Given a role-restricted viewer (Contract Owner, Legal Reviewer or Approver) accesses the Turnaround Tab [F-9], When contracts with "Not Set" Estimated Turnaround [F-16] fall within their entitled scope, Then those contracts are still visible in the list but remain excluded from any average turnaround figures shown to that role.

### Restrict Tracker contract visibility by viewing role (`UC10-BR-005`)
- Given a user with the Tenant Admin role opens the Tracker and sets the Period, applies the Contract Type Filter, Owner Filter, Date Range From and Date Range To, then switches between tabs, when the Tracker data loads, then all tenant contracts are included and the Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround and Variance values are shown across all contracts regardless of role ownership.
- Given a user with the Contract Owner (Sales/Procurement) role opens the Tracker, when the Period, Contract Type Filter, Owner Filter, Date Range From and Date Range To are applied, then only contracts where that user holds the Contract Owner role are included, and the displayed Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround and Variance reflect only that user's owned contracts.
- Given a user with the Legal Reviewer role opens the Tracker, when the Period, Contract Type Filter, Owner Filter, Date Range From and Date Range To are applied, then only contracts where that user holds the Legal Reviewer role are included, and the Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround and Variance are limited to those contracts.
- Given a user with the Approver role opens the Tracker, when the Period, Contract Type Filter, Owner Filter, Date Range From and Date Range To are applied, then only contracts where that user holds the Approver role are included, and the Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround and Variance are limited to those contracts.
- Given BR-4 governs Estimated Turnaround calculation, when applying the Change UC10 BR4 to update, then the revised Estimated Turnaround rule is enforced consistently for all role-scoped views described above without altering the role-based visibility restrictions of BR-5.

### Refresh tracker report data based on period or custom date range (`UC10-BR-006`)
- Given no custom Date Range is applied, When I select the Period as Daily, Then the Tracker refreshes all report data to reflect the last 24 hours.
- Given no custom Date Range is applied, When I select the Period as Weekly, Then the Tracker refreshes all report data to reflect the last 7 days.
- Given no custom Date Range is applied, When I select the Period as Monthly, Then the Tracker refreshes all report data to reflect the last 30 days.
- Given a valid Date Range From and Date Range To have been entered, When I apply the custom Date Range, Then it overrides the current Period selection and the Tracker refreshes data scoped to that custom range instead.
- Given the Period or Date Range has been changed and the Tracker has refreshed, Then the following data points are recalculated and re-displayed for the selected scope: Period, Contract Type Filter, Owner Filter, Date Range From, Date Range To, Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, Variance, and Change UC10 BR4 to.
- Given a custom Date Range is cleared after having been applied, When no Date Range remains set, Then the Tracker reverts to refreshing data according to the currently selected Period.

### Label AI-suggested estimated turnaround and log overrides (`UC10-BR-007`)
- Given the Tracker screen is displaying the Turnaround Tab, When a contract's Estimated Turnaround value was populated by an AI-suggested duration, Then the Estimated Turnaround field is visibly labelled 'AI Suggested' alongside its numeric value.
- Given an Estimated Turnaround value labelled 'AI Suggested', When a Contract Owner, Legal Reviewer, Approver or Tenant Admin overrides that value, Then the override is logged per the platform's accept/reject audit rule, capturing the original AI-suggested value, the new user-entered value, the user, and the timestamp.
- Given the Tracker screen's filter and tab controls, When the user interacts with the screen, Then the following named data points are all present and correctly rendered: Period, Contract Type Filter, Owner Filter, Date Range From, Date Range To, Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance.
- Given BR-4 currently states that Estimated Turnaround Days is taken solely from the target completion date set at Contract Creation (UC2), When BR-7 introduces AI-suggested estimated durations as an alternate source for populating Estimated Turnaround, Then BR-4 must be revised (Change UC10 BR4 to) to explicitly account for AI-suggested values as a valid population source alongside the UC2 target completion date, with the 'Not Set' exclusion rule still applying when neither source is available.
- Given an Estimated Turnaround value was AI-suggested and subsequently overridden, When the override is rejected or reverted, Then the audit log reflects the accept/reject decision consistent with the platform's standard accept/reject audit rule used elsewhere in the system.

### View and export full-tenant Tracker data as Tenant Admin (`UC10-BR-008`)
- Given I am logged in as Tenant Admin, When I open the Tracker screen, Then I can view Tracker data for all contracts, owners and users in the tenant, with no restriction based on contract ownership or role involvement.
- Given I am viewing the Tracker, When I apply filters, Then I can set Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To across all tenant data without restriction.
- Given the Ownership tab is open, When tenant-wide data is displayed, Then the Owner Name, Contracts Owned, and Average Cycle Time fields are shown for every owner in the tenant.
- Given the Bottleneck tab is open, When tenant-wide data is displayed, Then the Current Stage, Days in Current Stage, and Stuck Flag fields are shown for every contract in the tenant.
- Given the Turnaround tab is open, When tenant-wide data is displayed, Then the Estimated Turnaround, Actual Turnaround, and Variance fields are shown for every contract in the tenant.
- Given I am on any tab (Ownership, Cycle Time, Bottleneck, or Turnaround), When I select the Export Button, Then I can export that tab's full tenant data to Excel or PDF format.
- Given UC10 BR4 is changed per DP-UC10-020, When Estimated Turnaround is affected by that change, Then the Tenant Admin's tenant-wide view and export reflect the updated BR4 behavior accordingly.

### Restrict Contract Owner Tracker view to owned contracts (`UC10-BR-009`)
- Given I am logged in as a Contract Owner, When I open the Tracker screen, Then I see Tracker data only for contracts I own, filtered by Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To restricted to my own contracts.
- Given I am viewing the Ownership Tab, When the tab loads my data, Then I see only Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance values corresponding to contracts I own.
- Given I attempt to apply the Owner Filter, When I select a value, Then only Owner Name and associated data for owners other than myself are excluded, confirming I cannot view other users' ownership or cycle time data.
- Given I click the Export Button, When the export is generated in Excel or PDF format, Then the exported file contains only my own Tracker view data including Period, Contract Type Filter, Owner Filter, Date Range From, Date Range To, Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance.
- Given BR-4 is updated per Change UC10 BR4 to reflect that Estimated Turnaround is excluded from averages when not set, When I view my Tracker data, Then contracts without an Estimated Turnaround display 'Not Set' and are excluded from turnaround averages within my own data scope.
- Given I attempt to bypass filters via direct navigation or API manipulation, When I request Tracker data for another owner, Then the system denies access and displays no data outside contracts I own.

### Restrict Legal Reviewer Tracker data to reviewed contracts only (`UC10-BR-010`)
- Given I am logged in as a Legal Reviewer, When I open the Tracker screen, Then the Period [DP-UC10-001] dropdown, Contract Type Filter [DP-UC10-002], Owner Filter [DP-UC10-003], Date Range From [DP-UC10-004] and Date Range To [DP-UC10-005] are available but all resulting data is scoped only to contracts I have reviewed.
- Given I navigate to the Cycle Time, Bottleneck or Turnaround tabs, When the data loads, Then only rows for contracts I have reviewed are shown, displaying Owner Name [DP-UC10-010], Contracts Owned [DP-UC10-011], Average Cycle Time [DP-UC10-012], Current Stage [DP-UC10-013], Days in Current Stage [DP-UC10-014], Stuck Flag [DP-UC10-015], Estimated Turnaround [DP-UC10-016], Actual Turnaround [DP-UC10-017] and Variance [DP-UC10-018] limited to my reviewed contracts.
- Given another Legal Reviewer has reviewed contracts I did not review, When I view any Tracker tab, Then no cycle time, bottleneck or turnaround data belonging to that other reviewer's contracts is displayed to me.
- Given BR-4 is updated per Change UC10 BR4 to [DP-UC10-020], When Estimated Turnaround [DP-UC10-016] is not set for a contract I reviewed, Then that contract is excluded from my turnaround averages consistent with the revised BR-4 behavior.
- Given I attempt to access another reviewer's dataset via filter manipulation or direct navigation, When the system processes the request, Then access is denied and only my own reviewed-contract data remains visible.

### Restrict Approver Tracker visibility to assigned approval-stage data (`UC10-BR-011`)
- Given I am logged in as an Approver, When I open the Tracker screen, Then the Period [DP-UC10-001] filter, Contract Type Filter [DP-UC10-002], Owner Filter [DP-UC10-003], Date Range From [DP-UC10-004] and Date Range To [DP-UC10-005] are available but the data returned is scoped only to contracts where I am an assigned approver.
- Given I navigate to the Cycle Time tab, When the data loads, Then I see Average Cycle Time [DP-UC10-012] only for the Approval stage of contracts I am assigned to approve, and I cannot view cycle time data for Drafting, Negotiation or Signature stages beyond my own involvement.
- Given I navigate to the Bottleneck tab, When the data loads, Then I see Current Stage [DP-UC10-013], Days in Current Stage [DP-UC10-014] and Stuck Flag [DP-UC10-015] only for contracts I am assigned to approve, and no bottleneck data is shown for contracts assigned to other approvers.
- Given I navigate to the Ownership or Turnaround tabs, When the data loads, Then Owner Name [DP-UC10-010], Contracts Owned [DP-UC10-011], Estimated Turnaround [DP-UC10-016], Actual Turnaround [DP-UC10-017] and Variance [DP-UC10-018] are displayed only to the extent they relate to the approval stage of contracts I am assigned to, in accordance with the revised Estimated Turnaround calculation per Change UC10 BR4 to [DP-UC10-020].
- Given I attempt to access cycle time or bottleneck detail for a contract or stage where I am not the assigned approver, When the system evaluates my role scope, Then that contract's or stage's detail is excluded from my Tracker view.

### Block External Party and Signer from accessing the Tracker screen (`UC10-BR-012`)
- Given a user logged in with the role External Party or Signer, When that user attempts to navigate to the Tracker screen, Then access is denied and no Tracker data or controls are rendered, including Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To.
- Given a user logged in with the role External Party or Signer, When the system blocks Tracker access, Then none of the following data points are ever returned or displayed to that user: Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, Variance.
- Given a user logged in with the role External Party or Signer, When they attempt to request Tracker data directly via API or deep link, Then the request is rejected with an authorization error and is logged, consistent with Change UC10 BR4 to restrict visibility based on entitlement.
- Given a Tenant Admin, Contract Owner, Legal Reviewer or Approver is logged in, When they access the Tracker, Then the system confirms these are the only roles permitted, reaffirming that External Party and Signer remain excluded regardless of any contract association.

### Reset Tracker view state on screen open with no persisted object transitions (`UC10-BR-013`)
- Given the Tracker has no object state transitions of its own, When any tab is viewed, Then the displayed values for Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance are read-only reflections of states managed in UC2, UC5, UC6 and UC7, with no edit or transition actions available on the Tracker screen.
- Given a user has previously set Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To, When the user closes and reopens the Tracker screen, Then Period resets to its default value, Contract Type Filter and Owner Filter reset to their default (All) state, and Date Range From and Date Range To are cleared, since only Period and Tab state exist and neither persists across sessions.
- Given a user has selected a non-default Tab on the Tracker, When the screen is reopened, Then the Tab resets to its default selection, confirming that only Period and Tab state exist and both reset on each open.
- Given the requirement to change UC10 BR4 to [DP-UC10-020] has been applied, When Estimated Turnaround is displayed without a target completion date set in UC2, Then the field displays 'Not Set' and the contract is excluded from turnaround averages, consistent with the Tracker's role as a non-transitional, read-only reporting layer.

### Validate Report Controls Panel fields and data outputs on the Tracker (`UC10-FV-001`)
- Given the Tracker screen is opened, When the Report Controls Panel renders, Then the Period dropdown is mandatory and offers Daily, Weekly, Monthly, and the Contract Type Filter and Owner Filter dropdowns are optional and offer the tenant's configured contract types/users plus All.
- Given no Period is selected, When the user attempts to generate the report, Then a validation error is shown requiring Period selection before proceeding.
- Given the user enters a Date Range From value, When the Date Range From is not earlier than Date Range To, Then a validation error is displayed requiring Date Range From to be earlier than Date Range To.
- Given the user enters a Date Range To value, When the Date Range To is not later than Date Range From, Then a validation error is displayed requiring Date Range To to be later than Date Range From.
- Given valid filters are applied and the Ownership tab is selected, When the report data loads, Then each row displays Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance as applicable to the active tab.
- Given the Cycle Time tab is selected, When data loads, Then Average Cycle Time is displayed per stage per user/contract type.
- Given the Bottleneck tab is selected, When data loads, Then Current Stage, Days in Current Stage, and Stuck Flag are displayed for each contract.
- Given the Turnaround tab is selected, When data loads, Then Estimated Turnaround, Actual Turnaround, and Variance are displayed for each contract, with Variance computed as Actual minus Estimated.
- Given a contract has no target completion date set at Contract Creation, When Estimated Turnaround is displayed, Then per the Change UC10 BR4 to update, the field shows 'Not Set' and the contract is excluded from turnaround averages.
- Given a valid Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To combination is set, When the Export Button is clicked, Then the currently selected tab's data for the selected period is exported in Excel or PDF format.

### View Contracts by Owner table in Ownership tab (`UC10-GC-001`)
- Given I am logged in with a role permitted to view the Tracker, When I select the Ownership Tab, Then the Contracts by Owner table displays columns Owner Name, Contracts Owned, In Draft, In Negotiation, In Approval, In Signature, and Completed for each owner within my role's data entitlement.
- Given the Ownership tab is displayed, When I set the Period, Contract Type Filter, Owner Filter, Date Range From, and Date Range To, Then the table data refreshes to reflect those filter selections and the Period/Date Range precedence rule.
- Given I review the Ownership tab table row for an owner, When the row is rendered, Then it shows Owner Name, Contracts Owned (count), Average Cycle Time where applicable, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance for related drill-down data available from other tabs.
- Given an owner's Estimated Turnaround was not set at Contract Creation, When the table computes turnaround figures, Then the field displays 'Not Set' and that contract is excluded from turnaround averages, per the data point labeled 'Change UC10 BR4 to' which clarifies this exclusion behavior for Estimated Turnaround.
- Given the Ownership tab table is populated, When I inspect the Variance values, Then positive Variance values (Actual Turnaround minus Estimated Turnaround) are shown in red and negative or zero values are shown in green.
- Given I have appropriate access, When I trigger the Export Button, Then the Ownership tab table data, including Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, and Variance, is exported per my role's entitlement scope.

### View Average Cycle Time per Stage grouped by user and contract type (`UC10-GC-002`)
- Given I am on the Tracker screen with permitted role, When I apply the Period filter [DP-UC10-001] set to Daily, Weekly or Monthly, or override it with Date Range From [DP-UC10-004] and Date Range To [DP-UC10-005], and optionally filter using Contract Type Filter [DP-UC10-002] and Owner Filter [DP-UC10-003], Then the Cycle Time tab table/bar chart recalculates and displays data only for the selected scope.
- Given the Cycle Time tab is displayed, When the data is rendered per stage (Drafting, Negotiation, Approval, Signature) grouped by user and by contract type, Then each row/group shows Owner Name [DP-UC10-010], Contracts Owned [DP-UC10-011], and Average Cycle Time [DP-UC10-012] as the mean of (stage end date - stage start date) across qualifying contracts per BR-1.
- Given the Cycle Time tab supports cross-navigation to bottleneck detail, When bottleneck-related data for the same contracts is surfaced in this view, Then Current Stage [DP-UC10-013], Days in Current Stage [DP-UC10-014], and Stuck Flag [DP-UC10-015] (Yes/No) are displayed consistent with the tenant-configured thresholds in BR-2.
- Given the Cycle Time tab also exposes turnaround context for the same contracts, When turnaround data is displayed, Then Estimated Turnaround [DP-UC10-016], Actual Turnaround [DP-UC10-017], and Variance [DP-UC10-018] (Actual minus Estimated, red if positive, green if negative or zero per BR-3) are shown, with Estimated Turnaround showing 'Not Set' for contracts excluded from turnaround averages per BR-4.
- Given the reviewer feedback item Change UC10 BR4 to [DP-UC10-020] has been applied, When Estimated Turnaround Days has no target completion date set at Contract Creation, Then the field displays 'Not Set' and the contract is excluded from turnaround averages as revised, and this exclusion is reflected in the Cycle Time tab grouping without breaking the per-stage/user/contract-type aggregation.
- Given role-based visibility rules BR-5, BR-9, BR-10 and BR-11 apply, When a Contract Owner, Legal Reviewer or Approver views the Cycle Time tab, Then only Average Cycle Time, Owner Name, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround and Variance data within their own entitled contracts/stages is visible, while Tenant Admin sees data for all users and contract types.

### View Bottleneck Tab Columns Showing Current Stage, Days in Current Stage, and Stuck Flag (`UC10-GC-003`)
- Given I am logged in with a role permitted to view the Tracker and I navigate to the Bottleneck Tab, When the Bottleneck tab table renders, Then it displays the columns Current Stage, Days in Current Stage, and Stuck Flag for each contract I am entitled to see per BR-5.
- Given the Tracker screen is open, When I review the full set of data points defined for UC10, Then the following named fields and data groups are accounted for across the screen and its tabs: Period, Contract Type Filter, Owner Filter, Date Range From, Date Range To, Owner Name, Contracts Owned, Average Cycle Time, Current Stage, Days in Current Stage, Stuck Flag, Estimated Turnaround, Actual Turnaround, Variance, and Change UC10 BR4 to.
- Given a contract's Days in Current Stage exceeds the tenant-configured threshold for that stage (default 5 days for Drafting and Negotiation, 3 days for Approval and Signature) per BR-2, When the Bottleneck tab table renders that row, Then the Stuck Flag column displays 'Yes'; otherwise it displays 'No'.
- Given the Period dropdown or an applied Date Range filters the dataset per BR-6, When I view the Bottleneck tab, Then the Current Stage and Days in Current Stage values reflect only contracts within the selected Period or Date Range.
- Given I am a Contract Owner, When I view the Bottleneck tab, Then the table is restricted to only contracts I own per BR-9, and I cannot view Current Stage, Days in Current Stage, or Stuck Flag data for contracts owned by other users.
- Given the Bottleneck tab is displayed, When no contracts match the current Period, Contract Type Filter, or Owner Filter selections, Then the table displays an empty state and no Current Stage, Days in Current Stage, or Stuck Flag rows are shown.

### View Turnaround Tab Grid Columns (`UC10-GC-004`)
- Given I am a Contract Owner viewing the Tracker, When I select the Turnaround Tab [F-9], Then the table displays columns for Contract Name, Contract Type, Estimated Turnaround (Days) [F-16/DP-UC10-016], Actual Turnaround (Days) [F-17/DP-UC10-017] and Variance (Days) [F-18/DP-UC10-018] for each contract I own.
- Given the Turnaround tab is displayed, When I inspect the filter and period controls above the grid, Then I can see and use Period [DP-UC10-001], Contract Type Filter [DP-UC10-002], Owner Filter [DP-UC10-003], Date Range From [DP-UC10-004] and Date Range To [DP-UC10-005] to scope the data shown in the table.
- Given a contract's Estimated Turnaround value was set via Contract Creation, When the Variance (Days) column is calculated per BR-3, Then it equals Actual Turnaround minus Estimated Turnaround, is shown in red if positive and green if negative or zero.
- Given a contract has no target completion date set at Contract Creation, When the Estimated Turnaround column is rendered per the current BR-4 rule, Then the field displays "Not Set" and the contract is excluded from turnaround averages, reflecting the documented update 'Change UC10 BR4 to' [DP-UC10-020] governing this exclusion behavior.
- Given the Tracker also provides the Ownership tab and Bottleneck tab, When I navigate away from the Turnaround tab, Then I can still reference related fields such as Owner Name [DP-UC10-010], Contracts Owned [DP-UC10-011], Average Cycle Time [DP-UC10-012], Current Stage [DP-UC10-013], Days in Current Stage [DP-UC10-014] and Stuck Flag [DP-UC10-015] on their respective tabs without them appearing on the Turnaround tab itself.
- Given I am logged in as a Contract Owner, When the Turnaround tab loads, Then only contracts I own are shown in the grid, consistent with BR-9 role-based visibility restrictions.

## Rules

- Do not invent endpoints, routes, DTO fields or table columns beyond what is listed above -- treat this file as the contract for this module.
- Implement every endpoint against the real database via this module's tables/migrations -- no mock/in-memory data (see CLAUDE.md's conventions).
- If a change here would affect another module's existing files, stop and extend shared code instead of rewriting it.
