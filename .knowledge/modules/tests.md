---
type: Module
title: tests
description: 32 pytest files, one per resource/concern, using shared fixtures for tenant/user seeding and header construction.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/tests
tags: [backend, tests, pytest]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Structure

`tests/conftest.py` plus one `test_<resource>.py` file per router module (31 files), covering
every resource named in [modules/index.md](/modules/index.md) (e.g. `test_contracts.py`,
`test_approvals.py`, `test_tracker_ownership.py`, `test_settings_users.py`) plus cross-cutting
`test_auth.py`, `test_errors.py`, `test_health.py`, `test_pagination.py`, `test_persistence.py`.

# Shared fixture patterns (graph clusters)

Six of the twelve graph clusters are test-only, built around shared helpers repeated per test
file rather than imported from one place: `_seed_tenant_and_user`, `_headers`, `_setup`/
`_setup_basic`, `_seed_user`, `_seed_tenant`, `_seed_signer`, `_valid_payload`/`_add_payload`.
Each test file defines its own local copies of these helpers (high within-file cohesion, 0.62-0.90)
rather than sharing a single fixture module — consistent with the one-file-per-resource
generation pattern used for the source tree.

# Run

```bash
pytest -q
```

# Relationships

Exercises every module in [modules/index.md](/modules/index.md) against the conventions in
[Conventions](/conventions.md), in particular the role/header 401/403 matrix from
[App Core](/modules/app-core.md).
