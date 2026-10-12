"""Exercises every endpoint this task owns (`/api/v1/signing-sessions/{sessionId}` and its
`otp/verify`, `otp/resend`, `sign`, `decline` sub-actions) against a real in-memory database:
sequential signing order (UC7-BR-001), OTP verification/lockout (UC7-BR-003/016, UC7-AF-001,
UC7-FV-002), decline halting routing (UC7-AF-002, UC7-BR-008/018), auto-expiry and resend
(UC7-BR-020), applying a signature and auto-Executed on the final signer (UC7-BR-004/007/017/
019, UC7-FV-003), and the role/auth matrix (UC7-BR-011/014).
"""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.esignature import Signer
from app.models.tenant import Tenant
from app.models.user import User

SIGNER = "SIGNER"
CONTRACT_OWNER = "CONTRACT_OWNER"
APPROVER = "APPROVER"


def _headers(role: str, user_id) -> dict:
    return {"X-User-Role": role, "X-User-Id": str(user_id)}


def _seed_tenant(db_session) -> Tenant:
    tenant = Tenant(id=uuid.uuid4(), name="Acme Co", high_risk_threshold=70, created_by=uuid.uuid4(), updated_by=uuid.uuid4())
    db_session.add(tenant)
    return tenant


def _seed_user(db_session, tenant_id, role: str) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=f"{role.title()} User",
        email=f"{role.lower()}-{uuid.uuid4()}@acme.test",
        role=role,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )
    db_session.add(user)
    return user


def _seed_counterparty(db_session, tenant_id) -> Counterparty:
    cp = Counterparty(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Globex",
        email="contact@globex.test",
        company="Globex Corp",
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )
    db_session.add(cp)
    return cp


def _seed_contract(db_session, tenant_id, owner_id, counterparty_id, status: str = "Sent") -> Contract:
    from datetime import date

    today = date(2026, 1, 1)
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contract_name="Master Services Agreement",
        contract_type="MSA",
        industry="Service",
        counterparty_id=counterparty_id,
        contract_owner_id=owner_id,
        contract_value="100000.00",
        currency="USD",
        start_date=today,
        end_date=today.replace(year=2027),
        renewal_type="Manual",
        assigned_date=today,
        due_date=today.replace(year=2027),
        status=status,
        risk_score=42,
        created_by=owner_id,
        updated_by=owner_id,
    )
    db_session.add(contract)
    return contract


def _seed_signer(
    db_session,
    contract_id,
    order: int,
    *,
    status: str = "Sent",
    otp_code: str = "123456",
    otp_attempts: int = 0,
    otp_locked_until=None,
    link_expires_at=None,
) -> Signer:
    now = datetime.now(timezone.utc)
    signer = Signer(
        id=uuid.uuid4(),
        contract_id=contract_id,
        signer_name=f"Signer {order}",
        signer_email=f"signer{order}@example.com",
        signer_type="Internal",
        signing_order=order,
        signature_method="In-built E-signature",
        reminder_frequency_days=3,
        signer_status=status,
        otp_hash=hashlib.sha256(otp_code.encode()).hexdigest(),
        otp_attempts=otp_attempts,
        otp_locked_until=otp_locked_until,
        link_token=secrets_token(),
        link_expires_at=link_expires_at or (now + timedelta(days=7)),
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )
    db_session.add(signer)
    return signer


def secrets_token() -> str:
    return uuid.uuid4().hex


def _setup(db_session, *, contract_status: str = "Sent"):
    tenant = _seed_tenant(db_session)
    owner = _seed_user(db_session, tenant.id, CONTRACT_OWNER)
    other_owner = _seed_user(db_session, tenant.id, CONTRACT_OWNER)
    cp = _seed_counterparty(db_session, tenant.id)
    contract = _seed_contract(db_session, tenant.id, owner.id, cp.id, status=contract_status)
    db_session.commit()
    return tenant, owner, other_owner, contract


# ---- GET session: role/auth matrix and sequencing (UC7-BR-001/011/014) -------------------


