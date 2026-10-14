---
type: Module
title: signing
description: Contract signer management and the OTP-based signing-session flow (view, verify, sign, decline) plus the audit certificate produced once fully executed.
resource: https://github.com/AgentMCPAgenticThree/life-cycle-backend/tree/main/app/routers/signers.py
tags: [backend, uc6-uc7-combined, signing, esignature]
generated: { by: sage-maintenance/claude-code, at: 2026-10-13T06:27:43Z }
updated: { by: sage-maintenance/claude-code, at: 2026-10-14T12:47:46Z }
sources:
  - id: cbm-graph
    resource: codebase-memory-mcp project life-cycle-backend @ b0c64d78730b6ed271020fb3e7d89002e374f6da
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

# Contract status vs signer status

Send for Signature is available only while the contract is `Pending Signature`
(`contract_status.is_pending_signature`, which also accepts the legacy `Ready For Signature` /
`Sent` rows), and **sending does not change the contract status** — `Sent`, `Viewed`, `Signed`
and `Declined` are per-signer values. `_already_sent` (any signer past `Pending`) blocks a second
send and clears `sendForSignatureEnabled`; the two 409 texts are `_SEND_PRECONDITION_MESSAGE`
and `_ALREADY_SENT_MESSAGE`. `decline_signature` writes
`contract_status.SIGNATURE_DECLINED` (spaced), and the session responses now echo
`contract.status` verbatim instead of a hard-coded `Sent`/`SignatureDeclined`. See
[Contract Status](/modules/contract-status.md).

# Hotspot

`app.repositories.signing_sessions.list_by_contract` — fan-in 8.

# Relationships

Signers are added to contracts that have cleared [Approvals](/modules/approvals.md); e-signature
behavior (reminder cadence, OTP expiry) is configured via
[E-signature Settings](/modules/esignature-settings.md).

# Notifications

Three of this module's actions emit events through
[Notifications](/modules/notifications.md), each after its own commit:
`signers.send_for_signature` and `signing_sessions.apply_signature` (to the next signer in
order) send `Contract Sent for Signature`, `apply_signature` also sends `Contract Signed` once
the last signer completes, and `signing_sessions.decline_signature` sends
`Contract Signature Declined`. Delivery failures are swallowed there, so an unreachable mail
server cannot roll back a recorded signature.
