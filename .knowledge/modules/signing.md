---
type: Module
title: signing
description: Contract signer management and the OTP-based signing-session flow (view, verify, sign, decline) plus the audit certificate produced once fully executed.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/signers.py
tags: [backend, uc6-uc7-combined, signing, esignature]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ a01dca2cd1cf0d1b42a73a36cc3fce4dadcc0c75
    title: Codebase knowledge graph
status: stable
---

# Files

`app/routers/signers.py`, `app/routers/signing_sessions.py`,
`app/services/signers.py`, `app/services/signing_sessions.py`,
`app/repositories/signers.py`, `app/repositories/signing_sessions.py`,
`app/schemas/signer.py`, `app/schemas/signing_session.py`, `app/models/esignature.py`.

# Endpoints

* `GET/POST /contracts/{contractId}/signers`,
  `PUT/DELETE /contracts/{contractId}/signers/{signerId}`,
  `POST /contracts/{contractId}/signers/send`
* `GET /signing-sessions/{sessionId}`, `POST .../otp/verify`, `POST .../otp/resend`,
  `POST .../sign`, `POST .../decline`
* `GET /contracts/{contractId}/audit-certificate`

# Hotspot

`app.repositories.signing_sessions.list_by_contract` — fan-in 8.

# Relationships

Signers are added to contracts that have cleared [Approvals](/modules/approvals.md); e-signature
behavior (reminder cadence, OTP expiry) is configured via
[E-signature Settings](/modules/esignature-settings.md).
