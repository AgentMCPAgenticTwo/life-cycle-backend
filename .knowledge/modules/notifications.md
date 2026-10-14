---
type: Module
title: notifications
description: The single outbound-notification service — every email and in-app alert in the app goes through `dispatch`, gated by the tenant's Settings > Notifications toggles.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/notifications.py
tags: [backend, notifications, smtp, uc6, uc7, uc11]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T04:36:49Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ c43909447f3264a2fbec9ac9a11152e7d971a612
    title: Codebase knowledge graph
status: stable
---

# Files

| File | Role |
|---|---|
| `app/services/notifications.py` | `dispatch` plus the `EVENT_*` constants, `_toggles`, `_send_email`, `_append` |
| `app/config.py` | `Settings.smtp_host`/`smtp_port`/`smtp_username`/`smtp_password`/`smtp_from`/`smtp_use_tls`/`smtp_timeout_seconds` — see [App Core](/modules/app-core.md) |
| `app/repositories/settings_notifications.py` | `EVENT_NAMES`, `ensure_seeded`, `get_by_name` — the toggle rows this service reads |
| `tests/test_notifications.py` | toggle gating, in-app recording, failure isolation |

There is no router here: this module is service-only and is called from other services, never
from HTTP directly. The toggles it reads are edited through [Settings](/modules/settings.md).

# Events

`EVENT_APPROVED`, `EVENT_REJECTED`, `EVENT_SENT_BACK`, `EVENT_READY_FOR_SIGNATURE`,
`EVENT_SENT_FOR_SIGNATURE`, `EVENT_SIGNATURE_DECLINED`, `EVENT_EXECUTED`, `EVENT_USER_INVITED`.
Each constant's value must appear verbatim in
`app.repositories.settings_notifications.EVENT_NAMES`, or `_toggles` misses the row and silently
falls back to the both-channels-On default.

# Callers

| Caller | Events |
|---|---|
| `app.services.approvals._notify_action` (from `submit_action`) | approved / rejected / sent back, plus ready-for-signature when the last step clears |
| `app.services.signers.send_for_signature` | sent for signature |
| `app.services.signing_sessions.apply_signature` | executed, and sent-for-signature to the next signer |
| `app.services.signing_sessions.decline_signature` | signature declined |
| `app.services.settings_users.create_user` | new user invited |

# Rules that hold for every event

* A channel fires only when that event's toggle is On for the tenant; an event the tenant has
  never saved defaults to On on both channels (UC11-BR-007), matching what
  `settings_notifications.ensure_seeded` writes.
* `dispatch` never raises. A mail failure is logged and recorded as a `NotificationFailed` row;
  a toggle-read failure returns early. The triggering action is already committed, so delivery
  can never roll back an approval or a signature.
* Callers invoke `dispatch` **after** their own `db.commit()`, and `dispatch` commits its own
  bookkeeping separately.
* In-app alerts land in `tenant_audit_log` with `log_action = "Notification"` — no
  `in_app_notifications` table exists in any module contract, so no migration was added for one.
  That log is also read by [Settings](/modules/settings.md)'s `GET /settings/audit-log`.
* `_send_email` with no `SMTP_HOST` configured (the default in development and in tests) logs
  the message instead of sending it, so the app runs with no mail relay and no mail-provider
  dependency.

# Relationships

Depends on [App Core](/modules/app-core.md) for `settings`, and on
[Settings](/modules/settings.md) for the toggle rows and the audit-log repository. Triggered by
[Approvals](/modules/approvals.md), [Signing](/modules/signing.md) and
[Settings](/modules/settings.md).