def test_get_session_missing_role_header_401(db_client):
    resp = db_client.get(f"/api/v1/signing-sessions/{uuid.uuid4()}")
    assert resp.status_code == 401


def test_get_session_disallowed_role_403(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1)
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/signing-sessions/{s1.id}", headers=_headers(APPROVER, uuid.uuid4())
    )
    assert resp.status_code == 403


def test_get_session_unknown_session_404(db_session, db_client):
    _setup(db_session)
    resp = db_client.get(
        f"/api/v1/signing-sessions/{uuid.uuid4()}", headers=_headers(SIGNER, uuid.uuid4())
    )
    assert resp.status_code == 404


def test_get_session_pending_signer_not_found(db_session, db_client):
    # A signer who hasn't been sent a link yet has no active session.
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Pending")
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/signing-sessions/{s1.id}", headers=_headers(SIGNER, uuid.uuid4())
    )
    assert resp.status_code == 404


def test_get_session_blocked_when_prior_signer_unsigned(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, 1, status="Sent")
    s2 = _seed_signer(db_session, contract.id, 2, status="Sent")
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/signing-sessions/{s2.id}", headers=_headers(SIGNER, uuid.uuid4())
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["isCurrentTurn"] is False
    assert "wait" in body["blockedMessage"].lower()
    assert body["documentUrl"] is None
    assert body["signaturePadAvailable"] is False


