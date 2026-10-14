---
type: Module
title: migrations
description: 51 Alembic migrations, one table per revision, applied automatically at app startup, never reordered or edited once merged.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/alembic/versions
tags: [backend, migrations, alembic, postgresql]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ 700de34973c81dd98062f0bef469b620e6fc976b
    title: Codebase knowledge graph
status: stable
---

# Structure

`alembic/versions/0001_create_tenants.py` through `0051_create_tenant_audit_log.py`, applied in
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

# Convention: additive only

No migration in this repo edits or drops a table created by an earlier migration (verified by
file naming and content of the sampled 0042 file: pure `CREATE TABLE`, no `ALTER`/`DROP` against
pre-existing tables except the one explicitly named `0031_alter_contracts_for_lifecycle.py`,
which predates and is owned by the `life-cycle-uc8-uc9` batch itself, not a later batch
rewriting an earlier one). New modules must follow the same pattern: add new numbered revisions,
never touch an existing one.

# Gap: the auth tables/columns are model-only

The login work added `refresh_tokens` (`app/models/refresh_token.py`) and the
`password_hash`/`is_active`/`must_change_password`/`last_login_at` columns on `users`
(`app/models/user.py`) **without** a revision after `0051` — the highest revision is still
`0051_create_tenant_audit_log.py`. Tests pass because `tests/conftest.py` builds the schema from
`Base.metadata`, but a Postgres database brought up by `alembic upgrade head` will lack them.
Any fix must be a new `0052_…` revision, never an edit to `0002_create_users.py`. See
[Conventions > Deviation](/conventions.md#deviation-found-auth-schema-has-no-migration) and
[Auth](/modules/auth.md).

# No reference-data seeding found

See [Conventions > Deviation](/conventions.md#deviation-found-no-idempotent-reference-data-seeding-in-code)
— no migration or startup code inserts seed/reference rows despite CLAUDE.md requiring
idempotent seeding where reference data exists.
