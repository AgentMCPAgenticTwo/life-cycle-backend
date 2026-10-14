# Modules

# Cross-cutting

* [App Core](/modules/app-core.md) - Cross-cutting FastAPI app wiring shared by every resource module — entry point, bearer auth, settings, DB session, shared error types and model mixins.
* [Auth](/modules/auth.md) - Real login — JWT access tokens, rotating httpOnly-cookie refresh tokens, bcrypt password storage and the admin bootstrap script that replaced the X-User-Role/X-User-Id header stub.

# uc123 batch

* [Dashboard / Lookups](/modules/dashboard-lookups.md) - Dashboard summary/tasks/high-risk-contracts/filters and the shared users/counterparties/contracts lookup queries that back them, from the uc123 batch.
* [Contracts](/modules/contracts.md) - Contract listing, detail and creation including third-party-paper intake, the base resource most other modules extend.
* [Templates / Clauses](/modules/templates-clauses.md) - Reusable contract template and clause library with versioning, activation lifecycle, and the version-history endpoints shared by both resources.
* [Counterparties](/modules/counterparties.md) - Counterparty directory used by contract creation and dashboard filters.
* [Files](/modules/files.md) - Uploaded-file persistence backing third-party-paper intake and contract document retrieval; service/repository only, no dedicated router.

# lifecycle-uc4-uc5 batch

* [Lifecycle Clauses](/modules/lifecycle-clauses.md) - AI-assisted clause analysis, suggestion acceptance, manual editing and rejection for a contract in the drafting stage.
* [Lifecycle Negotiation](/modules/lifecycle-negotiation.md) - Contract metadata editing, ask-AI, negotiation routing/reviews, external-party negotiation links with OTP, version comparison, reminders and mark-agreed.

# uc6-uc7-combined batch

* [Approvals](/modules/approvals.md) - Approval queue, step-by-step approve/reject/request-changes actions, delegation and history, the second layering-verification sample for this repo.
* [Approval Matrix](/modules/approval-matrix.md) - Tenant-level approval matrix configuration (steps/thresholds) that approvals routing reads to decide who must approve.
* [Signing](/modules/signing.md) - Contract signer management and the OTP-based signing-session flow (view, verify, sign, decline) plus the audit certificate produced once fully executed.
* [E-signature Settings](/modules/esignature-settings.md) - Tenant-wide e-signature configuration (single GET/PUT resource) consumed by the signing-session flow.

# life-cycle-uc8-uc9 batch

* [Contract Lifecycle](/modules/contract-lifecycle.md) - Executed-contract detail, document retrieval, version history, activity log, folder tags, obligations, and renewal/amendment/termination actions.

# lifecycle-uc10-uc11 batch

* [Tracker](/modules/tracker.md) - Management tracker with four reporting tabs (ownership, cycle-time, bottleneck, turnaround), export, turnaround overrides and tenant bottleneck thresholds.
* [Settings](/modules/settings.md) - Tenant-admin-only settings surface — user management, approval rules, integrations, notification toggles, and the read-only audit log.

# Infrastructure

* [Migrations](/modules/migrations.md) - 51 Alembic migrations, one table per revision, applied automatically at app startup, never reordered or edited once merged.
* [Tests](/modules/tests.md) - 32 pytest files, one per resource/concern, using the shared `auth_headers` helper plus per-file tenant/user seeding.