def test_get_session_current_turn_before_otp_hides_document(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Sent")
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/signing-sessions/{s1.id}", headers=_headers(SIGNER, uuid.uuid4())
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["isCurrentTurn"] is True
    assert body["otpVerified"] is False
    assert body["documentUrl"] is None
    assert body["signaturePadAvailable"] is False
    assert body["blockedMessage"] is None


def test_get_session_expired_link_hides_everything(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(
        db_session, contract.id, 1, status="Sent",
        link_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/signing-sessions/{s1.id}", headers=_headers(SIGNER, uuid.uuid4())
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["signerStatus"] == "Expired"
    assert body["linkExpired"] is True
    assert "expired" in body["blockedMessage"].lower()
    assert body["documentUrl"] is None


# ---- OTP verify (UC7-BR-003/016, UC7-AF-001, UC7-FV-002) ---------------------------------


def test_verify_otp_invalid_format_400(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Sent")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/otp/verify",
        json={"otpCode": "12AB"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 400
    db_session.refresh(s1)
    assert s1.signer_status == "Sent"


def test_verify_otp_success_reveals_document_and_advances_status(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Sent", otp_code="654321")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/otp/verify",
        json={"otpCode": "654321"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["signerStatus"] == "Viewed"
    assert body["documentUrl"]
    assert body["signaturePadAvailable"] is True
    assert body["errorMessage"] is None


def test_verify_otp_wrong_code_does_not_advance_status(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Sent", otp_code="654321")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/otp/verify",
        json={"otpCode": "111111"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["signerStatus"] == "Sent"
    assert body["documentUrl"] is None
    assert body["attemptsRemaining"] == 2
    assert body["errorMessage"]


def test_verify_otp_third_failure_locks_link_for_15_minutes(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Sent", otp_code="654321", otp_attempts=2)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/otp/verify",
        json={"otpCode": "111111"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 200
    body = resp.json()
    # UC7-AF-001: status remains unchanged (not advanced to Viewed) since verification failed.
    assert body["signerStatus"] == "Sent"
    assert body["attemptsRemaining"] == 0
    assert body["lockedUntil"] is not None
    assert "request a new code" in body["errorMessage"].lower()

    # Attempting again before the lockout window elapses is denied outright.
    resp2 = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/otp/verify",
        json={"otpCode": "654321"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp2.status_code == 403


def test_verify_otp_blocked_when_prior_signer_unsigned(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, 1, status="Sent")
    s2 = _seed_signer(db_session, contract.id, 2, status="Sent", otp_code="222222")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s2.id}/otp/verify",
        json={"otpCode": "222222"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 403


# ---- OTP resend (UC7-BR-020) --------------------------------------------------------------


def test_resend_otp_after_expiry_resets_status_to_sent(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(
        db_session, contract.id, 1, status="Sent",
        link_expires_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/otp/resend", headers=_headers(SIGNER, uuid.uuid4())
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["signerStatus"] == "Sent"
    assert body["linkExpired"] is False


def test_resend_otp_by_contract_owner_non_owner_403(db_session, db_client):
    tenant, owner, other_owner, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Expired")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/otp/resend",
        headers=_headers(CONTRACT_OWNER, other_owner.id),
    )
    assert resp.status_code == 403


def test_resend_otp_blocked_once_signed(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Signed")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/otp/resend", headers=_headers(SIGNER, uuid.uuid4())
    )
    assert resp.status_code == 409


# ---- Apply signature (UC7-BR-001/004/007/017/019, UC7-FV-003) ------------------------------


def test_sign_requires_otp_verified_first(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Sent")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/sign",
        json={"signatureData": "base64...", "signatureType": "Draw"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 409


def test_sign_blank_signature_pad_400(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Viewed")
    s1.otp_verified_at = datetime.now(timezone.utc)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/sign",
        json={"signatureData": "   ", "signatureType": "Draw"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 400


def test_sign_not_my_turn_blocked(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, 1, status="Sent")
    s2 = _seed_signer(db_session, contract.id, 2, status="Viewed")
    s2.otp_verified_at = datetime.now(timezone.utc)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s2.id}/sign",
        json={"signatureData": "base64...", "signatureType": "Draw"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 403


def test_sign_advances_to_next_signer_without_executing(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Viewed")
    s1.otp_verified_at = datetime.now(timezone.utc)
    _seed_signer(db_session, contract.id, 2, status="Pending")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/sign",
        json={"signatureData": "base64...", "signatureType": "Draw"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["signerStatus"] == "Signed"
    assert body["contractStatus"] == "Sent"
    assert body["nextSignerId"] is not None

    db_session.refresh(contract)
    assert contract.status == "Sent"


def test_sign_last_signer_executes_contract(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, 1, status="Signed")
    s2 = _seed_signer(db_session, contract.id, 2, status="Viewed")
    s2.otp_verified_at = datetime.now(timezone.utc)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s2.id}/sign",
        json={"signatureData": "base64...", "signatureType": "Type"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contractStatus"] == "Executed"
    assert body["nextSignerId"] is None

    db_session.refresh(contract)
    assert contract.status == "Executed"


# ---- Decline (UC7-AF-002, UC7-BR-008/018) --------------------------------------------------


def test_decline_requires_viewed_status(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Sent")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/decline",
        json={"reason": "Terms unacceptable"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 409


def test_decline_missing_reason_400(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Viewed")
    s1.otp_verified_at = datetime.now(timezone.utc)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/decline",
        json={"reason": ""},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 400


def test_decline_halts_routing_and_sets_contract_declined(db_session, db_client):
    tenant, owner, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, 1, status="Viewed")
    s1.otp_verified_at = datetime.now(timezone.utc)
    s2 = _seed_signer(db_session, contract.id, 2, status="Pending")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/signing-sessions/{s1.id}/decline",
        json={"reason": "Pricing terms unacceptable"},
        headers=_headers(SIGNER, uuid.uuid4()),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["signerStatus"] == "Declined"
    assert body["contractStatus"] == "SignatureDeclined"
    assert body["reason"] == "Pricing terms unacceptable"

    db_session.refresh(contract)
    assert contract.status == "SignatureDeclined"

    # UC7-BR-018 AC3: routing halted -- the next signer in order was never sent a link, so
    # their session never activates (still Pending, no OTP/link issued).
    db_session.refresh(s2)
    assert s2.signer_status == "Pending"
    resp2 = db_client.get(
        f"/api/v1/signing-sessions/{s2.id}", headers=_headers(SIGNER, uuid.uuid4())
    )
    assert resp2.status_code == 404
