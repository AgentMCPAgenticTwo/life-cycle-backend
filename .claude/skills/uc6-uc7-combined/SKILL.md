---
name: uc6-uc7-combined
description: Use when building, extending or fixing the 'UC6-UC7-combined' backend module (UC6-UC7-combined). Covers the 20 endpoint(s), 31 DTO(s) and 10 table(s) this module owns, plus its acceptance criteria. Do not use for other modules' endpoints.
---

# UC6-UC7-combined — implementation skill

This skill is generated from the module contract (`db_contract` / `api_contract`) and this epic's BRD stories. It governs WHAT this specific module contains; `CLAUDE.md` at the repo root still governs HOW to build (stack, layering, dependency and error-handling conventions) and wins on any disagreement about style or structure.

## Endpoints to implement (base path: `/api/v1`)

Implement exactly these paths, methods and role lists — the frontend calls them literally.

- `GET /api/v1/approvals` (paged) — roles: APPROVER, TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER; request: `—`; response: `ApprovalListResponse` — List approvals visible to the current user (pending, delegated, or tenant-wide for Tenant Admin), with empty-state when none pending
- `GET /api/v1/approvals/{approvalId}` — roles: APPROVER, TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER; request: `—`; response: `ApprovalResponse` — Get full approval review detail for a contract's current step including all read-only fields and action eligibility flags
- `POST /api/v1/approvals/{approvalId}/actions` — roles: APPROVER; request: `ApprovalActionRequest`; response: `ApprovalActionResponse` — Submit an Approve, Reject, or Send Back action for the current approval step, enforcing sequence, mandatory-comments and ownership rules
- `POST /api/v1/approvals/{approvalId}/delegate` — roles: APPROVER; request: `DelegateRequest`; response: `DelegateResponse` — Assign a time-bound Delegate to act on the Approver's behalf for the current step, validating delegate eligibility, sequence, and ownership
- `GET /api/v1/approvals/{approvalId}/history` (paged) — roles: APPROVER, TENANT_ADMIN, CONTRACT_OWNER, LEGAL_REVIEWER; request: `—`; response: `ApprovalHistoryListResponse` — Retrieve the immutable Approval History tab entries for a contract's approval workflow, retained for 7 years
- `GET /api/v1/approval-matrix-config` — roles: TENANT_ADMIN; request: `—`; response: `ApprovalMatrixConfigListResponse` — Retrieve tenant-configured approval matrix rules by contract type, value, and risk band
- `PUT /api/v1/approval-matrix-config` — roles: TENANT_ADMIN; request: `UpdateApprovalMatrixConfigRequest`; response: `ApprovalMatrixConfigListResponse` — Update tenant-configured approval matrix rules and step sequences
- `GET /api/v1/contracts/{contractId}/signers` — roles: CONTRACT_OWNER, LEGAL_REVIEWER, TENANT_ADMIN; request: `—`; response: `SignerListResponse` — List all signers and their statuses for a contract's e-signature workflow (Signer List tab/grid)
- `POST /api/v1/contracts/{contractId}/signers` — roles: CONTRACT_OWNER; request: `AddSignerRequest`; response: `SignerResponse` — Add a new signer row to the Signer List with mandatory signer fields
- `PUT /api/v1/contracts/{contractId}/signers/{signerId}` — roles: CONTRACT_OWNER; request: `UpdateSignerRequest`; response: `SignerResponse` — Update or reorder a signer; blocked once the first signature has been collected
- `DELETE /api/v1/contracts/{contractId}/signers/{signerId}` — roles: CONTRACT_OWNER; request: `—`; response: `SignerResponse` — Remove a signer from the Signer List; blocked once the first signature has been collected
- `POST /api/v1/contracts/{contractId}/signers/send` — roles: CONTRACT_OWNER; request: `SendForSignatureRequest`; response: `SendForSignatureResponse` — Send for Signature: transition contract to Sent and email the secure link to the first signer(s) in Signing Order
- `GET /api/v1/signing-sessions/{sessionId}` — roles: SIGNER; request: `—`; response: `SigningSessionResponse` — Get the current signer's session state (document, status, eligibility) gated by sequential order and precondition checks
- `POST /api/v1/signing-sessions/{sessionId}/otp/verify` — roles: SIGNER; request: `VerifyOtpRequest`; response: `VerifyOtpResponse` — Verify the signer's 6-digit OTP, revealing the document viewer and Signature Pad on success; locks link after 3 invalid attempts
- `POST /api/v1/signing-sessions/{sessionId}/otp/resend` — roles: SIGNER, CONTRACT_OWNER; request: `—`; response: `SigningSessionResponse` — Re-send a new OTP/signing link after lockout expiry or link expiry
- `POST /api/v1/signing-sessions/{sessionId}/sign` — roles: SIGNER; request: `ApplySignatureRequest`; response: `ApplySignatureResponse` — Apply the signer's signature via the Signature Pad; advances sequence and auto-transitions contract to Executed on the final signature
- `POST /api/v1/signing-sessions/{sessionId}/decline` — roles: SIGNER; request: `DeclineSignatureRequest`; response: `DeclineSignatureResponse` — Decline to sign with a mandatory reason; halts routing and sets contract status to Signature Declined
- `GET /api/v1/contracts/{contractId}/audit-certificate` — roles: CONTRACT_OWNER, LEGAL_REVIEWER; request: `—`; response: `AuditCertificateResponse` — Download the signed audit certificate listing every signer's identity, IP, timestamp, and signing details; available only once Executed
- `GET /api/v1/esignature-settings` — roles: TENANT_ADMIN; request: `—`; response: `EsignatureSettingsResponse` — Get tenant-wide reminder frequency and default signature provider configuration
- `PUT /api/v1/esignature-settings` — roles: TENANT_ADMIN; request: `UpdateEsignatureSettingsRequest`; response: `EsignatureSettingsResponse` — Update tenant-wide reminder frequency (default 3 days) and default signature provider

Enforce the roles above at the framework's authorization layer **and** with the owner/assignment check in business logic. Missing auth header → 401, disallowed role → 403.


## DTOs — request/response types must match these exactly

