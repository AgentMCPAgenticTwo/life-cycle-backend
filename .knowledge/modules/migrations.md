---
type: Module
title: migrations
description: 54 Alembic migrations, one table per revision (plus one data-only fix-up), applied automatically at app startup, never reordered or edited once merged.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/alembic/versions
tags: [backend, migrations, alembic, postgresql]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-15T05:15:24Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 24c451af17fc14c47102e38019b754771e026556
    title: Codebase knowledge graph
status: stable
---

# Structure

`alembic/versions/0001_create_tenants.py` through
`0054_archive_approval_matrix_configs.py`, applied in
order by `app.main._run_migrations` (see [App Core](/modules/app-core.md)) at every startup via
`command.upgrade(cfg, "head")`. Each file creates exactly one table (confirmed by reading
`0042_create_contract_lifecycle_stage_history.py`, which only calls `op.create_table` once plus
one `op.create_index`).

# Numbering by generation batch

| Range | Batch | Tables |
|---|---|---|
| 0001-0014 | uc123 | tenants, users, counterparties, uploaded_files, templates(+versions), clauses(+versions), contracts, contract_tasks, contract_clauses, contract_metadata, clause_audit_log, ask_ai_interactions |
| 0015-0020 | lifecycle-uc4-uc5 | negotiation_routings/reviewers/versions/comments/external_links/reminders |
| 0021-0030 | uc6-uc7-combined | approval_matrix_configs/steps, approvals, approval_step_instances, approval_delegations, approval_audit_log, signers, signature_audit_log, audit_certificates, esignature_settings |
| 0031-0041 | life-cycle-uc8-uc9 | contract lifecycle alterations, contract_assignments, contract_documents, contract_versions, folder_tags, contract_folder_tags, activity_log_entries, obligations, renewal_alerts, contract_lifecycle_actions, obligation_audit_log |
| 0042-0051 | lifecycle-uc10-uc11 | contract_lifecycle_stage_history, contract_owners, contract_turnaround_metrics, turnaround_override_log, tenant_bottleneck_thresholds, tenant_users, approval_matrix_rules, tenant_integrations, tenant_notification_settings, tenant_audit_log |
| 0052 | auth correction | `users` credential columns, refresh_tokens |
| 0053 | status-flow correction | no DDL — data-only rewrite of `contracts.status`, `approvals.status`, `negotiation_routings.negotiation_status` |
| 0054 | approval-matrix correction | `approval_matrix_configs.archived_at` column |

# Convention: additive only

No migration in this repo edits or drops a table created by an earlier migration (verified by
file naming and content of the sampled 0042 file: pure `CREATE TABLE`, no `ALTER`/`DROP` against
pre-existing tables except the one explicitly named `0031_alter_contracts_for_lifecycle.py`,
which predates and is owned by the `life-cycle-uc8-uc9` batch itself, not a later batch
rewriting an earlier one). New modules must follow the same pattern: add new numbered revisions,
never touch an existing one.

# Closed: the auth tables/columns now have a revision

The login work first added `refresh_tokens` (`app/models/refresh_token.py`) and the
`password_hash`/`is_active`/`must_change_password`/`last_login_at` columns on `users`
(`app/models/user.py`) with no migration. `alembic/versions/0052_add_user_credentials_and_refresh_tokens.py`
(revision `AddUserCredentialsAndRefreshTokens`, `down_revision = "CreateTenantAuditLog"`) closes
that gap: it `op.add_column`s the four `users` columns, creates `refresh_tokens` and its
`idx_refresh_tokens_user` index, and has a working `downgrade`. This is the one revision in the
repo that alters a table created by an earlier batch (`users`, from `0002_create_users.py`) —
done additively, as a new revision, rather than by editing `0002`. See
[Auth](/modules/auth.md) and [Conventions](/conventions.md).

# 0053 is the repo's first data-only revision

`0053_unify_contract_status_flow.py` (revision `UnifyContractStatusFlow`, `down_revision =
"AddUserCredentialsAndRefreshTokens"`) creates and alters nothing: it is six `op.execute`
`UPDATE`s that bring existing rows onto the unified status vocabulary described in
[Contract Status](/modules/contract-status.md). Its `downgrade` is deliberately a no-op —
two old values fold into one going forward, and the application still reads the old spellings.
A migration that only moves data is still a new numbered revision, never an edit to an earlier
one.

# 0054 adds a column to an earlier batch's table

`0054_archive_approval_matrix_configs.py` (revision `ArchiveApprovalMatrixConfigs`,
`down_revision = "UnifyContractStatusFlow"`) is a single `op.add_column` putting `archived_at`
on `approval_matrix_configs` (created by the `uc6-uc7-combined` batch), with a matching
`op.drop_column` downgrade. Like `0052` it alters an earlier batch's table additively, as a new
revision — see [Approval Matrix](/modules/approval-matrix.md) for why the column exists.

# Seeding happens in app code, not in migrations

No migration uses `op.bulk_insert`. The repo's only reference-data seeder is
`app.repositories.settings_notifications.ensure_seeded`, called from the application layer on
`GET /settings/notifications` and guarded by an existence check per event name. See
[Conventions](/conventions.md) and [Notifications](/modules/notifications.md).
