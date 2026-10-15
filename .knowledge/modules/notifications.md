---
type: Module
title: notifications
description: The single outbound-notification service — every email and in-app alert in the app goes through `dispatch`, gated by the tenant's Settings > Notifications toggles.
updated: { by: sage-maintenance/claude-code, at: 2026-10-15T05:15:24Z }
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/notifications.py
tags: [backend, notifications, smtp, uc6, uc7, uc11]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T04:36:49Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 24c451af17fc14c47102e38019b754771e026556
    title: Codebase knowledge graph
status: stable
---

# Files

| File | Role |
|---|---|
| `app/services/notifications.py` | `dispatch` plus the `EVENT_*` constants, `signing_invite_body`, `_toggles`, `_send_email`, `_append` |
| `app/config.py` | `Settings.smtp_host`/`smtp_port`/`smtp_username`/`smtp_password`/`smtp_from`/`smtp_use_tls`/`smtp_timeout_seconds`, `Settings.app_base_url` — see [App Core](/modules/app-core.md) |
| `app/repositories/settings_notifications.py` | `EVENT_NAMES`, `ensure_seeded`, `get_by_name` — the toggle rows this service reads |
| `tests/test_notifications.py` | toggle gating, in-app recording, failure isolation |

There is no router here: this module is service-only and is called from other services, never
from HTTP directly. The toggles it reads are edited through [Settings](/modules/settings.md).

# Events

`EVENT_SENT_FOR_APPROVAL`, `EVENT_APPROVED`, `EVENT_REJECTED`, `EVENT_SENT_BACK`, `EVENT_READY_FOR_SIGNATURE`,
`EVENT_SENT_FOR_SIGNATURE`, `EVENT_SIGNATURE_DECLINED`, `EVENT_EXECUTED`, `EVENT_USER_INVITED`,
and the automatic/time-driven set `EVENT_SENT_TO_COUNTERPARTY`, `EVENT_REVIEW_REMINDER`,
`EVENT_SIGNATURE_REMINDER`, `EVENT_EXPIRING_SOON`.
Each constant's value must appear verbatim in
`app.repositories.settings_notifications.EVENT_NAMES`, or `_toggles` misses the row and silently
falls back to the both-channels-On default.

# Callers

| Caller | Events |
|---|---|
| `app.services.approvals.notify_step_approver` (from `mark_agreed` and from `submit_action` when an Approve advances a step) | sent for approval, to the current step's approver |
| `app.services.approvals._notify_action` (from `submit_action`) | approved / rejected / sent back, plus ready-for-signature when the last step clears |
| `app.services.signers.send_for_signature` | sent for signature — one mail per first-order signer, since the link reference and OTP are per-signer credentials |
| `app.services.signing_sessions.resend_otp` | sent for signature, with the rotated link and OTP |
| `app.services.signing_sessions.apply_signature` | executed, and sent-for-signature to the next signer |
| `app.services.signing_sessions.decline_signature` | signature declined |
| `app.services.settings_users.create_user` | new user invited |
| `app.services.lifecycle_negotiation._issue_external_link` | contract sent to counterparty — carries the secure link token and the OTP |
| `app.services.lifecycle_negotiation.send_reminder` | review reminder (the manual Send Reminder click) |
| `app.services.scheduled_notifications` | review reminder, signature reminder, expiring soon — see [Scheduled Notifications](/modules/scheduled-notifications.md) |

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
  dependency. The log line includes the **body**, not just the recipients and subject: with no
  relay configured that log is the only place the signing link and the one-time password can be
  read, and the tests parse it.

# `signing_invite_body` — the one signing-invite body

Every "here is your signing link" mail is built by `signing_invite_body(signer_name,
contract_name, session_id, link_token, otp_code, expires_at, lead_in)`, so the three senders
differ only in their `lead_in`:

| Sender | Lead-in |
|---|---|
| `app.services.signers.send_for_signature` | first send, to each first-order signer |
| `app.services.signing_sessions.apply_signature` | it is now the next signer's turn |
| `app.services.signing_sessions.resend_otp` | a new link has been issued |

The body carries the clickable `{settings.app_base_url}/sign/{session_id}` URL, the secure link
reference (`link_token`), the one-time password and the link expiry — without the URL and the
OTP there is nothing for the signer to open or type. The plaintext OTP exists only in the
calling function (the row stores a SHA-256 hash), so each caller holds it just long enough to
pass it here. It mirrors the counterparty-review mail in
`app.services.lifecycle_negotiation`.

# Relationships

Depends on [App Core](/modules/app-core.md) for `settings`, and on
[Settings](/modules/settings.md) for the toggle rows and the audit-log repository. Triggered by
[Approvals](/modules/approvals.md), [Signing](/modules/signing.md),
[Settings](/modules/settings.md), [Lifecycle Negotiation](/modules/lifecycle-negotiation.md)
and [Scheduled Notifications](/modules/scheduled-notifications.md).
