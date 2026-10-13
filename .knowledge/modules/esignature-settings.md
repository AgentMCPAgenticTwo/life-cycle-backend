---
type: Module
title: esignature-settings
description: Tenant-wide e-signature configuration (single GET/PUT resource) consumed by the signing-session flow.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/esignature_settings.py
tags: [backend, uc6-uc7-combined, esignature, settings]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/esignature_settings.py`, `app/services/esignature_settings.py`,
`app/repositories/esignature_settings.py`, `app/schemas/esignature_settings.py`.

# Endpoints

* `GET /esignature-settings` -> `EsignatureSettingsResponse`
* `PUT /esignature-settings` -> `EsignatureSettingsResponse` (`UpdateEsignatureSettingsRequest`)

# Relationships

Read by [Signing](/modules/signing.md) when sending/verifying/reminding signers. Distinct
resource from [Settings](/modules/settings.md)'s `tenant_notification_settings` /
`tenant_integrations` — this one is specific to e-signature behavior, added in the
`uc6-uc7-combined` batch, well before the generic `lifecycle-uc10-uc11` settings surface.
