---
type: Module
title: settings
description: Tenant-admin-only settings surface — user management, approval rules, integrations, notification toggles, and the read-only audit log.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/settings_users.py
tags: [backend, lifecycle-uc10-uc11, settings, admin]
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T06:05:54Z }
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 700de34973c81dd98062f0bef469b620e6fc976b
    title: Codebase knowledge graph
status: stable
---

# Files

Five router files, each with matching service/repository/schema:
`settings_users.py`, `settings_approval_rules.py`, `settings_integrations.py`,
`settings_notifications.py`, `settings_audit_log.py` under `app/routers/`, `app/services/`,
`app/repositories/`, `app/schemas/`. All endpoints require `TENANT_ADMIN` — the only module
where every route has a single-role allow-list.

# Endpoints

* `GET/POST /settings/users`, `POST /settings/users/{userId}/reset-password`,
  `PATCH /settings/users/{userId}/status`
* `GET/POST /settings/approval-rules`
* `GET /settings/integrations`, `POST .../connect`, `POST .../disconnect`
* `GET /settings/notifications`, `PUT /settings/notifications/{eventName}`
* `GET /settings/audit-log` -> `AuditLogEntryResponse` (paged, `AuditLogQueryParams`)

# Cluster evidence

Graph cluster 22 (87 members, cohesion 0.75) groups `connect_integration`,
`update_user_status`, `create_user`, `disconnect_integration` — confirming this is one cohesive
unit, distinct from the tracker tabs (cluster 1) even though both come from the same
`lifecycle-uc10-uc11` contract.

# Business rules worth noting

* `PATCH /settings/users/{userId}/status` must block removing the **last active TENANT_ADMIN**
  — this invariant lives in `app/services/settings_users.py`, not the repository.
* `POST /settings/users` also provisions a login credential: `app/services/settings_users.py`
  takes `CreateUserRequest.initialPassword` or calls `app.security.generate_password`, validates
  it with `password_violations`, stores the bcrypt hash on a `users` row with
  `must_change_password` set, and returns it once as `CreateUserResponse.temporaryPassword` — no
  later read of the user includes it again.
* `POST /settings/users/{userId}/reset-password` (`reset_password`) issues a fresh temporary
  password (`ResetPasswordResponse`) and revokes every refresh token the user holds, so the old
  password cannot keep a session alive. See [Auth](/modules/auth.md).
* `POST /settings/users` also sends the `New User Invited` notification via
  `app.services.notifications.dispatch`, after its own commit. See
  [Notifications](/modules/notifications.md).
* `GET /settings/notifications` calls `app.repositories.settings_notifications.ensure_seeded`,
  the repo's only idempotent seeder: it inserts any of the fourteen `EVENT_NAMES` rows the
  tenant is missing with both toggles On (UC11-BR-007), skipping names already present, so it is
  safe on every request. `list_by_tenant` then returns them in `EVENT_NAMES` order rather than
  insertion order. The newest three names — `Contract Sent to Counterparty`, `Review Reminder`,
  `Signature Reminder` — were appended for the automatic notifications in
  [Scheduled Notifications](/modules/scheduled-notifications.md); because the seeder is guarded
  per name, adding them touched no existing tenant row.
* `POST /settings/integrations/{integrationName}/connect` masks credentials in the response
  (`maskedCredential`) and persists `credential_ciphertext` separately from the masked display
  value (`tenant_integrations.credential_masked_display`).

# Tables

`tenant_users`, `approval_matrix_rules`, `tenant_integrations`,
`tenant_notification_settings`, `tenant_audit_log` (migrations 0047-0051).

# Relationships

`approval_matrix_rules` here is a second, simpler approval-configuration table alongside
[Approval Matrix](/modules/approval-matrix.md)'s `approval_matrix_configs`/`steps` — see that
module's note on why both exist. `tenant_audit_log` is a generic log distinct from the
per-resource audit logs used by [Approvals](/modules/approvals.md) (`approval_audit_log`) and
[Signing](/modules/signing.md) (`signature_audit_log`). It is also where
[Notifications](/modules/notifications.md) records in-app alerts
(`log_action = "Notification"`) and delivery failures (`"NotificationFailed"`), so
`GET /settings/audit-log` surfaces rows this module did not write.
