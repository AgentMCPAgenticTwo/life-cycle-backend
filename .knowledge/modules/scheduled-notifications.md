---
type: Module
title: scheduled-notifications
description: The time-driven half of notifications — an in-process sweep that fires UC5 reviewer reminders, UC7 signature reminders and UC9 renewal alerts because a date passed rather than because an endpoint was called.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/services/scheduled_notifications.py
tags: [backend, notifications, scheduler, uc5, uc7, uc9]
generated: { by: sage-maintenance/claude-code, at: 2026-10-14T06:05:54Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-15T05:15:24Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 24c451af17fc14c47102e38019b754771e026556
    title: Codebase knowledge graph
status: stable
---

# Files

| File | Role |
|---|---|
| `app/services/scheduled_notifications.py` | the three sweeps, `run_all`, `sweep_loop`, `_run_all_in_new_session` |
| `app/repositories/scheduled_notifications.py` | tenant-wide queries: `list_open_signers`, `list_renewal_candidates`, `get_renewal_alert`, `insert_renewal_alert`, `list_role_emails`, `get_user_email`, `get_contract_by_id` |
| `app/repositories/lifecycle_negotiation.py` | `list_overdue_routings`, `list_reminders_since` — the UC5 half of the queries |
| `app/config.py` | `Settings.notification_sweep_interval_seconds` (`NOTIFICATION_SWEEP_INTERVAL_SECONDS`, default 3600; `0` disables) |
| `app/main.py` | `lifespan` starts `sweep_loop()` as an `asyncio` task and cancels it on shutdown |
| `tests/test_scheduled_notifications.py` | per-sweep cadence, once-only and stop-condition tests |

There is no router: nothing here is reachable over HTTP. Every message goes out through
`app.services.notifications.dispatch`, so the tenant's Settings > Notifications toggles still
gate each channel — see [Notifications](/modules/notifications.md).

# The three sweeps

| Function | Use case | Cadence | Stops when |
|---|---|---|---|
| `run_reviewer_reminders` | UC5 | one email per day to the overdue reviewer and the Contract Owner | the review is submitted, or `negotiation_status` is `Agreed` (excluded in `list_overdue_routings`) |
| `run_signature_reminders` | UC7 | every X days, X from the signer's Reminder Frequency, then the tenant e-signature setting, then `DEFAULT_SIGNATURE_REMINDER_DAYS` (3) | the signer signs/declines, or the contract status is in `SIGNING_CLOSED_STATUSES` (which lists both `Signature Declined` and the legacy `SignatureDeclined`, so a row migration 0053 has not reached still stops the reminders — see [Contract Status](/modules/contract-status.md)) |
| `run_renewal_alerts` | UC9 | 90/60/30 days before the End Date and before the Notice Period deadline (`ALERT_BASIS_END_DATE` / `ALERT_BASIS_NOTICE`) | each (contract, threshold, basis) fires exactly once — the `renewal_alerts` row is the guard |

`run_signature_reminders`' body includes the signer's portal link,
`{settings.app_base_url}/sign/{signer.id}` — a reminder that only said "open your signing link"
gave the recipient nothing to click. It deliberately does **not** repeat the one-time password
(the row stores only its hash by then), and tells the signer to ask the contract owner for a
resend instead; that resend is [Signing](/modules/signing.md)'s `resend_otp`.

`run_all` calls all three over one `Session` and is the entry point for both the background
loop and any external scheduler. It is pure business logic over a session, so a test calls it
directly.

# Why it runs in-process

This repository declares no scheduler dependency and CLAUDE.md forbids adding packages, so
`sweep_loop` is an `asyncio` task owned by the app `lifespan` rather than a cron/Celery job.
It only starts when `DATABASE_URL` is set and the interval is above zero. Because each sweep is
idempotent per day/per cadence, a shorter interval only makes an alert land sooner — never
twice.

`SYSTEM_ACTOR_ID` is the actor recorded against a notification nobody triggered. It is derived
with `uuid.uuid5` rather than written as a literal, per the no-hard-coded-ids rule in
[Conventions](/conventions.md). `_as_naive_utc` normalises timestamps because SQLite (the tests'
stand-in for Postgres) does not round-trip tz-aware columns.

# Relationships

Dispatches through [Notifications](/modules/notifications.md); reads negotiation routings and
reminders from [Lifecycle Negotiation](/modules/lifecycle-negotiation.md), signers and the
reminder frequency from [Signing](/modules/signing.md) and
[E-signature Settings](/modules/esignature-settings.md), and renewal thresholds
(`RENEWAL_THRESHOLDS_DAYS`, `EXECUTED_STATUSES`, `_parse_notice_period_days`) from
[Contract Lifecycle](/modules/contract-lifecycle.md). Wired into the app by
[App Core](/modules/app-core.md).