- **ApprovalResponse** (response): `{ id: uuid, contractId: uuid, contractTitle: string, contractType: string, contractValue: number, counterpartyName: string, keyTermsSummary?: string, deviationsFromStandard?: string, aiRiskScore?: integer, approvalMatrixStepLabel: string, approvalMatrixStepNumber: integer, approvalMatrixTotalSteps: integer, status: string, comments?: string, delegateToUserId?: uuid, delegateToName?: string, delegationStartDate?: date, delegationEndDate?: date, currentApproverId: uuid, currentApproverName: string, isCurrentUserApprover: boolean, isCurrentUserActiveDelegate: boolean, isStepActionable: boolean, canApprove: boolean, canReject: boolean, canSendBack: boolean, canDelegate: boolean, createdAt: datetime, updatedAt: datetime }`
- **ApprovalListItemResponse** (response): `{ id: uuid, contractId: uuid, contractTitle: string, contractType: string, contractValue: number, counterpartyName: string, keyTermsSummary?: string, deviationsFromStandard?: string, aiRiskScore?: integer, approvalMatrixStepLabel: string, status: string }`
- **ApprovalListResponse** (response): `{ items: array, page: integer, pageSize: integer, totalCount: integer, isEmpty: boolean, emptyMessage?: string }`
- **ApprovalActionRequest** (request): `{ actionType: string, comments?: string }`
- **ApprovalActionResponse** (response): `{ approvalId: uuid, status: string, approvalMatrixStepLabel: string, approvalMatrixStepNumber: integer, contractStatus: string }`
- **DelegateRequest** (request): `{ delegateToUserId: uuid, startDate: date, endDate: date }`
- **DelegateResponse** (response): `{ id: uuid, approvalId: uuid, delegateToUserId: uuid, delegateToName: string, startDate: date, endDate: date, createdBy: uuid, createdAt: datetime }`
- **ApprovalHistoryEntryResponse** (response): `{ id: uuid, approvalId: uuid, contractTitle: string, contractType: string, contractValue: number, counterpartyName: string, keyTermsSummary?: string, deviationsFromStandard?: string, aiRiskScore?: integer, approvalMatrixStepLabel: string, action: string, actorId: uuid, actorName: string, actorRole: string, actingAsDelegateForUserId?: uuid, delegateToUserId?: uuid, delegateToName?: string, priorState: string, newState: string, comments?: string, timestamp: datetime }`
- **ApprovalHistoryListResponse** (response): `{ items: array, page: integer, pageSize: integer, totalCount: integer }`
- **ApprovalMatrixStepConfig** (response): `{ stepNumber: integer, approverRole?: string, approverUserId?: uuid, stepName: string }`
- **ApprovalMatrixConfigResponse** (response): `{ id: uuid, contractType: string, valueMin?: number, valueMax?: number, riskBandMin?: integer, riskBandMax?: integer, steps: array }`
- **ApprovalMatrixConfigListResponse** (response): `{ items: array }`
- **UpdateApprovalMatrixConfigRequest** (request): `{ items: array }`
- **SignerResponse** (response): `{ id: uuid, contractId: uuid, signerName: string, signerEmail: string, signerType: string, signingOrder: integer, signatureMethod: string, reminderFrequencyDays?: integer, signerStatus: string, otpVerifiedAt?: datetime, signaturePadCompleted: boolean, ipAddress?: string, signedAt?: datetime, declineReason?: string, linkExpiresAt?: datetime }`
- **SignerListResponse** (response): `{ contractId: uuid, signers: array, sendForSignatureEnabled: boolean, signingOrderLocked: boolean }`
- **AddSignerRequest** (request): `{ signerName: string, signerEmail: string, signerType: string, signingOrder: integer, signatureMethod: string }`
- **UpdateSignerRequest** (request): `{ signerName?: string, signerEmail?: string, signerType?: string, signingOrder?: integer, signatureMethod?: string }`
- **SendForSignatureRequest** (request): `{ signatureMethod?: string }`
- **SendForSignatureResponse** (response): `{ contractId: uuid, contractStatus: string, signers: array, errorMessage?: string }`
- **SigningSessionResponse** (response): `{ sessionId: uuid, contractId: uuid, signerId: uuid, signerName: string, signerEmail: string, signerStatus: string, isCurrentTurn: boolean, otpVerified: boolean, documentUrl?: string, signaturePadAvailable: boolean, declineAvailable: boolean, reminderFrequencyDays?: integer, linkExpired: boolean, blockedMessage?: string }`
- **VerifyOtpRequest** (request): `{ otpCode: string }`
- **VerifyOtpResponse** (response): `{ signerStatus: string, documentUrl?: string, signaturePadAvailable: boolean, attemptsRemaining?: integer, lockedUntil?: datetime, errorMessage?: string }`
- **ApplySignatureRequest** (request): `{ signatureData: string, signatureType: string }`
- **ApplySignatureResponse** (response): `{ signerId: uuid, signerStatus: string, contractStatus: string, nextSignerId?: uuid }`
- **DeclineSignatureRequest** (request): `{ reason: string }`
- **DeclineSignatureResponse** (response): `{ signerId: uuid, signerStatus: string, contractStatus: string, reason: string }`
- **AuditCertificateSignerEntry** (response): `{ signerName: string, signerEmail: string, signerType: string, signingOrder: integer, signatureMethod: string, reminderFrequencyDays?: integer, signerStatus: string, ipAddress?: string, signedAt?: datetime, otpVerifiedAt?: datetime, signaturePadCompleted: boolean }`
- **AuditCertificateResponse** (response): `{ contractId: uuid, generatedAt: datetime, downloadUrl: string, signers: array }`
- **EsignatureSettingsResponse** (response): `{ reminderFrequencyDays: integer, defaultSignatureProvider: string }`
- **UpdateEsignatureSettingsRequest** (request): `{ reminderFrequencyDays?: integer, defaultSignatureProvider?: string }`
- **ErrorResponse** (response): `{ code: string, message: string, timestamp: datetime }`

## Tables (models mirror these)

