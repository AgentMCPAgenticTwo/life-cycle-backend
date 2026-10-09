---
name: lifecycle-uc4-uc5
description: Use when building, extending or fixing the 'lifecycle uc4 uc5' backend module (lifecycle uc4 uc5). Covers the 19 endpoint(s), 30 DTO(s) and 10 table(s) this module owns, plus its acceptance criteria. Do not use for other modules' endpoints.
---

# lifecycle uc4 uc5 — implementation skill

This skill is generated from the module contract (`db_contract` / `api_contract`) and this epic's BRD stories. It governs WHAT this specific module contains; `CLAUDE.md` at the repo root still governs HOW to build (stack, layering, dependency and error-handling conventions) and wins on any disagreement about style or structure.

## Endpoints to implement (base path: `/api/v1/lifecycle`)

Implement exactly these paths, methods and role lists — the frontend calls them literally.

- `GET /api/v1/lifecycle/contracts/{contractId}/clause-analysis` — roles: LEGAL_REVIEWER, CONTRACT_OWNER, TENANT_ADMIN; request: `—`; response: `ClauseAnalysisResponse` — Retrieve AI-extracted clauses, risk scores, mandatory flags and contract metadata for the Clause Analysis screen
- `POST /api/v1/lifecycle/contracts/{contractId}/clauses/{clauseId}/accept-suggestion` — roles: LEGAL_REVIEWER, CONTRACT_OWNER; request: `—`; response: `ClauseResponse` — Accept the AI-suggested text for a clause, replacing current text and logging the action
- `PUT /api/v1/lifecycle/contracts/{contractId}/clauses/{clauseId}` — roles: LEGAL_REVIEWER; request: `EditClauseRequest`; response: `ClauseResponse` — Save a manual rewrite of a clause via the Clause Edit Box; blocked on stale version per concurrency check
- `POST /api/v1/lifecycle/contracts/{contractId}/clauses/{clauseId}/reject` — roles: LEGAL_REVIEWER; request: `RejectClauseRequest`; response: `ClauseResponse` — Reject a clause suggestion, logging user, timestamp and before/after text
- `PUT /api/v1/lifecycle/contracts/{contractId}/metadata` — roles: LEGAL_REVIEWER, CONTRACT_OWNER; request: `UpdateMetadataRequest`; response: `ContractMetadataResponse` — Update AI-extracted contract metadata fields; relabels edited fields as User-confirmed
- `POST /api/v1/lifecycle/contracts/{contractId}/ask-ai` — roles: LEGAL_REVIEWER, CONTRACT_OWNER; request: `AskAIRequest`; response: `AskAIResponse` — Submit a free-text question about the contract and receive an AI answer with verification disclaimer
- `POST /api/v1/lifecycle/contracts/{contractId}/proceed-to-negotiation` — roles: LEGAL_REVIEWER, CONTRACT_OWNER; request: `—`; response: `ProceedToNegotiationResponse` — Finalize clause set and metadata and route the contract to Negotiation & Routing (UC5), blocked if mandatory clauses remain missing
- `POST /api/v1/lifecycle/contracts/{contractId}/retry-extraction` — roles: LEGAL_REVIEWER, CONTRACT_OWNER; request: `—`; response: `ClauseAnalysisResponse` — Retry AI clause extraction after a failure or timeout
- `GET /api/v1/lifecycle/contracts/{contractId}/audit-log` (paged) — roles: LEGAL_REVIEWER, CONTRACT_OWNER, TENANT_ADMIN; request: `—`; response: `PagedAuditLogResponse` — Retrieve the immutable audit trail of Accept/Edit/Reject/Metadata/AskAI actions for a contract
- `POST /api/v1/lifecycle/contracts/{contractId}/negotiation/routing` — roles: CONTRACT_OWNER; request: `RoutingRequest`; response: `RoutingResponse` — Configure routing (type, reviewers, external party, dates) and submit a Draft contract for internal/external review, creating Version 1
- `GET /api/v1/lifecycle/contracts/{contractId}/negotiation` — roles: CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER, TENANT_ADMIN; request: `—`; response: `NegotiationTrackerResponse` — Retrieve the negotiation tracker: routing config, reviewers, status, current version, overdue flag, version history and comments
- `POST /api/v1/lifecycle/contracts/{contractId}/negotiation/reviews` — roles: LEGAL_REVIEWER, APPROVER; request: `SubmitReviewRequest`; response: `SubmitReviewResponse` — Submit an internal reviewer's redline/comment, incrementing the version and routing to next reviewer or external party
- `POST /api/v1/lifecycle/contracts/{contractId}/negotiation/external-link` — roles: CONTRACT_OWNER, LEGAL_REVIEWER; request: `—`; response: `GenerateExternalLinkResponse` — Generate a secure OTP-protected link for the external party once internal review completes
- `POST /api/v1/lifecycle/negotiation/external/{linkToken}/verify-otp` — roles: EXTERNAL_PARTY; request: `VerifyOtpRequest`; response: `VerifyOtpResponse` — Verify the OTP for an external party secure link; locks link after three failed attempts
- `POST /api/v1/lifecycle/negotiation/external/{linkToken}/submit` — roles: EXTERNAL_PARTY; request: `ExternalSubmitRequest`; response: `ExternalSubmitResponse` — External party submits redlines/comments on the current version; triggers AI clause analysis and reverts status to With Internal
- `GET /api/v1/lifecycle/contracts/{contractId}/negotiation/compare` — roles: CONTRACT_OWNER, LEGAL_REVIEWER, APPROVER; request: `—`; response: `CompareVersionsResponse` — Return a side-by-side redline comparison between two selected prior versions of the same contract and tenant
- `POST /api/v1/lifecycle/contracts/{contractId}/negotiation/reminder` — roles: CONTRACT_OWNER; request: `—`; response: `ReminderResponse` — Send a manual reminder email to an overdue reviewer; supplements the automatic daily reminder
- `POST /api/v1/lifecycle/contracts/{contractId}/negotiation/mark-agreed` — roles: LEGAL_REVIEWER; request: `—`; response: `MarkAgreedResponse` — Legal Reviewer explicitly marks negotiation as Agreed after at least one full review cycle
- `POST /api/v1/lifecycle/contracts/{contractId}/negotiation/comments` — roles: LEGAL_REVIEWER, CONTRACT_OWNER, APPROVER; request: `CommentRequest`; response: `CommentResponse` — Add a free-text comment tied to a clause and the current negotiation version

Enforce the roles above at the framework's authorization layer **and** with the owner/assignment check in business logic. Missing auth header → 401, disallowed role → 403.


## DTOs — request/response types must match these exactly

- **ClauseResponse** (response): `{ clauseId: uuid, clauseText: string, clauseCategory?: string, libraryMatchStatus: string, riskScore: string, aiExplanation?: string, suggestedText?: string, status: string, isMandatory: boolean, mandatoryClauseFlag: boolean, mandatoryClauseFlagLabel?: string, version: integer, updatedAt: datetime, updatedBy?: uuid }`
- **ContractMetadataResponse** (response): `{ parties?: string, partiesLabel: string, contractValue?: number, contractValueLabel: string, startDate?: date, startDateLabel: string, endDate?: date, endDateLabel: string, renewalTerms?: string, renewalTermsLabel: string, paymentTerms?: string, paymentTermsLabel: string, keyObligations?: string, keyObligationsLabel: string }`
- **ClauseAnalysisResponse** (response): `{ contractId: uuid, fileFormatSupported: boolean, analysisStatus: string, clauses: array, overallContractRiskScore: string, metadata?: ContractMetadataResponse, proceedToNegotiationEnabled: boolean, askAiEnabled: boolean }`
- **EditClauseRequest** (request): `{ clauseText: string, expectedVersion: integer }`
- **RejectClauseRequest** (request): `{ reason?: string }`
- **UpdateMetadataRequest** (request): `{ parties?: string, contractValue?: number, startDate?: date, endDate?: date, renewalTerms?: string, paymentTerms?: string, keyObligations?: string }`
- **AskAIRequest** (request): `{ question: string }`
- **AskAIResponse** (response): `{ answer: string, disclaimer: string, relatedClauseIds?: array }`
- **AuditLogEntryResponse** (response): `{ id: uuid, userId: uuid, userName: string, timestamp: datetime, clauseId?: uuid, actionType: string, fieldName?: string, beforeText?: string, afterText?: string }`
- **PagedAuditLogResponse** (response): `{ items: array, page: integer, pageSize: integer, totalCount: integer }`
- **ProceedToNegotiationResponse** (response): `{ contractId: uuid, negotiationStatus: string, routedAt?: datetime, clauses: array, overallContractRiskScore: string, metadata?: ContractMetadataResponse, askAiAvailable: boolean }`
- **ReviewerResponse** (response): `{ reviewerId: uuid, reviewerName: string, role?: string, isMandatory: boolean, reviewStatus: string, submittedAt?: datetime, sequenceOrder?: integer }`
- **RoutingRequest** (request): `{ routingType: string, internalReviewers: array, externalPartyName: string, externalPartyEmail: string, assignedDate: date, dueDate: date }`
- **RoutingResponse** (response): `{ contractId: uuid, routingType: string, internalReviewers: array, externalPartyName: string, externalPartyEmail: string, assignedDate: date, dueDate: date, negotiationStatus: string, versionNumber: integer }`
- **VersionSummaryResponse** (response): `{ versionNumber: integer, createdAt: datetime, createdBy: string, source: string }`
- **CommentResponse** (response): `{ commentId: uuid, clauseId?: string, commentText: string, authorName: string, createdAt: datetime, versionNumber: integer }`
- **CommentRequest** (request): `{ clauseId?: string, commentText: string }`
- **NegotiationTrackerResponse** (response): `{ contractId: uuid, routingType: string, internalReviewers: array, externalPartyName: string, externalPartyEmail: string, assignedDate: date, dueDate: date, negotiationStatus: string, versionNumber: integer, overdueFlag: boolean, versions: array, comments: array }`
- **SubmitReviewRequest** (request): `{ commentText?: string, redlineText?: string }`
- **SubmitReviewResponse** (response): `{ versionNumber: integer, negotiationStatus: string }`
- **GenerateExternalLinkResponse** (response): `{ linkToken: string, expiresAt: datetime, status: string }`
- **VerifyOtpRequest** (request): `{ otp: string }`
- **NegotiationExternalViewResponse** (response): `{ contractId: uuid, versionNumber: integer, documentText: string, commentBoxEnabled: boolean }`
- **VerifyOtpResponse** (response): `{ verified: boolean, negotiationData?: NegotiationExternalViewResponse }`
- **ExternalSubmitRequest** (request): `{ commentText?: string, redlineText: string }`
- **ExternalSubmitResponse** (response): `{ versionNumber: integer, negotiationStatus: string }`
- **ClauseDiffResponse** (response): `{ clauseId?: string, clauseCategory?: string, textA?: string, textB?: string, changeType: string }`
- **CompareVersionsResponse** (response): `{ versionA: VersionSummaryResponse, versionB: VersionSummaryResponse, differences: array, comments: array, negotiationStatus: string, routingType: string, internalReviewers: array, externalPartyName: string, externalPartyEmail: string, assignedDate: date, dueDate: date }`
- **ReminderResponse** (response): `{ sentTo: string, sentAt: datetime, reminderType: string }`
- **MarkAgreedResponse** (response): `{ negotiationStatus: string, versionNumber: integer, routingType: string, internalReviewers: array, externalPartyName: string, externalPartyEmail: string, assignedDate: date, dueDate: date }`

## Tables (models mirror these)