### `approval_matrix_configs` — Tenant-configured approval matrix rules keyed by contract type, value range and AI risk band
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `contract_type`: VARCHAR(100) (not null)
- `value_min`: NUMERIC(18,2) (nullable)
- `value_max`: NUMERIC(18,2) (nullable)
- `risk_band_min`: INTEGER (nullable)
- `risk_band_max`: INTEGER (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: tenant_id,contract_type

### `approval_matrix_steps` — Ordered steps defined within an approval matrix configuration
- `id`: UUID (not null)
- `config_id`: UUID (not null)
- `step_number`: INTEGER (not null)
- `step_name`: VARCHAR(200) (not null)
- `approver_role`: VARCHAR(100) (nullable)
- `approver_user_id`: UUID (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: config_id,step_number

### `approvals` — Approval workflow instance for a contract, tracking overall status and current step
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `contract_owner_id`: UUID (not null)
- `config_id`: UUID (nullable)
- `current_step_number`: INTEGER (not null)
- `total_steps`: INTEGER (not null)
- `status`: VARCHAR(30) (not null)
- `ai_risk_score`: INTEGER (nullable)
- `key_terms_summary`: TEXT (nullable)
- `deviations_from_standard`: TEXT (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: contract_id, status

### `approval_step_instances` — Per-step instance of an approval, tracking assigned approver, status, and comments for that step
- `id`: UUID (not null)
- `approval_id`: UUID (not null)
- `step_number`: INTEGER (not null)
- `approver_user_id`: UUID (not null)
- `status`: VARCHAR(30) (not null)
- `comments`: TEXT (nullable)
- `acted_by`: UUID (nullable)
- `acted_as_delegate_for`: UUID (nullable)
- `acted_at`: TIMESTAMPTZ (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: approval_id,step_number

### `approval_delegations` — Time-bound delegation assignments allowing a Delegate to act on behalf of an Approver
- `id`: UUID (not null)
- `approval_id`: UUID (not null)
- `approver_user_id`: UUID (not null)
- `delegate_to_user_id`: UUID (not null)
- `start_date`: DATE (not null)
- `end_date`: DATE (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: approval_id, delegate_to_user_id

### `approval_audit_log` — Immutable audit log of every Approve/Reject/SendBack/Delegate action, retained 7 years without hard delete, denormalized with contract/approval context for the Approval History tab
- `id`: UUID (not null)
- `approval_id`: UUID (not null)
- `contract_title`: VARCHAR(500) (not null)
- `contract_type`: VARCHAR(100) (not null)
- `contract_value`: NUMERIC(18,2) (not null)
- `counterparty_name`: VARCHAR(300) (not null)
- `key_terms_summary`: TEXT (nullable)
- `deviations_from_standard`: TEXT (nullable)
- `ai_risk_score`: INTEGER (nullable)
- `approval_matrix_step_label`: VARCHAR(200) (not null)
- `action`: VARCHAR(20) (not null)
- `actor_id`: UUID (not null)
- `actor_role`: VARCHAR(50) (not null)
- `acting_as_delegate_for`: UUID (nullable)
- `delegate_to_user_id`: UUID (nullable)
- `delegate_to_name`: VARCHAR(200) (nullable)
- `prior_state`: VARCHAR(30) (not null)
- `new_state`: VARCHAR(30) (not null)
- `comments`: TEXT (nullable)
- `retention_expires_at`: TIMESTAMPTZ (not null)
- `archived`: BOOLEAN (not null)
- `timestamp`: TIMESTAMPTZ (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: approval_id

### `signers` — Signers configured on a contract's e-signature workflow, their order, status and signing audit details
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `signer_name`: VARCHAR(200) (not null)
- `signer_email`: VARCHAR(320) (not null)
- `signer_type`: VARCHAR(20) (not null)
- `signing_order`: INTEGER (not null)
- `signature_method`: VARCHAR(40) (not null)
- `reminder_frequency_days`: INTEGER (nullable)
- `signer_status`: VARCHAR(20) (not null)
- `otp_hash`: VARCHAR(255) (nullable)
- `otp_attempts`: INTEGER (not null)
- `otp_locked_until`: TIMESTAMPTZ (nullable)
- `otp_verified_at`: TIMESTAMPTZ (nullable)
- `signature_pad_data`: TEXT (nullable)
- `signed_at`: TIMESTAMPTZ (nullable)
- `ip_address`: VARCHAR(64) (nullable)
- `decline_reason`: TEXT (nullable)
- `link_token`: VARCHAR(255) (nullable)
- `link_expires_at`: TIMESTAMPTZ (nullable)
- `last_reminder_sent_at`: TIMESTAMPTZ (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: contract_id,signing_order

### `signature_audit_log` — Immutable event log for each signer's OTP verification and signature capture events, feeding the audit certificate
- `id`: UUID (not null)
- `signer_id`: UUID (not null)
- `contract_id`: UUID (not null)
- `event_type`: VARCHAR(30) (not null)
- `ip_address`: VARCHAR(64) (nullable)
- `details`: TEXT (nullable)
- `timestamp`: TIMESTAMPTZ (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: signer_id, contract_id

### `audit_certificates` — Generated audit certificate record for an executed contract
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `generated_at`: TIMESTAMPTZ (not null)
- `file_url`: VARCHAR(500) (not null)
- `data_snapshot`: JSONB (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: contract_id

### `esignature_settings` — Tenant-wide reminder frequency and default signature provider configuration
- `id`: UUID (not null)
- `tenant_id`: UUID (not null)
- `reminder_frequency_days`: INTEGER (not null)
- `default_signature_provider`: VARCHAR(40) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: tenant_id

## Migrations

Create these with exactly these names, in this order:

- `CreateApprovalMatrixConfigs`
- `CreateApprovalMatrixSteps`
- `CreateApprovals`
- `CreateApprovalStepInstances`
- `CreateApprovalDelegations`
- `CreateApprovalAuditLog`
- `CreateSigners`
- `CreateSignatureAuditLog`
- `CreateAuditCertificates`
- `CreateEsignatureSettings`

Never edit or re-order a migration that already exists — add a new one.


## Acceptance criteria to satisfy

### Review and Act on a Pending Contract Approval (`UC6-MF-001`)
- Given an Approver opens the Approvals list and selects a pending contract, When the Approval Review screen loads, Then it displays Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, and an empty Comments field.
- Given the Approver reviews the Key Terms Summary, Deviations from Standard, and AI Risk Score, When these are displayed, Then they are read-only and labelled "AI Suggestion – for reference only".
- Given the Approver enters Comments and clicks Approve, When Comments is left blank, Then the system accepts the submission since Comments is optional for Approve, records the approval, logs the action, and advances the contract to the next Approval Matrix Step or sets status to "Ready for Signature" and notifies the Contract Owner if it was the last step.
- Given the Approver clicks Reject without entering Comments, When the submission is attempted, Then the system blocks the action and requires Comments to be filled before setting the contract status to "Rejected", logging the action, and notifying the Contract Owner.
- Given the Approver clicks Send Back without entering Comments, When the submission is attempted, Then the system blocks the action and requires Comments to be filled before returning the contract to "In Negotiation" status, logging the action, and notifying the Contract Owner.
- Given the Approver clicks Delegate, When the Approver selects a user in Delegate To and a date range, Then the system reassigns the pending approval action to that delegate for the specified period and logs the delegation.

### Block Out-of-Sequence Approval Attempt (`UC6-AF-001`)
- Given a contract pending approval with a sequential approval matrix showing Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step, when an Approver whose step has not yet been reached attempts to click Approve, Reject, or Send Back, then the system blocks the action and displays the message 'This step is not yet available for approval. Waiting on an earlier approver.'
- Given the Approver's step is not yet active, when the Approval screen is rendered, then the Approve, Reject, and Send Back buttons are disabled for that step per BR-7, and no Comments can be entered for that step.
- Given an earlier Approver's step is still Pending Approval, when the out-of-sequence Approver views the Approval Matrix Step field, then it clearly indicates the current active step (e.g. 'Step 2 of 3 – Finance Approver') so the Approver understands why their action is blocked.
- Given an Approver attempts to use the Delegate To field or the Delegate button for a step not yet reached, when they try to submit a delegated action out of sequence, then the system blocks the attempt with the same 'waiting on an earlier approver' message.
- Given the blocked attempt occurs, when the system rejects the action, then no entry is written to the Approval History tab and no change is made to Comments, AI Risk Score, or any other read-only fields for that contract.

### Block Reject or Send Back submission when Comments are missing (`UC6-AF-002`)
- Given the Approval screen is displaying Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step for the contract at the Approver's current step, when the Approver clicks Reject or Send Back without entering text in Comments, then the system displays 'Comments are required when rejecting or sending back a contract.' and does not submit the action.
- Given the Approver has left Comments empty and clicks Reject, when the submission is blocked, then the contract's Approval Matrix Step and status remain unchanged and no entry is written to the Approval History tab.
- Given the Approver has left Comments empty and clicks Send Back, when the submission is blocked, then the contract remains at the current Approval Matrix Step and is not returned to Negotiation.
- Given the error message is displayed, when the Approver subsequently enters text into Comments and clicks Reject or Send Back again, then the action is accepted and processed per BR-21 or BR-22.
- Given the Approver has delegated authority via Delegate To, when the active Delegate clicks Reject or Send Back without entering Comments, then the same blocking message is displayed and the action is not submitted.
- Given read-only fields Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step, when the validation error is shown, then none of these fields are altered or editable as a result of the blocked submission.

### Deny access to Approval Review screen for unauthorized users (`UC6-AF-003`)
- Given a user does not hold the Approver or Delegate role for the current approval step, When they attempt to open the Approval Review screen, Then the system displays 'You do not have permission to approve this contract.' and denies access.
- Given access is denied, When the screen fails to load for the unauthorized user, Then none of the contract's data points — Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To — are rendered or exposed to that user.
- Given access is denied, When the attempt is made, Then no Approve, Reject, Send Back, or Delegate action is available to the user and no Comments can be entered.
- Given an active Delegate for the relevant Approver attempts to open the screen, When their delegation window is currently valid, Then access is granted rather than denied.

### Detect and Refresh Stale Approval State on Concurrent Action Conflict (`UC6-AF-004`)
- Given an Approver has a contract open on the Approval screen and another concurrent session has already fully Approved, Rejected, or Sent Back the same contract, When the Approver attempts to submit an Approve, Reject, Send Back, or Delegate action, Then the system blocks the action and displays the message 'This contract's approval status has changed. Please refresh to see the latest status.'
- Given the conflict message has been displayed, When the system reloads the current state, Then the Approval screen refreshes to display the latest values for Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step, reflecting the outcome recorded by the concurrent session
- Given the state has been reloaded after a conflict, When the Approver reviews the Comments field, Then any previously entered but unsubmitted Comments are discarded and the field is cleared or repopulated only with the actual persisted comments for the current approval step
- Given the state has been reloaded after a conflict and the Approver had opened the Delegate option, When the refreshed state loads, Then the Delegate To selection is cleared if the step is no longer actionable by this Approver, consistent with the new approval status
- Given the contract was fully approved, rejected, or sent back by another session, When the state reloads, Then the Approve, Reject, Send Back, and Delegate controls are disabled or hidden as appropriate to the new status, preventing further duplicate actions on a stale step

### Block Delegate Assignment for Ineligible User (`UC6-AF-005`)
- Given the Approval screen displays the contract's Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments and Delegate To fields, When the Approver clicks Delegate to assign a Delegate, Then the Delegate To dropdown lists selectable users.
- Given the Approver selects a user in the Delegate To dropdown who does not hold the Approver role in the tenant, When the Approver attempts to confirm the delegation, Then the system displays the message 'Selected user is not an eligible Approver and cannot be set as delegate.' and the delegation is not saved.
- Given the delegation attempt was rejected due to an ineligible user, When the Approver views the Approval screen, Then the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step and Comments remain unchanged and the Delegate To field is cleared or reset for re-selection.
- Given the error message is displayed, When the Approver selects a different user in the Delegate To dropdown who does hold the Approver role, Then the system allows the delegation to proceed.

### Display empty-state message when no contracts await approver action (`UC6-AF-006`)
- Given the logged-in Approver has no contracts assigned to them at their current pending step, When they navigate to the Approvals list, Then the system displays 'No contracts are currently awaiting your approval.' instead of a contract list.
- Given the Approvals list is empty, When the empty-state message is displayed, Then no contract rows showing Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, or Delegate To are rendered.
- Given a contract later becomes pending the Approver's action, When the Approvals list is refreshed or reloaded, Then the empty-state message is replaced by the contract entry showing its Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step.
- Given the Approver is acting as an active Delegate with no delegated contracts currently pending, When they view the Approvals list, Then the same empty-state message is shown.

### Block Progression to E-signature Until All Approval Steps Are Approved (`UC6-BR-001`)
- Given a contract is in the approval workflow displaying Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step, When one or more steps in the configured approval matrix are not yet marked Approved, Then the system must not transition the contract to E-signature (UC7) and the Approval Matrix Step field must reflect the current incomplete step.
- Given the Approver reviews a contract at its current Approval Matrix Step, When the Approver attempts to trigger progression to E-signature before all steps are Approved, Then the system blocks the transition and displays the pending steps remaining.
- Given all steps in the configured approval matrix, including any step completed via a Delegate selected through Delegate To, have been marked Approved, When the final step is approved, Then the system automatically transitions the contract to Ready for Signature and triggers E-signature (UC7).
- Given an Approver submits an Approve, Reject, or Send Back action with Comments entered as required, When the action is recorded, Then the Comments field is validated and stored alongside the Approval Matrix Step before any evaluation of overall matrix completion is performed.
- Given the contract's full set of approval-related data points (Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, Delegate To) is displayed to the Approver, When the approval matrix is not fully Approved, Then the E-signature transition control remains unavailable regardless of the values of these read-only or display-only fields.

### Configure tenant-based approval matrix rules (`UC6-BR-002`)
- Given a contract has completed Negotiation & Routing (UC5), When it is submitted into the approval matrix, Then the sequence of required approval roles/users is determined by tenant-configured rules based on Contract Type and Contract Value.
- Given a contract has an AI Risk Score, When the approval matrix is evaluated, Then the AI risk score band is used alongside Contract Type and Contract Value to determine the required approval steps and sequence.
- Given an Approver is viewing a contract pending approval, When the Approval screen is displayed, Then it shows the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step as determined by the configured matrix.
- Given a contract is at a given step in the configured matrix, When an action is taken, Then the Comments field is captured per the matrix-defined step and recorded against that Approval Matrix Step.
- Given a Tenant Admin wants to delegate approval configuration review, When the matrix is set up, Then the Delegate To field and assignments respect the roles/users defined in the tenant-configured approval matrix rules.
- Given the approval matrix rules are configured in Settings (UC11), When a Tenant Admin updates contract type, value or risk band thresholds, Then subsequently routed contracts use the updated rules to determine approvers and sequence.

### Require Comments When Rejecting or Sending Back a Contract (`UC6-BR-003`)
- Given the Approval screen is displaying Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step for a contract pending my decision, when I select Reject without entering any text in Comments, then the system blocks submission and displays a validation error indicating Comments is mandatory for this action.
- Given the Approval screen is displaying Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step for a contract pending my decision, when I select Send Back without entering any text in Comments, then the system blocks submission and displays a validation error indicating Comments is mandatory for this action.
- Given I have selected Reject or Send Back, when I enter text into Comments and submit, then the system accepts the submission and records the Comments against the contract's approval history.
- Given I instead choose to Delegate using Delegate To, when no action (Reject or Send Back) is being submitted, then Comments is not required to proceed with configuring the delegation.

### Submit Approval Without Mandatory Comments (`UC6-BR-004`)
- Given an Approver is viewing a contract at their Approval Matrix Step, with Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, and AI Risk Score displayed for reference, When the Approver selects Approve and leaves the Comments field blank, Then the system accepts the submission and does not block progression for missing Comments.
- Given the Approver chooses to add free-text input in Comments while approving, When they click Approve with Comments populated, Then the system accepts both the Comments and the Approve action and records them together.
- Given the Approver has not delegated the approval and is acting directly, When they submit Approve with Comments left empty, Then the transition to the next Approval Matrix Step (or to Ready for Signature) proceeds without validation errors related to Comments.
- Given an active Delegate selected via Delegate To is acting on behalf of the Approver, When the Delegate submits Approve without entering Comments, Then the system accepts the approval, since Comments remain optional for the Approve action regardless of whether the actor is the Approver or an active Delegate.

### Reset Approval Sequence on Send Back (`UC6-BR-005`)
- Given a contract is in Pending Approval status displaying its Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step, When the Approver clicks Send Back without entering Comments, Then the system blocks the action and requires Comments to be entered before submission.
- Given the Approver enters Comments and clicks Send Back, When the action is submitted, Then the contract status changes to 'In Negotiation' (UC5) and the current Approval Matrix Step value is reset.
- Given a contract previously had one or more steps marked Approved, When a Send Back action is submitted for that contract, Then all prior approvals on that contract are cleared and the approval sequence restarts from the first step upon re-routing.
- Given a contract is sent back and subsequently re-routed through Negotiation, When it re-enters the approval workflow, Then approvals must be re-obtained at every step of the Approval Matrix Step sequence, including any step previously completed by a Delegate selected via Delegate To.
- Given a Send Back action is performed, When the transition occurs, Then the Comments, Approval Matrix Step, and resulting 'In Negotiation' status are recorded in the Approval History.

### Reject Contract and Terminate Approval Workflow (`UC6-BR-006`)
- Given a contract is displayed for approval showing Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step, When the Approver selects Reject, Then the Comments field is mandatory and the action cannot be submitted without Comments being entered.
- Given the Approver enters Comments and submits Reject, When the rejection is processed, Then the contract status is set to 'Rejected' and the approval workflow ends, with the Comments, Approval Matrix Step, and AI Risk Score recorded on the approval record.
- Given a contract has status 'Rejected', When any Approver or Delegate attempts to take a further approval action (Approve, Reject, or Send Back) on that contract, Then the system blocks the action because the workflow is terminal.
- Given a contract has status 'Rejected', When the Contract Owner views the contract, Then no approval action is available and the only path forward is for the Contract Owner to create a new version of the contract.
- Given the Approver has delegated their authority via Delegate To, When the active Delegate performs the Reject action with Comments, Then the same rejection rule applies: contract status becomes 'Rejected' and the workflow is terminated.
- Given the contract detail view during rejection, When the Approver reviews the displayed fields, Then Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To are all present and consistent with the rejected state.

### Disable Approval Actions for Unreached Sequential Steps (`UC6-BR-007`)
- Given a contract in a sequential approval matrix where one or more earlier steps are not yet Approved, When the current Approver views the approval screen showing Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To, Then the Approve, Reject, and Send Back buttons are disabled for that Approver's step.
- Given all earlier sequential steps are marked Approved, When the Approver whose step has now been reached views the Approval Matrix Step indicator, Then the Approve, Reject, and Send Back buttons become enabled for their step.
- Given an Approver attempts to submit an Approve, Reject, or Send Back action on a step that has not yet been reached, When the action is submitted (e.g., via a direct request bypassing the disabled UI), Then the system blocks the transition and returns an error indicating an earlier sequential step is incomplete.
- Given the approval screen is displayed for a not-yet-reached step, When the Approver reviews the read-only fields Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, and AI Risk Score, Then these fields remain viewable but no Comments can be entered and no Delegate To selection can be acted upon to approve, reject, or send back.

### Set time-bound delegation for approval actions (`UC6-BR-008`)
- Given an Approver is viewing an assigned contract with Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step displayed, when the Approver selects Delegate and chooses a Delegate To value along with a start and end date, then the delegation is saved as time-bound and the Delegate gains approval rights only within that window.
- When the delegation start and end date window is active and the Delegate takes an Approve, Reject, or Send Back action (entering Comments where required by BR-3), then the action is logged against both the Delegate and the original Approver.
- Given the current date falls outside the configured start and end date window, when the Delegate attempts to act on the contract, then the system blocks the action as the delegation is not active.
- Given a Delegate action is logged, when the Approval History tab is reviewed, then it shows the action attributed to both the Delegate and the original Approver, along with timestamp and any Comments entered.
- Given the Delegate To field is only visible when the Approver selects Delegate, when the Approver has not selected Delegate, then no delegation start/end date fields or Delegate To dropdown are shown.

### View AI Risk Score and Deviations as read-only reference information (`UC6-BR-009`)
- Given an approval record is displayed with Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To, When the Approver views the AI Risk Score and Deviations from Standard fields, Then both fields are rendered as read-only and cannot be edited by the Approver.
- Given the AI Risk Score field is displayed, When the Approver views it, Then it is labelled 'AI Suggestion – for reference only' to indicate it is advisory and not a binding system decision.
- Given the Deviations from Standard field is displayed, When the Approver views it, Then it is labelled 'AI Suggestion – for reference only' and shown alongside the Approval Matrix Step, Key Terms Summary, Contract Value, Contract Type, Counterparty Name, and Contract Title for full context.
- Given an AI Risk Score of any value and any listed Deviations from Standard, When the Approver attempts to Approve, Reject, or Send Back (with mandatory Comments where required) or set a Delegate To, Then the AI Risk Score and Deviations values do not themselves block or allow progression of the approval action.
- Given the Approver attempts to directly edit the AI Risk Score or Deviations from Standard fields, When the attempt is made, Then the system prevents the edit and no input controls are available for these fields.

### Log all approval actions to the immutable audit trail (`UC6-BR-010`)
- Given an Approver or active Delegate is viewing a contract showing Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score and Approval Matrix Step, When the Approver clicks Approve with optional Comments, Then an immutable audit log entry is created recording the user, timestamp, action (Approve) and Comments.
- Given an Approver or active Delegate is reviewing a contract, When the Approver clicks Reject and enters mandatory Comments, Then an immutable audit log entry is created recording the user, timestamp, action (Reject) and Comments.
- Given an Approver or active Delegate is reviewing a contract, When the Approver clicks Send Back and enters mandatory Comments, Then an immutable audit log entry is created recording the user, timestamp, action (Send Back) and Comments.
- Given an Approver selects Delegate and chooses a Delegate To user for a defined date range, When the Delegate To selection is confirmed, Then an immutable audit log entry is created recording the user, timestamp, action (Delegate) and Comments (if any).
- Given a Delegate performs an Approve, Reject or Send Back action during the delegation window, When the action is submitted, Then the audit log entry is created recording both the Delegate and the original Approver as the user along with timestamp, action and Comments.
- Given any of the above audit log entries has been written, When a user attempts to edit or delete it, Then the system prevents the change, confirming the log entry is immutable.

### Prevent Contract Owner from approving their own contract (`UC6-BR-011`)
- Given a contract is Pending Approval and the logged-in user is the Contract Owner who created it, When that user attempts to access the Approval screen for the contract, Then the system must prevent the Contract Owner from being assigned or acting as Approver on their own contract, regardless of Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, or Delegate To values displayed.
- Given the Contract Owner is listed in the tenant's approval matrix for a contract type/value/risk band, When the system assigns Approvers for that contract's Approval Matrix Step, Then the Contract Owner must be excluded from the list of eligible Approvers and Delegate To options for that contract.
- Given the Contract Owner attempts to submit an Approve, Reject, or Send Back action with Comments on a contract they created, When the action is submitted, Then the system must reject the submission and display an error indicating the Contract Owner cannot approve their own contract.
- Given an Approver sets a Delegate via the Delegate To field for a contract, When the selected Delegate is the Contract Owner of that contract, Then the system must prevent this Delegate assignment and display an error.

### Record full audit detail for each approve/reject action (`UC6-BR-012`)
- Given an Approver is viewing a contract at Approval Matrix Step with its Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, and AI Risk Score displayed, When the Approver submits an Approve, Reject, or Send Back action, Then the system records the actor, timestamp, role, prior state, and new state for that action.
- Given the Approver enters text into Comments (mandatory for Reject or Send Back, optional for Approve), When the action is submitted, Then the entered Comments text is persisted alongside the recorded actor, timestamp, role, prior state, and new state.
- Given a Delegate acts on behalf of an Approver using the Delegate To assignment, When the Delegate submits an approve/reject action, Then the record captures the actor as the Delegate, the role, timestamp, prior state, new state, and any Comments, consistent with BR-8 logging against both Delegate and original Approver.
- Given a recorded approve/reject action, When viewed in Approval History, Then the Contract Title, Contract Type, Contract Value, Counterparty Name, Approval Matrix Step, actor, role, timestamp, prior state, new state, and Comments are all visible and none are editable after the fact.

### Retain approval audit records for seven years without hard deletion (`UC6-BR-013`)
- Given an approval audit record exists for a contract containing Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To (where applicable), When the record is created, Then it is stored in the immutable audit log and retained for a minimum of 7 years from the date of creation.
- Given an approval audit record is within its 7-year retention period, When a Tenant Admin or any other user attempts to permanently delete the record, Then the system blocks the hard-delete action and only allows the record to be marked inactive/archived.
- Given an approval audit record has reached or passed the end of its 7-year retention period, When a retention review or archival process runs, Then the record is marked inactive/archived rather than being physically removed from the system.
- Given an archived/inactive approval audit record, When a Tenant Admin views the Approval History tab, Then the full log of status changes along with Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To remains viewable and is not lost.
- Given a status change occurs on a contract's approval workflow (e.g., Approve, Reject, Send Back, Delegate), When the change is logged, Then the audit record capturing that status change is subject to the same 7-year retention and no-hard-delete rule as all other approval audit records.

### View assigned contract details and act with Approve, Reject, Send Back or Delegate (`UC6-BR-014`)
- Given a contract assigned to me for approval, When I open the approval screen, Then I can view the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, and any prior Comments, all as read-only display fields.
- Given I am viewing an assigned contract, When I review the AI Risk Score and Deviations from Standard, Then these fields are read-only and I cannot edit them or change the configured approval matrix.
- Given an assigned contract at my step, When I choose to Approve, Then I may optionally enter Comments and submit, and the contract proceeds per the approval matrix.
- Given an assigned contract at my step, When I choose to Reject or Send Back, Then I am required to enter Comments before the action can be submitted, otherwise the action is blocked.
- Given I need another user to act on my behalf, When I select Delegate and choose a Delegate To user with a start and end date, Then that Delegate gains my Approve/Reject/Send Back rights for the specified period.
- Given I attempt to edit contract content fields such as Key Terms Summary or Deviations from Standard, When I try to modify them, Then the system prevents the edit, confirming these remain display-only for the Approver.

### Act as Delegate with Full Approval Rights but No Further Delegation (`UC6-BR-015`)
- Given I am an active Delegate for an Approver within the delegated period, when I open a contract assigned to that Approver, then I can view the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step exactly as the Approver would see them.
- Given I am an active Delegate, when I view the approval actions, then I have the same Approve, Reject and Send Back rights as the delegating Approver for the current Approval Matrix Step.
- Given I choose to Reject or Send Back as a Delegate, when I submit the action, then entering Comments is mandatory and the action is blocked until Comments are provided.
- Given I choose to Approve as a Delegate, when I submit the action, then Comments are optional.
- Given I am acting as a Delegate, when I view the Delegate To field or Delegate action, then I am not permitted to delegate my own access further to another user, and the option to do so is unavailable to me.
- Given my delegation period has ended, when I attempt to Approve, Reject or Send Back a contract, then the action is blocked because I am no longer an active Delegate.

### Configure approval matrix and view tenant-wide approvals without acting unless named Approver (`UC6-BR-016`)
- Given I am a Tenant Admin in Settings, When I configure the approval matrix, Then I can define rules based on Contract Type, Contract Value and risk thresholds for routing contracts.
- Given I am a Tenant Admin viewing the tenant-wide approvals list, When I open a pending or completed approval record, Then I can view its Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and any Delegate To assignment.
- Given I am a Tenant Admin who is not assigned as a named Approver on a contract, When I view that contract's approval screen, Then the Approve, Reject and Send Back actions are disabled or unavailable to me.
- Given I am a Tenant Admin who is also assigned as a named Approver for a specific contract, When I act on that contract's pending approval step, Then I am permitted to Approve, Reject or Send Back using the Comments field as required by the action type.
- Given I am a Tenant Admin viewing a contract I am not assigned to approve, When I review the Approval Matrix Step and Delegate To fields, Then they are presented as read-only information without any action controls enabled.

### View Read-Only Approval Status for Own Contracts (`UC6-BR-017`)
- Given a Contract Owner is logged in and viewing one of their own contracts in the Approval screen, When the screen loads, Then the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, and Comments are all displayed in read-only form.
- Given a Contract Owner is viewing their own contract's approval status, When the screen renders the available actions, Then the Approve, Reject and Send Back buttons are not present or are disabled for the Contract Owner.
- Given a Contract Owner is viewing their own contract's approval status, When the screen renders delegation controls, Then the Delegate To field and Delegate button are not visible or usable to the Contract Owner.
- Given a Contract Owner attempts to submit an Approve, Reject or Send Back action via a direct request, When the system processes the request, Then the action is rejected and the contract's approval state remains unchanged.
- Given a Contract Owner is viewing the Approval History tab for their own contract, When they open it, Then prior decisions, timestamps and Comments are shown but no editable action controls are available.

### View read-only approval details as Legal Reviewer without approval actions (`UC6-BR-018`)
- Given a Legal Reviewer is logged in and viewing a contract in the approval workflow, When the Approval screen loads, Then the Legal Reviewer can see the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, and Comments fields in read-only form.
- Given a Legal Reviewer is viewing the Approval screen, When the screen renders, Then the Approve, Reject, and Send Back buttons are not available or are disabled for the Legal Reviewer.
- Given a Legal Reviewer is viewing the Approval screen, When the screen renders, Then the Delegate To dropdown and Delegate action are not available to the Legal Reviewer, as delegation is reserved for Approvers.
- Given a Legal Reviewer attempts to submit an Approve, Reject, or Send Back action via direct API call or URL manipulation, When the request is processed, Then the system rejects the action and no change is made to the approval status.
- Given a Legal Reviewer is viewing a contract, When they inspect the Deviations from Standard and Comments sections, Then both are displayed exactly as entered by the Approver/Delegate without edit controls being presented.

### Block External Party and Signer from Accessing Approval Screen (`UC6-BR-019`)
- Given a contract is in the Approval stage (UC6) displaying Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To, When an External Party attempts to navigate to the Approval screen, Then access is denied and none of these fields are rendered or returned to the External Party.
- Given a contract is in the Approval stage (UC6), When a Signer attempts to navigate to the Approval screen, Then access is denied and the Signer cannot view Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, or Delegate To.
- Given an External Party or Signer is authenticated in the system, When they attempt to directly request the Approval screen URL or API endpoint, Then the system returns an access-denied response without exposing any Approval screen data or controls.
- Given the Approval screen exposes Approve, Reject, Send Back, and Delegate actions, When an External Party or Signer attempts to invoke any of these actions, Then the action is rejected due to lack of Approval screen access.

### Approve pending approval step with required validations (`UC6-BR-020`)
- Given a contract is in Pending Approval status at the current step, displaying Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step, When the assigned Approver or an active Delegate clicks Approve, Then the contract transitions to Approved for that step provided no required field is missing Comments and all earlier sequential steps are already complete.
- Given the Approver attempts to Approve but a required field is missing Comments, When the Approve action is submitted, Then the transition is blocked and an error is shown indicating Comments are required.
- Given the approval matrix is sequential and an earlier step has not yet been marked Approved, When an Approver or Delegate at a later step attempts to Approve, Then the transition is blocked and the Approve action remains disabled until the earlier step completes.
- Given an active Delegate is acting within their delegated window, When the Delegate clicks Approve with the Comments field (if populated) and Delegate To value correctly attributed, Then the transition to Approved is permitted exactly as if performed by the assigned Approver, and the action is logged against both the Delegate and the original Approver.
- Given the user is neither the assigned Approver nor an active Delegate, When they attempt to Approve, Then the transition is blocked regardless of the state of Comments, Approval Matrix Step, or other displayed fields such as AI Risk Score.

### Reject a Contract Pending Approval with Mandatory Comments (`UC6-BR-021`)
- Given a contract is in Pending Approval status and assigned to me as Approver (or I am the active Delegate for that Approver), When I review the contract's Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step, Then these fields are displayed read-only for my reference before I act.
- Given I am the assigned Approver or active Delegate for the current Approval Matrix Step, When I click Reject without entering text in the Comments field, Then the system blocks the submission and displays a validation error indicating Comments are mandatory for a Reject action.
- Given I am the assigned Approver or active Delegate, When I enter text into the Comments field and click Reject, Then the contract status transitions from Pending Approval to Rejected.
- Given a contract has transitioned to Rejected, When any user views the contract, Then the Rejected status is shown as a terminal state and no further Approve, Reject, Send Back or Delegate actions are available on the current version.
- Given a contract is Rejected, When an attempt is made to progress the approval workflow (e.g. advance the Approval Matrix Step), Then the system prevents further approval action and requires the Contract Owner to create a new version before the workflow can resume.
- Given a contract is acted upon by a Delegate using the Delegate To assignment, When the Delegate rejects the contract with Comments, Then the Reject transition and Comments are recorded as performed by the Delegate on behalf of the delegating Approver.

### Send a contract back to negotiation with mandatory comments (`UC6-BR-022`)
- Given a contract is in Pending Approval status and I am the assigned Approver or an active Delegate, when I view the approval screen, then I see the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step displayed for reference.
- Given I am viewing a contract in Pending Approval status, when I select Send Back without entering Comments, then the system blocks the transition and prompts me to enter Comments before proceeding.
- Given I am the assigned Approver or an active Delegate for the contract, when I enter Comments and select Send Back, then the contract status transitions to 'In Negotiation' (UC5) and the Comments are recorded against the transition.
- Given I select Delegate To for an active delegation, when the Delegate performs the Send Back action with Comments, then the transition is permitted the same as for the original Approver, and the action is logged against both the Delegate and the Approver.
- Given a contract has been Sent Back to Negotiation, when the transition completes, then any prior approval sequence progress is reset as defined in BR-5.
- Given I am not the assigned Approver or an active Delegate for the contract, when I attempt to select Send Back, then the action is not permitted.

### Automatically advance contract to next sequential approval step (`UC6-BR-023`)
- Given the current approval screen shows Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and Approval Matrix Step for a contract at an Approved step, When the Approver reviews this data and the matrix has further sequential steps remaining, Then the contract automatically transitions from Approved (current step) to Pending Approval (next step) without requiring any additional action from the Approver.
- Given the Approver has submitted an Approve action on the current step with optional Comments entered, When the matrix configuration indicates another sequential step follows, Then the system automatically updates the Approval Matrix Step label to reflect the next step (e.g. advancing from 'Step 2 of 3' to 'Step 3 of 3') and sets the status to Pending Approval for the newly assigned Approver or Delegate To.
- Given a contract has just transitioned automatically to Pending Approval for the next step, When the next assigned Approver opens the contract, Then they can view the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, and prior step's Comments, and the Delegate To field remains available if they choose to delegate.
- Given the matrix has no further sequential steps after the current Approved step, When the Approver approves, Then the automatic transition to Pending Approval does not occur, and instead the contract proceeds per BR-24 toward Ready for Signature.

### Automatically transition fully approved contract to Ready for Signature (`UC6-BR-024`)
- Given a contract's approval screen displays Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To, when every configured approval step shows status Approved, then the contract automatically transitions to Ready for Signature and UC7 (E-signature) is triggered.
- Given at least one configured approval step is not yet marked Approved, when the system evaluates the overall approval status, then the transition to Ready for Signature is blocked and the contract remains in its current Pending Approval or Approved (current step) status.
- Given the final approval step has just been Approved by an Approver, when the system checks that no earlier or later configured step remains unapproved, then the Ready for Signature transition occurs automatically without requiring any further user action.
- Given the contract has transitioned to Ready for Signature, when the Contract Owner views the Approval Matrix Step field, then it reflects that all steps are complete and UC7 has been initiated.
- Given the transition to Ready for Signature has occurred, when the audit log is reviewed, then the automatic transition event is recorded alongside the prior approval actions, comments, and the data shown on the approval screen (Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, Delegate To).

### View Approval Review Screen Fields (`UC6-FV-001`)
- Given a contract is pending my approval, When I open the Approval Review screen, Then I see the Contract Title, Contract Type, Contract Value, Counterparty Name, Key Terms Summary, Deviations from Standard, AI Risk Score, Approval Matrix Step, Comments, and Delegate To fields as applicable to the current step.
- Given the Approval Review screen is displayed, When I inspect the Contract Title, Contract Type, Contract Value, and Counterparty Name fields, Then each is shown as read-only display data sourced from the contract header and cannot be edited.
- Given the Approval Review screen is displayed, When I inspect the Key Terms Summary and Deviations from Standard fields, Then each is shown as a read-only text area populated from the routing (UC5) output and the template comparison respectively.
- Given the Approval Review screen is displayed, When I view the AI Risk Score, Then it is shown as a whole number between 0 and 100, labelled 'AI Suggestion', and is read-only.
- Given the Approval Review screen is displayed, When I view the Approval Matrix Step, Then it shows my current position in the sequence, e.g. 'Step 2 of 3 – Finance Approver'.
- Given I select Reject or Send Back without entering text in the Comments field, When I submit the action, Then the system blocks submission and requires Comments to be completed before proceeding.
- Given I select Approve, When I submit the action without entering Comments, Then the system accepts the submission because Comments are optional for Approve.
- Given I select Delegate, When the Delegate panel opens, Then the Delegate To dropdown becomes visible for me to select a delegate along with a date range.

## Rules

- Do not invent endpoints, routes, DTO fields or table columns beyond what is listed above -- treat this file as the contract for this module.
- Implement every endpoint against the real database via this module's tables/migrations -- no mock/in-memory data (see CLAUDE.md's conventions).
- If a change here would affect another module's existing files, stop and extend shared code instead of rewriting it.