### `contract_clauses` — Stores each AI-extracted or manually-tagged clause with category, library match status, risk score and lifecycle status
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `clause_category`: VARCHAR(50) (nullable)
- `library_match_status`: VARCHAR(20) (not null)
- `risk_score`: VARCHAR(10) (not null)
- `ai_explanation`: TEXT (nullable)
- `suggested_text`: TEXT (nullable)
- `clause_text`: TEXT (not null)
- `status`: VARCHAR(30) (not null)
- `is_mandatory`: BOOLEAN (not null)
- `mandatory_flag_cleared`: BOOLEAN (not null)
- `version`: INTEGER (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
- `deleted_at`: TIMESTAMPTZ (nullable)
- `deleted_by`: UUID (nullable)
  indexes: contract_id, contract_id,status

### `contract_metadata` — Stores AI-extracted/user-confirmed contract-level metadata fields for a contract
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `parties`: TEXT (nullable)
- `parties_label`: VARCHAR(20) (not null)
- `contract_value`: NUMERIC(18,2) (nullable)
- `contract_value_label`: VARCHAR(20) (not null)
- `start_date`: DATE (nullable)
- `start_date_label`: VARCHAR(20) (not null)
- `end_date`: DATE (nullable)
- `end_date_label`: VARCHAR(20) (not null)
- `renewal_terms`: TEXT (nullable)
- `renewal_terms_label`: VARCHAR(20) (not null)
- `payment_terms`: TEXT (nullable)
- `payment_terms_label`: VARCHAR(20) (not null)
- `key_obligations`: TEXT (nullable)
- `key_obligations_label`: VARCHAR(20) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: contract_id

### `clause_audit_log` — Immutable audit trail of Accept/Edit/Reject/Metadata/AskAI actions against clauses and metadata
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `clause_id`: UUID (nullable)
- `user_id`: UUID (not null)
- `action_type`: VARCHAR(30) (not null)
- `field_name`: VARCHAR(50) (nullable)
- `before_text`: TEXT (nullable)
- `after_text`: TEXT (nullable)
- `occurred_at`: TIMESTAMPTZ (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: contract_id,occurred_at

### `ask_ai_interactions` — Stores free-text Ask AI questions, answers, and disclaimer context per contract
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `user_id`: UUID (not null)
- `question`: TEXT (not null)
- `answer`: TEXT (nullable)
- `disclaimer`: TEXT (nullable)
- `related_clause_ids`: JSONB (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: contract_id

### `negotiation_routings` — Stores the routing configuration and current negotiation status/version pointer for a contract
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `routing_type`: VARCHAR(20) (not null)
- `external_party_name`: VARCHAR(200) (not null)
- `external_party_email`: VARCHAR(200) (not null)
- `assigned_date`: DATE (not null)
- `due_date`: DATE (not null)
- `negotiation_status`: VARCHAR(20) (not null)
- `current_version_number`: INTEGER (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: contract_id

### `negotiation_reviewers` — Stores internal reviewers assigned to a negotiation routing, including mandatory auto-added reviewers and review status
- `id`: UUID (not null)
- `negotiation_routing_id`: UUID (not null)
- `reviewer_id`: UUID (not null)
- `reviewer_name`: VARCHAR(200) (not null)
- `role`: VARCHAR(50) (nullable)
- `is_mandatory`: BOOLEAN (not null)
- `review_status`: VARCHAR(20) (not null)
- `sequence_order`: INTEGER (nullable)
- `submitted_at`: TIMESTAMPTZ (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: negotiation_routing_id

### `negotiation_versions` — Stores read-only version history for a contract's negotiation, each snapshot created on redline/comment
- `id`: UUID (not null)
- `contract_id`: UUID (not null)
- `negotiation_routing_id`: UUID (not null)
- `version_number`: INTEGER (not null)
- `source`: VARCHAR(10) (not null)
- `document_snapshot`: JSONB (nullable)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: contract_id,version_number

### `negotiation_comments` — Stores free-text comments entered via the Comment Box, tied to a clause and negotiation version
- `id`: UUID (not null)
- `negotiation_version_id`: UUID (not null)
- `clause_id`: UUID (nullable)
- `comment_text`: TEXT (not null)
- `author_id`: UUID (not null)
- `author_name`: VARCHAR(200) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: negotiation_version_id

### `negotiation_external_links` — Stores secure OTP-protected links issued to external parties, tracking lockout and expiry state
- `id`: UUID (not null)
- `negotiation_routing_id`: UUID (not null)
- `link_token`: VARCHAR(100) (not null)
- `otp_hash`: VARCHAR(255) (not null)
- `failed_attempts`: INTEGER (not null)
- `status`: VARCHAR(20) (not null)
- `expires_at`: TIMESTAMPTZ (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: link_token

### `negotiation_reminders` — Logs automatic daily and manual reminder emails sent to overdue reviewers
- `id`: UUID (not null)
- `negotiation_routing_id`: UUID (not null)
- `reviewer_id`: UUID (nullable)
- `sent_at`: TIMESTAMPTZ (not null)
- `reminder_type`: VARCHAR(10) (not null)
- `created_at`: TIMESTAMPTZ (not null)
- `created_by`: UUID (not null)
- `updated_at`: TIMESTAMPTZ (not null)
- `updated_by`: UUID (not null)
  indexes: negotiation_routing_id,sent_at

## Migrations

Create these with exactly these names, in this order:

- `CreateContractClauses`
- `CreateContractMetadata`
- `CreateClauseAuditLog`
- `CreateAskAiInteractions`
- `CreateNegotiationRoutings`
- `CreateNegotiationReviewers`
- `CreateNegotiationVersions`
- `CreateNegotiationComments`
- `CreateNegotiationExternalLinks`
- `CreateNegotiationReminders`

Never edit or re-order a migration that already exists — add a new one.


## Acceptance criteria to satisfy

### Review AI-Extracted Clauses and Metadata Before Proceeding to Negotiation (`UC4-MF-001`)
- Given a draft or uploaded contract is opened, When AI extraction runs, Then the Clause List panel displays each clause's text, Clause Category, and Library Match Status.
- Given a clause row is reviewed, When the user inspects it, Then the system displays its Risk Score, AI Explanation, and Suggested Text.
- Given a clause's Suggested Text is shown, When the user clicks Accept Suggestion, Then the clause text is replaced, marked Accepted, and logged with user, timestamp, and clause id.
- Given a user wants to rewrite a clause, When the user edits text in the Clause Edit Box and clicks Save, Then the clause is marked Edited (Manual) and the before/after text is logged with user and timestamp.
- Given the tenant's mandatory clause list, When a mandatory clause is not found in the contract, Then the system displays the Mandatory Clause Flag labelled 'Mandatory clause missing' in red.
- Given all individual clause risk scores, When the system computes the contract-level result, Then it displays the Overall Contract Risk Score as the highest of the individual scores.
- Given the contract is extracted, When metadata is auto-filled, Then the system populates Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations, each marked 'AI-suggested' until edited.
- Given a question is typed into the Ask AI Box, When the user submits it, Then the system displays an AI-generated answer referencing the relevant clause(s) with the note that it is AI suggestion only.
- Given all mandatory clauses are resolved, When the user clicks Proceed to Negotiation, Then the system saves the finalised clause set and metadata and routes the contract to Negotiation & Routing (UC5).

### Block AI Analysis for Unsupported File Formats (`UC4-AF-001`)
- Given a contract document exists in a file format other than PDF or DOCX, when a Legal Reviewer or Contract Owner opens the contract for AI Clause Analysis, then the system displays the message 'This file type is not supported for AI analysis. Please upload a PDF or DOCX file.' and blocks analysis.
- Given analysis is blocked due to an unsupported file format, when the screen renders, then none of the following are populated or displayed: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and the Ask AI Box.
- Given the unsupported file type message is displayed, when the Legal Reviewer or Contract Owner attempts to interact with the Ask AI Box, then the system prevents submission since no analysis data is available.
- Given the contract's file format is unsupported, when the alternate flow is triggered, then the contract remains in its UC2 'Draft' state and no clause-level or document-level analysis state is created or modified.

### Continue Clause Tagging Manually After AI Extraction Failure (`UC4-AF-002`)
- Given a Legal Reviewer or Contract Owner opens a contract for AI Clause Analysis, When the AI extraction process fails or times out, Then the system displays the message "AI analysis could not be completed. Please retry or continue manually."
- Given the AI analysis failure message is displayed, When the user chooses to retry, Then the system re-attempts AI extraction and, if it still fails, re-displays the same failure message.
- Given the AI analysis failure message is displayed, When the user chooses to continue manually, Then the system allows manual entry and tagging for Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.
- Given the user is tagging clauses manually, When no AI Explanation or Suggested Text is available due to the extraction failure, Then those fields are shown as blank or not applicable rather than populated with AI content.
- Given the user manually sets a Mandatory Clause Flag or Overall Contract Risk Score, When the entry is saved, Then the system records the value as user-entered and logs the change per BR-6.
- Given AI extraction has failed, When the user attempts to use the Ask AI Box, Then the system either disables the Ask AI Box or indicates that AI-based answers are currently unavailable.
- Given manual tagging is completed for all mandatory clause categories, When the user views the Proceed to Negotiation button, Then it becomes enabled consistent with BR-5.

### Deny unauthorized access to Clause Analysis screen (`UC4-AF-003`)
- Given a user is logged in without Legal Reviewer or Contract Owner role for the tenant, when the user attempts to open the Clause Analysis screen, then the system displays the message "You do not have permission to view this contract's clause analysis." and denies access.
- Given access is denied, when the denial is enforced, then none of the following data points are rendered or exposed to the user: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.
- Given the user is Approver, External Party, or Signer, when they attempt to navigate directly to the Clause Analysis screen via URL or deep link, then the system still displays the permission-denied message and blocks rendering of the screen's data groups.
- Given access is denied, when the system logs the attempt, then no clause data, metadata, or Ask AI Box content is included in any client-side response payload sent to the unauthorized user.

### Block concurrent clause edit conflicts with refresh prompt (`UC4-AF-004`)
- Given a Legal Reviewer and a Contract Owner both open the same contract's clause analysis screen simultaneously and both begin editing the same clause via the Clause Edit Box, When the first user clicks Save and the change is persisted, Then the second user's subsequent Save attempt on the same clause is blocked and the system displays the message "This clause was just updated by another user. Please refresh to see the latest version."
- Given the second user's Save is blocked due to a concurrent update, When the second user refreshes the screen, Then the Clause List Panel reloads the latest version of the clause including its current Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box content, and Mandatory Clause Flag so the second user can re-apply their edit against current data
- Given the refresh has occurred after a blocked save, When the clause analysis screen reloads, Then the Overall Contract Risk Score label is recalculated and displayed consistent with the latest accepted clause state
- Given the refresh has occurred after a blocked save, When the Contract Metadata section is displayed, Then the Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations fields reflect the latest saved values and are not overwritten by the blocked save attempt
- Given the refresh has occurred after a blocked save, When the second user wishes to query the contract, Then the Ask AI Box remains available for submitting questions and is unaffected by the earlier blocked save
- Given a save is blocked due to concurrent edit conflict, When the blocking message is displayed, Then no audit log entry is written for the blocked (second) save attempt, and only the successfully persisted first save is recorded per BR-6

### Prevent Empty Ask AI Question Submission (`UC4-AF-005`)
- Given a contract analysis screen displaying Clause List Panel with Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations, When the Legal Reviewer or Contract Owner leaves the Ask AI Box empty and clicks the Ask button, Then the system displays the message 'Please enter a question before submitting.' and does not call the AI.
- Given the Ask AI Box is empty, When the Ask button is clicked, Then no AI Answer Display is populated and no request is sent to the AI service.
- Given the validation message has been displayed, When the user enters a non-empty question into the Ask AI Box and clicks Ask again, Then the question is submitted to the AI and the AI Answer Display shows the response with the note 'AI suggestion only — verify before relying on this answer.'
- Given the Ask AI Box validation failed, When the screen re-renders, Then the Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations remain unchanged and unaffected by the failed submission.

### Block Proceed to Negotiation When Mandatory Clauses Are Missing (`UC4-AF-006`)
- Given a contract in Draft state with its Clause List Panel displaying each clause's Clause Category, Library Match Status, Risk Score, AI Explanation, and Suggested Text, When at least one mandatory clause has Library Match Status of Missing and its Mandatory Clause Flag is displayed, Then the Proceed to Negotiation button remains disabled per BR-5.
- Given the Legal Reviewer or Contract Owner clicks 'Proceed to Negotiation' while a mandatory clause is still Missing, When the system evaluates the contract's clause statuses, Then the system displays the message 'This contract is missing one or more mandatory clauses. Resolve all red-flagged clauses before proceeding.' and blocks navigation to UC5.
- Given the blocking message is displayed, When the user reviews the screen, Then the following data points remain visible and unchanged for context: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.
- Given a mandatory clause is flagged Missing, When the user attempts to resolve it via the Clause Edit Box and saves replacement text, Then the clause status moves to Edited (Manual) per BR-17 and the Mandatory Clause Flag is cleared once no mandatory clauses remain Missing.
- Given all mandatory clauses have been resolved, When the user clicks 'Proceed to Negotiation' again, Then the system permits navigation to UC5 without displaying the blocking message.

### Calculate Overall Contract Risk Score from Highest Clause Risk (`UC4-BR-001`)
- Given a contract has at least one clause with Risk Score 'High', when the system computes the Overall Contract Risk Score, then the Overall Contract Risk Score is displayed as 'High'.
- Given no clause has Risk Score 'High' but at least one clause has Risk Score 'Medium', when the system computes the Overall Contract Risk Score, then the Overall Contract Risk Score is displayed as 'Medium'.
- Given all clauses have Risk Score 'Low', when the system computes the Overall Contract Risk Score, then the Overall Contract Risk Score is displayed as 'Low'.
- Given the Clause Analysis screen is displayed, when a Legal Reviewer, Contract Owner, or Tenant Admin views the contract, then the following data points are each visible and correctly populated: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.
- Given a clause's Risk Score changes after an Accept Suggestion or Save edit action, when the clause-level Risk Score is recalculated, then the Overall Contract Risk Score is re-evaluated using the highest remaining clause Risk Score.
- Given the contract has zero clauses with a Risk Score assigned, when the Overall Contract Risk Score is computed, then it defaults to 'Low' until at least one clause is scored.

### Flag mandatory clause categories as Missing when absent from document text (`UC4-BR-002`)
- Given a published clause library with a mandatory Clause Category, When the AI analysis scans the document text and finds no matching text for that category, Then the Library Match Status for that category is set to 'Missing' and displayed in the Clause List Panel.
- Given a clause is marked Missing and the category is mandatory, When the Clause List Panel renders the clause row, Then the Mandatory Clause Flag displays 'Mandatory clause missing' in red alongside the Clause Category and Library Match Status.
- Given a clause is marked Missing, When the system computes the Risk Score for that clause, Then the Risk Score is set to a non-Low value and is reflected in the Overall Contract Risk Score per BR-1.
- Given a clause is marked Missing, When the Legal Reviewer views the clause detail, Then no Suggested Text or AI Explanation referencing a matched clause is shown, since no matching text exists in the document.
- Given a clause is marked Missing, When the Legal Reviewer opens the Clause Edit Box, Then they may enter replacement clause text, which upon Save moves the clause out of Missing status per BR-17.
- Given the system completes mandatory-clause checking, When reviewing all data points associated with the clause analysis screen, Then the following data points are each accounted for in the UI and logic: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.

### Flag Clause as Deviated When Wording Exceeds Similarity Threshold (`UC4-BR-003`)
- Given an extracted clause matches a library clause category but its wording differs beyond the tenant's configured similarity threshold, When the clause analysis is run, Then the clause's Library Match Status is set to 'Deviated' and displayed in the Clause List Panel.
- Given a clause's wording differs from the library clause but the difference is within the tenant's configured similarity threshold, When the clause analysis is run, Then the clause's Library Match Status is set to 'Standard' and not 'Deviated'.
- Given a clause is entirely absent from the document text, When the clause analysis is run, Then the clause's Library Match Status is set to 'Missing' and not 'Deviated'.
- Given a clause is flagged as 'Deviated', When the Legal Reviewer or Contract Owner opens the clause details, Then the system displays the Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box associated with the clause and contract.
- Given a clause is marked 'Deviated' and is also flagged mandatory, When the Legal Reviewer views the clause, Then the Mandatory Clause Flag does not display 'Mandatory clause missing' since the clause is present but deviating, and the Overall Contract Risk Score is recalculated to reflect the clause's Risk Score per BR-1.
- Given a clause's Library Match Status changes to 'Deviated', When the Legal Reviewer requests an explanation, Then the AI Explanation field and Suggested Text field are populated to support the Legal Reviewer's or Contract Owner's decision to Accept Suggestion or Edit via the Clause Edit Box.

### Flag Unmatched Clauses as Non-standard (`UC4-BR-004`)
- Given a contract has been processed for clause analysis, When an extracted clause's wording does not correspond to any Clause Category defined in the tenant's clause library, Then its Library Match Status is set to 'Non-standard'.
- Given a clause is marked Non-standard, When the Clause List Panel is displayed, Then the clause's Clause Category is shown as 'Other' or left unassigned, and its Library Match Status reads 'Non-standard'.
- Given a clause is marked Non-standard, When the Legal Reviewer or Contract Owner opens the clause detail, Then the AI Explanation describes why no library category matched, a Risk Score (Low, Medium, or High) is assigned, and any Suggested Text offered is a fallback wording rather than a library-matched clause.
- Given a Non-standard clause is present, When the Legal Reviewer edits it, Then the Clause Edit Box is available for manual rewrite and the edit is captured via the Save action.
- Given a Non-standard clause is not flagged as mandatory, When the Mandatory Clause Flag is evaluated, Then it does not display 'Mandatory clause missing' solely due to Non-standard status.
- Given one or more clauses are marked Non-standard, When the Overall Contract Risk Score is calculated, Then the Non-standard clause's Risk Score is included in that calculation per BR-1.
- Given a contract contains Non-standard clauses alongside other contract data, When the analysis screen renders, Then the following data points are all present and correctly populated where applicable: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.

### Block Proceed to Negotiation until mandatory clauses resolved (`UC4-BR-005`)
- Given the Clause List Panel shows at least one clause with Library Match Status of Missing that is flagged mandatory, When the Legal Reviewer or Contract Owner views the screen, Then the Proceed to Negotiation button is disabled and the Mandatory Clause Flag displays 'Mandatory clause missing' in red.
- Given the clause analysis screen is displayed, When the Legal Reviewer or Contract Owner reviews a clause, Then the Clause Category, Library Match Status, Risk Score, AI Explanation, and Suggested Text are shown for that clause, and the Overall Contract Risk Score is displayed for the contract as a whole.
- Given a clause requires manual correction, When the Legal Reviewer uses the Clause Edit Box to replace the missing mandatory clause text and saves it, Then the Library Match Status for that clause is no longer Missing and the Mandatory Clause Flag is cleared for that clause.
- Given no clause remains with Library Match Status of Missing and flagged mandatory, When the Legal Reviewer or Contract Owner views the screen, Then the Proceed to Negotiation button becomes enabled.
- Given the contract metadata panel is displayed, When the Legal Reviewer or Contract Owner reviews the contract, Then Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations are all visible alongside the clause data.
- Given the Ask AI Box is available on the screen, When the Legal Reviewer or Contract Owner wants to clarify why the Proceed to Negotiation button is disabled, Then they may use the Ask AI Box to ask a question about the missing mandatory clause without that interaction affecting the button's disabled state.

### Log every Accept, Edit, and Reject action to an immutable audit trail (`UC4-BR-006`)
- Given a clause with a Clause Category and Library Match Status displayed, when a Legal Reviewer or Contract Owner clicks Accept Suggestion, then the audit log records the user, timestamp, clause id, and before/after text, including the affected Clause Category, Library Match Status, Risk Score, AI Explanation, and Suggested Text at the time of the action.
- Given the Clause Edit Box is used to manually rewrite clause text, when the Save action is confirmed, then the audit log records the user, timestamp, clause id, and before/after text reflecting the change made via the Clause Edit Box.
- Given a clause is rejected, when the Reject action is performed, then the audit log records the user, timestamp, clause id, and before/after text for that clause, including its Mandatory Clause Flag status and any impact on the Overall Contract Risk Score.
- Given any change to Contract Metadata fields - Parties, Contract Value, Start Date, End Date, Renewal Terms, Payment Terms, or Key Obligations - is made as part of an Accept, Edit, or Reject action, when the change is saved, then the audit log records the user, timestamp, clause id, and before/after text for the affected metadata field(s).
- Given a question is submitted via the Ask AI Box in connection with a clause decision, when the associated Accept, Edit, or Reject action is logged, then the Ask AI Box interaction is captured in the audit trail alongside the user, timestamp, clause id, and before/after text.
- Given an audit log entry exists for any Accept Suggestion, Edit, or Reject action, when any user, including Tenant Admin, attempts to edit or delete that entry, then the system blocks the action and the entry remains unchanged.
- Given the full set of named data points - Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box - when any of these are involved in a logged action, then each relevant data point's before/after state is individually captured and retrievable from the audit log.

### Relabel AI-extracted metadata as user-confirmed after manual edit (`UC4-BR-007`)
- Given a contract opened on the AI Clause Analysis screen, When the AI extraction completes, Then each of the following metadata fields is displayed labelled 'AI-suggested': Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations.
- Given a Contract Owner edits the Contract Metadata - Parties field and clicks Save, When the save completes, Then only the Contract Metadata - Parties field changes its label to 'User-confirmed' while the remaining metadata fields keep the 'AI-suggested' label.
- Given a Legal Reviewer edits the Contract Metadata - Contract Value field and saves the change, When the save completes, Then the Contract Metadata - Contract Value field is labelled 'User-confirmed'.
- Given a Legal Reviewer edits the Contract Metadata - Start Date or Contract Metadata - End Date field in DD/MM/YYYY format and saves, When the save completes, Then the respective edited date field is labelled 'User-confirmed'.
- Given a user edits the Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, or Contract Metadata - Key Obligations field and saves, When the save completes, Then the respective edited field is labelled 'User-confirmed'.
- Given no manual edit has been saved for a metadata field, When the Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, or Ask AI Box content is displayed, Then these non-metadata elements are unaffected by the AI-suggested/User-confirmed labelling rule and retain their own defined behaviour.
- Given a Contract Owner attempts to directly edit clause text via the Clause Edit Box, When the Contract Owner lacks edit rights per BR-10, Then the attempt is blocked and the AI-suggested/User-confirmed labelling applies only to the metadata fields listed, not to clause text.

### Display Verification Disclaimer with AI Answer (`UC4-BR-008`)
- Given a contract is open on the AI Clause Analysis screen with its Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations all populated, When a Legal Reviewer or Contract Owner enters a question into the Ask AI Box and submits it, Then the AI Answer Display shows the answer accompanied by the note 'AI suggestion only — verify before relying on this answer.'
- Given the AI Answer Display has rendered a response to a question submitted via the Ask AI Box, When the Legal Reviewer or Contract Owner reviews the response, Then the disclaimer note must be visibly attached to every answer and must not be dismissible or removable from view.
- Given no question has been submitted via the Ask AI Box, When the AI Clause Analysis screen is first loaded with Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations displayed, Then the AI Answer Display and disclaimer note remain empty/hidden until a question is asked.
- Given a Contract Owner submits a question via the Ask AI Box, When the answer is returned, Then the same disclaimer wording appears regardless of which actor (Legal Reviewer or Contract Owner) asked the question.

### Review, Override, and Progress Clause Analysis as Legal Reviewer (`UC4-BR-009`)
- Given I am logged in as a Legal Reviewer on a contract in UC4, When I open the Clause Analysis screen, Then I can view all extracted clauses along with their Clause Category, Library Match Status, Risk Score, and AI Explanation.
- Given a clause has an AI Suggested Text, When I click Accept Suggestion or Edit followed by saving changes in the Clause Edit Box, Then the clause text is updated and the action is logged to the audit trail.
- Given a clause's Risk Score was determined by the AI, When I override it, Then the Risk Score is updated and the Overall Contract Risk Score is recalculated accordingly.
- Given I enter a question into the Ask AI Box, When I submit it, Then I receive an AI-generated answer accompanied by the verification disclaimer.
- Given I am reviewing a contract, When I view the contract details, Then I can see Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations.
- Given a mandatory clause is missing, When I view the clause list, Then the Mandatory Clause Flag is displayed and the 'Proceed to Negotiation' action remains disabled until resolved.
- Given all mandatory clauses have been resolved, When I click Proceed to Negotiation, Then the contract is routed to UC5 Negotiation.
- Given all 16 data points relevant to this screen — Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box — When I interact with the Clause Analysis screen as a Legal Reviewer, Then each of these fields is visible, accessible, and editable as permitted by my role.

### View and accept AI clause analysis as Contract Owner without direct edit rights (`UC4-BR-010`)
- Given a Contract Owner is viewing the AI Clause Analysis screen, When the clause list loads, Then the Contract Owner can view the following data points for each clause and contract: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.
- Given a Contract Owner is viewing a clause with AI-Suggested status, When the Contract Owner clicks Accept Suggestion, Then the clause text is replaced with the Suggested Text and the acceptance is logged to the audit trail.
- Given a Contract Owner is viewing a clause, When the Contract Owner attempts to open the Clause Edit Box or directly edit clause text, Then the system prevents the edit action and no Save of manual clause text is permitted for the Contract Owner.
- Given a Legal Reviewer has already edited and saved a clause, When the Contract Owner views that clause, Then the Contract Owner cannot override or revert the Legal Reviewer's edit.
- Given a Contract Owner enters a free-text question in the Ask AI Box, When the Contract Owner submits the question, Then the AI Answer Display shows the read-only response accompanied by the disclaimer note.

### View read-only clause analysis across tenant contracts for audit purposes (`UC4-BR-011`)
- Given I am logged in as Tenant Admin, When I open the AI Clause Analysis screen for any contract in the tenant, Then I can view the Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box for every clause and contract without restriction to a specific contract owner.
- Given I am logged in as Tenant Admin, When I view a clause's Suggested Text or Clause Edit Box, Then the Accept Suggestion, Edit, Reject, and Save controls are disabled or hidden so that no clause content can be accepted, edited, or rejected by me.
- Given I am logged in as Tenant Admin, When I view the Ask AI Box on any contract, Then I can see prior AI responses but any attempt to submit a new question or action that modifies clause data is prevented.
- Given I am logged in as Tenant Admin, When I attempt to interact with the Overall Contract Risk Score, Mandatory Clause Flag, or any Contract Metadata field, Then these fields are displayed as read-only labels or text and cannot be edited by me.
- Given I am logged in as Tenant Admin, When I navigate across multiple contracts within the tenant, Then the clause analysis data (Clause Category, Library Match Status, Risk Score, AI Explanation) for each contract is visible for audit review purposes only.

### Restrict Clause Analysis Screen Access from Unauthorized Roles (`UC4-BR-012`)
- Given a user logged in with the Approver, External Party, or Signer role, When they attempt to navigate to the AI Clause Analysis screen, Then the system denies access and does not render the Clause List Panel or any of its contents.
- Given access is denied to Approver, External Party or Signer, When the denial occurs, Then none of the following data points are exposed to that user: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.
- Given a Legal Reviewer or Contract Owner is logged in, When they navigate to the AI Clause Analysis screen, Then full access to the screen and its data points is granted per their authorized role permissions.
- Given an Approver, External Party or Signer attempts direct URL access to the AI Clause Analysis screen, When the request is processed, Then the system redirects or blocks the request and logs the unauthorized access attempt.

### Retain Draft State During Clause Analysis (`UC4-BR-013`)
- Given a contract is in 'Draft' state from UC2, When the Legal Reviewer or Contract Owner opens the AI Clause Analysis screen, Then the contract's document-level state remains 'Draft' and is not altered by viewing the screen.
- Given the AI Clause Analysis screen is displaying the Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and the Ask AI Box, When any of these elements are viewed, edited, or interacted with, Then the contract's state remains 'Draft' and no independent state machine is introduced for this screen.
- Given a Legal Reviewer accepts a clause suggestion, edits clause text, overrides a risk score, or submits an Ask AI question, When these actions are performed on this screen, Then the overall contract state remains unchanged as 'Draft' and only clause-level or metadata-level statuses are affected.
- Given the contract is still in 'Draft' state, When the Legal Reviewer clicks 'Proceed to Negotiation' and all mandatory clauses are resolved, Then the contract transitions out of 'Draft' into the UC5 negotiation state, confirming that this screen itself does not manage that transition.

### Accept AI-suggested clause with one click (`UC4-BR-014`)
- Given a clause displaying Clause Category, Library Match Status, Risk Score, AI Explanation, and Suggested Text with status AI-Suggested, when the Legal Reviewer or Contract Owner clicks Accept Suggestion, then the clause status changes from AI-Suggested to Accepted and the Suggested Text replaces the clause's current text.
- Given a clause is in the Clause Edit Box awaiting review, when the Accept Suggestion action is taken instead of Save, then the Clause Edit Box is not used and the clause moves directly to Accepted status.
- Given a clause is accepted, when the acceptance is recorded, then the Mandatory Clause Flag is re-evaluated and the Overall Contract Risk Score is recalculated based on the updated clause's Risk Score.
- Given the clause being accepted may relate to Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations, when the acceptance occurs, then none of these metadata fields' labels are altered by the clause acceptance action.
- Given a user has submitted a question via the Ask AI Box unrelated to the clause being accepted, when a clause Accept action occurs, then the Ask AI Box content and any prior answer remain unaffected by the clause status change.
- Given the clause status is not AI-Suggested (e.g., already Accepted, Edited, Re-flagged, or Missing-Mandatory), when a user attempts to click Accept Suggestion, then the one-click Accept action is unavailable or has no effect on that clause.

### Transition Clause Status to Edited (Manual) on Save (`UC4-BR-015`)
- Given a clause is displayed on the Clause List Panel with status AI-Suggested, showing its Clause Category, Library Match Status, Risk Score, AI Explanation, and Suggested Text, When the Legal Reviewer clicks Edit to open the Clause Edit Box and modifies the text, Then the clause status remains AI-Suggested until the edit is saved.
- Given the Legal Reviewer has made changes in the Clause Edit Box, When the Legal Reviewer clicks Save, Then the clause status transitions from AI-Suggested to Edited (Manual) and the change is logged with user, timestamp, clause id, and before/after text.
- Given a clause transitions to Edited (Manual), When the Overall Contract Risk Score is recalculated, Then it reflects the highest individual clause Risk Score across all clauses including the newly edited one.
- Given a clause was flagged via the Mandatory Clause Flag as 'Mandatory clause missing', When the Legal Reviewer saves replacement text in the Clause Edit Box, Then the clause moves to Edited (Manual) status and the Mandatory Clause Flag is cleared.
- Given the clause analysis screen also displays Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations, When the Legal Reviewer saves an edited clause, Then none of these metadata fields' AI-suggested/user-confirmed labelling is affected by the clause edit action alone.
- Given the Ask AI Box is used to query the contract, When the Legal Reviewer subsequently saves an edited clause, Then the Ask AI Box interaction remains independent of and does not alter the clause's Edited (Manual) status transition.
- Given the clause edit save action is performed by a Legal Reviewer, When any other role (e.g., Contract Owner) attempts to save edited clause text, Then the status transition to Edited (Manual) must not occur, confirming only a Legal Reviewer can trigger this transition.

### Re-flag accepted or edited clauses changed after a library update (`UC4-BR-016`)
- Given a clause is in Accepted or Edited status, When the tenant's clause library is updated and the clause content is subsequently changed again, Then the system automatically transitions the clause status to Re-flagged.
- Given a clause has been moved to Re-flagged, When the Legal Reviewer or Contract Owner opens the Clause List Panel [F-1], Then the clause's Library Match Status [DP-UC4-003] and Risk Score [DP-UC4-004] are re-evaluated and displayed alongside its Clause Category [DP-UC4-002] and an updated AI Explanation [DP-UC4-005].
- Given a clause is Re-flagged, When the Legal Reviewer reviews it, Then the Suggested Text [DP-UC4-006] is shown and the Clause Edit Box [DP-UC4-009] remains available for manual rewrite, with the Mandatory Clause Flag [DP-UC4-011] re-checked if applicable.
- Given a clause transitions to Re-flagged, When the Overall Contract Risk Score [DP-UC4-012] is recalculated, Then it reflects the highest individual clause Risk Score across the contract, including the Re-flagged clause.
- Given a clause is Re-flagged after a library update, When the reviewer inspects the contract, Then all other contract-level data points remain unaffected and correctly displayed, specifically Contract Metadata - Parties [DP-UC4-013], Contract Metadata - Contract Value [DP-UC4-014], Contract Metadata - Start Date [DP-UC4-015], Contract Metadata - End Date [DP-UC4-016], Contract Metadata - Renewal Terms [DP-UC4-017], Contract Metadata - Payment Terms [DP-UC4-018], Contract Metadata - Key Obligations [DP-UC4-019], and the Ask AI Box [DP-UC4-020] remains available for querying.

### Block Missing-Mandatory Clauses Until Replaced With Text (`UC4-BR-017`)
- Given a clause's Library Match Status is Missing and its Mandatory Clause Flag displays 'Mandatory clause missing' in red, When the Legal Reviewer or Contract Owner views the Clause List Panel, Then the clause's Clause Category, Library Match Status, Risk Score, and AI Explanation are visible but the clause cannot transition to Accepted or Edited (Manual) status via Accept Suggestion.
- Given a clause is blocked as Missing-Mandatory, When the Legal Reviewer attempts to click Accept Suggestion without first entering text, Then the system prevents the state change and the Mandatory Clause Flag continues to display 'Mandatory clause missing'.
- Given a clause is blocked as Missing-Mandatory, When the Legal Reviewer opens the Clause Edit Box via Edit, enters replacement text, and clicks Save, Then the clause status becomes Edited (Manual) and the Mandatory Clause Flag is cleared.
- Given the Missing-Mandatory clause has been replaced and becomes Edited (Manual), When the Overall Contract Risk Score is recalculated, Then it reflects the updated Risk Score of the replaced clause alongside all other clause Risk Scores.
- Given a contract has one or more Missing-Mandatory clauses, When the Contract Owner views Contract Metadata fields - Parties, Contract Value, Start Date, End Date, Renewal Terms, Payment Terms, and Key Obligations, Then these metadata fields remain visible and editable independently of the mandatory clause block, confirming the block applies only to clause acceptance states.
- Given a Missing-Mandatory clause remains unresolved, When a user submits a question via the Ask AI Box, Then the system still allows the query and returns an answer in AI Answer Display, but the clause's blocked status is unaffected by the Ask AI interaction.
- Given the Suggested Text is displayed for a Missing-Mandatory clause, When the Legal Reviewer reviews it without saving an edit, Then the clause remains blocked and does not move to Accepted or Edited (Manual) status.
- Given all 16 relevant data points — Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box — are present on the UC4 screen, When a clause is Missing-Mandatory, Then only its own status transition is blocked while all other data points continue to display and function normally until the clause is replaced with text and becomes Edited (Manual).

### Prevent Unreviewed AI Clause Suggestions from Displaying as Final Content (`UC4-BR-018`)
- Given a clause has an AI-generated Suggested Text that has not been accepted, edited, or rejected by a Legal Reviewer or Contract Owner, When the Clause List Panel is rendered, Then the clause's Suggested Text must be visually distinguished (e.g. labelled 'AI-Suggested') and must never be displayed as the final/authoritative clause text.
- Given a clause analysis is displayed for a contract, When the system renders the following data points, Then each must be shown with correct labelling and status such that unreviewed AI content is never presented as final: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.
- Given an end user (e.g. Approver, External Party, Signer) who has no access to this screen attempts to view contract content, When the contract is still in Draft state with unreviewed AI suggestions, Then those raw suggestions must not be surfaced to that user anywhere outside this screen.
- Given an AI-suggested clause has not yet been accepted or rejected, When a user attempts to proceed the contract to Negotiation or export/share the document, Then the system must block or flag the unresolved AI suggestion so it cannot be mistaken for finalized contract content.
- Given a Legal Reviewer or Contract Owner accepts, edits, or rejects an AI suggestion via the Accept Suggestion, Edit, or Save actions, When the action is completed, Then the clause's displayed status updates from 'AI-Suggested' to the appropriate final state (Accepted, Edited (Manual), or Rejected) and only then may it be treated as reviewed content.

### View Clause List Panel with Category and Match Status Fields (`UC4-FV-001`)
- Given a contract has been analyzed by AI, When the Legal Reviewer opens the Clause List Panel, Then each clause row displays its Clause Category (one of Payment, Liability, Indemnity, Termination, Confidentiality, IP, Governing Law, Other).
- Given a contract has been analyzed by AI, When the Legal Reviewer views a clause row, Then the Library Match Status is shown as one of Standard, Deviated, Missing, or Non-standard.
- Given a clause has been flagged by the AI, When the Legal Reviewer inspects the clause, Then the Risk Score (Low, Medium, High) and the corresponding AI Explanation text are displayed as read-only.
- Given a clause is marked Deviated, Missing, or Non-standard, When the Legal Reviewer opens the clause detail, Then the Suggested Text field shows the AI-suggested standard or fallback wording and the Clause Edit Box is available for manual rewrite.
- Given a mandatory clause category is not found in the document, When the Legal Reviewer views the clause list, Then the Mandatory Clause Flag displays 'Mandatory clause missing' in red.
- Given all clauses have been evaluated, When the Legal Reviewer views the summary, Then the Overall Contract Risk Score (Low, Medium, High) is displayed.
- Given AI extraction has completed, When the Legal Reviewer reviews contract metadata, Then the following fields are displayed and editable: Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations.
- Given the Legal Reviewer wants to ask a question about the contract, When they locate the Ask AI Box, Then it is available as a free-text input for submitting contract-related questions.

### Review and action clause risk details with full metadata visibility (`UC4-FV-002`)
- Given a contract has been analysed, When the Legal Reviewer opens the Clause Review/Detail surface, Then the following data points must be displayed or available for interaction: Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, and Ask AI Box.
- Given a clause has a calculated Risk Score of Low, Medium, or High, When the Legal Reviewer views the clause, Then the Risk Score is displayed alongside the read-only AI Explanation describing the reason for the flag.
- Given a clause's Library Match Status is Deviated or Non-standard, When the Legal Reviewer reviews the clause, Then the Suggested Text is shown and the Legal Reviewer can click Accept Suggestion to replace the clause text, which is logged per BR-6.
- Given a mandatory clause category defined in the tenant's clause library is not found in the document, When the Legal Reviewer views that clause entry, Then the Mandatory Clause Flag displays 'Mandatory clause missing' in red per BR-2 and BR-11.
- Given a clause requires manual rewrite, When the Legal Reviewer clicks Edit, enters text in the Clause Edit Box, and clicks Save, Then the clause status moves to Edited (Manual) per BR-15 and the change is written to the audit log per BR-6.
- Given at least one clause Risk Score exists on the contract, When the Legal Reviewer views the Overall Contract Risk Score, Then it reflects the highest individual clause Risk Score per BR-1.
- Given the Legal Reviewer has a question about the contract, When they enter text in the Ask AI Box and submit it, Then the AI Answer Display shows the response accompanied by the note 'AI suggestion only — verify before relying on this answer' per BR-8.
- Given AI-extracted Contract Metadata fields (Parties, Contract Value, Start Date, End Date, Renewal Terms, Payment Terms, Key Obligations) are displayed, When the Legal Reviewer views them, Then each field is labelled 'AI-suggested' until a manual edit is saved, after which it is labelled 'User-confirmed' per BR-7.

### Edit AI-Extracted Contract Metadata (`UC4-FV-003`)
- Given a contract document has been analyzed, When the Contract Metadata panel is displayed, Then the Contract Metadata - Parties field is shown as AI-extracted text and is editable.
- Given the Contract Metadata panel is displayed, When the Contract Metadata - Contract Value field is populated, Then it is shown as an AI-extracted numeric value and is editable.
- Given the Contract Metadata panel is displayed, When the Contract Metadata - Start Date field is populated, Then it is shown as an AI-extracted date in a date picker formatted DD/MM/YYYY and is editable.
- Given the Contract Metadata panel is displayed, When the Contract Metadata - End Date field is populated, Then it is shown as an AI-extracted date in a date picker formatted DD/MM/YYYY and is editable.
- Given the Contract Metadata panel is displayed, When the Contract Metadata - Renewal Terms field is populated, Then it is shown as AI-extracted text in a text area and is editable.
- Given the Contract Metadata panel is displayed, When the Contract Metadata - Payment Terms field is populated, Then it is shown as AI-extracted text in a text area and is editable.
- Given the Contract Metadata panel is displayed, When the Contract Metadata - Key Obligations field is populated, Then it is shown as AI-extracted text in a text area and is editable.
- Given a user saves a manual edit to any of Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, or Contract Metadata - Key Obligations, When the save completes, Then the field label changes from 'AI-suggested' to 'User-confirmed' per BR-7.

### Ask AI Question About Contract (`UC4-FV-004`)
- Given a contract is open on the AI Clause Analysis screen, When the Legal Reviewer or Contract Owner enters a free text question into the Ask AI Box [DP-UC4-020], Then the Ask Button becomes enabled for submission.
- Given a question has been entered in the Ask AI Box [DP-UC4-020], When the user clicks the Ask Button, Then the AI Answer Display shows a read-only response accompanied by the note 'AI suggestion only — verify before relying on this answer.'
- Given the AI needs to answer a question, When it formulates the response, Then the AI may draw upon any of the following data points as context: Clause Category [DP-UC4-002], Library Match Status [DP-UC4-003], Risk Score [DP-UC4-004], AI Explanation [DP-UC4-005], Suggested Text [DP-UC4-006], Clause Edit Box [DP-UC4-009], Mandatory Clause Flag [DP-UC4-011], Overall Contract Risk Score [DP-UC4-012], Contract Metadata - Parties [DP-UC4-013], Contract Metadata - Contract Value [DP-UC4-014], Contract Metadata - Start Date [DP-UC4-015], Contract Metadata - End Date [DP-UC4-016], Contract Metadata - Renewal Terms [DP-UC4-017], Contract Metadata - Payment Terms [DP-UC4-018], and Contract Metadata - Key Obligations [DP-UC4-019].
- Given the user is a Legal Reviewer or Contract Owner, When they access the Ask AI Box [DP-UC4-020] and Ask Button, Then the feature is available to both roles per BR-9 and BR-10.
- Given a user without Ask AI permission (e.g. Tenant Admin, Approver, External Party, Signer), When they view the screen, Then the Ask AI Box [DP-UC4-020], Ask Button, and AI Answer Display are either hidden or disabled per BR-11 and BR-12.
- Given the Ask AI Box [DP-UC4-020] is left empty, When the user attempts to click the Ask Button, Then the submission is prevented until a question is entered.

### View Overall Contract Risk Score and Proceed to Negotiation Control (`UC4-FV-005`)
- Given a contract has been analysed by AI, When the Clause Analysis screen loads, Then the Overall Contract Risk Score is displayed at the top as Low, Medium or High per BR-1.
- Given at least one clause is flagged Missing and mandatory, When the Legal Reviewer views the screen, Then the Proceed to Negotiation button is disabled per BR-5.
- Given all mandatory clauses are resolved, When the Legal Reviewer clicks Proceed to Negotiation, Then the contract routes to UC5.
- Given the screen displays clause-level data, When the Legal Reviewer or Contract Owner reviews a clause, Then the Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, and Mandatory Clause Flag are all shown alongside the Overall Contract Risk Score.
- Given the screen displays contract metadata, When the Legal Reviewer or Contract Owner reviews the contract, Then the Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations are all displayed.
- Given the screen provides an AI query tool, When the Legal Reviewer or Contract Owner wants additional information, Then the Ask AI Box is available for free-text questions.
- Given all 16 required data points (Clause Category, Library Match Status, Risk Score, AI Explanation, Suggested Text, Clause Edit Box, Mandatory Clause Flag, Overall Contract Risk Score, Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, Contract Metadata - Key Obligations, Ask AI Box) must be present, When the screen renders, Then each of these named data points is visible and correctly labelled.

### View extracted clause list with category and library match status (`UC4-GC-001`)
- Given a contract document has been processed by AI clause extraction, when I open the Clause List Panel, then each row displays the clause's Clause Category and Library Match Status alongside the clause text.
- Given the Clause Category column is displayed, when a clause is categorized, then its value is one of: Payment, Liability, Indemnity, Termination, Confidentiality, IP, Governing Law, or Other.
- Given the Library Match Status column is displayed, when a clause is compared against the tenant's clause library, then its value is one of: Standard, Deviated, Missing, or Non-standard.
- Given I select a clause row, when the clause detail expands, then the Risk Score, AI Explanation, and Suggested Text are shown for that clause.
- Given I choose to edit a clause, when the Clause Edit Box is opened, then I can manually rewrite the clause text.
- Given a mandatory clause category is not found in the document, when the Clause List Panel renders, then the Mandatory Clause Flag is displayed for that category.
- Given all clauses have been analyzed, when I view the panel summary, then the Overall Contract Risk Score is displayed reflecting the highest individual clause risk.
- Given the contract metadata has been AI-extracted, when I view the metadata section, then Contract Metadata - Parties, Contract Metadata - Contract Value, Contract Metadata - Start Date, Contract Metadata - End Date, Contract Metadata - Renewal Terms, Contract Metadata - Payment Terms, and Contract Metadata - Key Obligations are all displayed and editable.
- Given I want to ask a question about the contract, when I view the panel, then an Ask AI Box is available for free-text input.

## Rules

- Do not invent endpoints, routes, DTO fields or table columns beyond what is listed above -- treat this file as the contract for this module.
- Implement every endpoint against the real database via this module's tables/migrations -- no mock/in-memory data (see CLAUDE.md's conventions).
- If a change here would affect another module's existing files, stop and extend shared code instead of rewriting it.
