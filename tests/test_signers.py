"""Exercises every endpoint this task owns (`/api/v1/contracts/{contractId}/signers`,
`/api/v1/contracts/{contractId}/audit-certificate`) against a real in-memory database: the
role/ownership matrix, mandatory-field and format validation, signing-order uniqueness, the
Signer List lock after the first signature, Send for Signature's precondition/provider-failure
behavior, and the audit certificate's Executed-only gate -- see TASK.md's stories
UC7-AF-004..006, UC7-BR-002/004/005/009/010/012..015/019, UC7-FV-001/005, UC7-GC-001, UC7-MF-001.
"""
import uuid

from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.esignature import EsignatureSettings, Signer
from app.models.tenant import Tenant
from app.models.user import User

CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
TENANT_ADMIN = "TENANT_ADMIN"
APPROVER = "APPROVER"


def _headers(role: str, user_id: uuid.UUID) -> dict:
    return {"X-User-Role": role, "X-User-Id": str(user_id)}


def _seed_tenant(db_session) -> Tenant:
    tenant = Tenant(id=uuid.uuid4(), name="Acme Co", high_risk_threshold=70, created_by=uuid.uuid4(), updated_by=uuid.uuid4())
    db_session.add(tenant)
    return tenant


def _seed_user(db_session, tenant_id: uuid.UUID, role: str) -> User:
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


def _seed_counterparty(db_session, tenant_id: uuid.UUID) -> Counterparty:
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


def _seed_contract(
    db_session, tenant_id: uuid.UUID, owner_id: uuid.UUID, counterparty_id: uuid.UUID, status: str = "Ready For Signature"
) -> Contract:
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
    db_session, contract_id: uuid.UUID, order: int, *, status: str = "Pending", method: str = "In-built E-signature"
) -> Signer:
    signer = Signer(
        id=uuid.uuid4(),
        contract_id=contract_id,
        signer_name=f"Signer {order}",
        signer_email=f"signer{order}@example.com",
        signer_type="Internal",
        signing_order=order,
        signature_method=method,
        signer_status=status,
        otp_attempts=0,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )
    db_session.add(signer)
    return signer


def _setup(db_session, *, contract_status: str = "Ready For Signature"):
    tenant = _seed_tenant(db_session)
    owner = _seed_user(db_session, tenant.id, CONTRACT_OWNER)
    other_owner = _seed_user(db_session, tenant.id, CONTRACT_OWNER)
    legal = _seed_user(db_session, tenant.id, LEGAL_REVIEWER)
    admin = _seed_user(db_session, tenant.id, TENANT_ADMIN)
    cp = _seed_counterparty(db_session, tenant.id)
    contract = _seed_contract(db_session, tenant.id, owner.id, cp.id, status=contract_status)
    db_session.commit()
    return tenant, owner, other_owner, legal, admin, contract


# ---- role / auth matrix -----------------------------------------------------------------


def test_list_signers_missing_role_header_401(db_client):
    resp = db_client.get(f"/api/v1/contracts/{uuid.uuid4()}/signers")
    assert resp.status_code == 401


def test_list_signers_disallowed_role_403(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    approver = _seed_user(db_session, tenant.id, APPROVER)
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract.id}/signers", headers=_headers(APPROVER, approver.id)
    )
    assert resp.status_code == 403


def test_list_signers_unknown_contract_404(db_session, db_client):
    tenant, owner, _, _, _, _contract = _setup(db_session)
    resp = db_client.get(
        f"/api/v1/contracts/{uuid.uuid4()}/signers", headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 404


def test_list_signers_non_owner_contract_owner_403(db_session, db_client):
    tenant, owner, other_owner, _, _, contract = _setup(db_session)
    resp = db_client.get(
        f"/api/v1/contracts/{contract.id}/signers", headers=_headers(CONTRACT_OWNER, other_owner.id)
    )
    assert resp.status_code == 403


def test_list_signers_legal_reviewer_and_tenant_admin_allowed(db_session, db_client):
    tenant, owner, _, legal, admin, contract = _setup(db_session)
    for user in (legal, admin):
        resp = db_client.get(
            f"/api/v1/contracts/{contract.id}/signers", headers=_headers(user.role, user.id)
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["contractId"] == str(contract.id)
        assert body["signers"] == []
        assert body["sendForSignatureEnabled"] is False
        assert body["signingOrderLocked"] is False


# ---- Add signer (UC7-FV-001, UC7-BR-002, UC7-BR-010) -------------------------------------


def _add_payload(**overrides):
    payload = {
        "signerName": "Jane Signer",
        "signerEmail": "jane@example.com",
        "signerType": "Internal",
        "signingOrder": 1,
        "signatureMethod": "In-built E-signature",
    }
    payload.update(overrides)
    return payload


def test_add_signer_happy_path_enables_send_for_signature(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(),
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["signerName"] == "Jane Signer"
    assert body["signerStatus"] == "Pending"
    assert body["reminderFrequencyDays"] == 3  # UC7-FV-001: default of 3 days

    listing = db_client.get(
        f"/api/v1/contracts/{contract.id}/signers", headers=_headers(CONTRACT_OWNER, owner.id)
    ).json()
    assert listing["sendForSignatureEnabled"] is True


def test_add_signer_uses_tenant_configured_reminder_frequency(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    db_session.add(
        EsignatureSettings(
            id=uuid.uuid4(),
            tenant_id=tenant.id,
            reminder_frequency_days=5,
            default_signature_provider="In-built E-signature",
            created_by=owner.id,
            updated_by=owner.id,
        )
    )
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(),
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 201
    assert resp.json()["reminderFrequencyDays"] == 5


def test_add_signer_invalid_email_400(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(signerEmail="not-an-email"),
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 400


def test_add_signer_invalid_signer_type_400(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(signerType="Vendor"),
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 400


def test_add_signer_invalid_signature_method_400(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(signatureMethod="PaperMail"),
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 400


def test_add_signer_missing_mandatory_field_400(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    payload = _add_payload()
    del payload["signerName"]
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers", json=payload, headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 400


def test_add_signer_duplicate_signing_order_400(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, order=1)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(signingOrder=1),
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 400


def test_add_signer_non_owner_403(db_session, db_client):
    tenant, owner, other_owner, _, _, contract = _setup(db_session)
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(),
        headers=_headers(CONTRACT_OWNER, other_owner.id),
    )
    assert resp.status_code == 403


def test_add_signer_legal_reviewer_role_403(db_session, db_client):
    tenant, owner, _, legal, _, contract = _setup(db_session)
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(),
        headers=_headers(LEGAL_REVIEWER, legal.id),
    )
    assert resp.status_code == 403


def test_add_signer_blocked_once_locked(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, order=1, status="Signed")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(signingOrder=2),
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 403
    assert "locked" in resp.json()["error"].lower()


def test_add_signer_blocked_once_executed(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session, contract_status="Executed")
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers",
        json=_add_payload(),
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 403


# ---- Update signer (UC7-AF-004, UC7-BR-004) ----------------------------------------------


def test_update_signer_reorder_allowed_before_signing(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, order=1)
    _seed_signer(db_session, contract.id, order=2)
    db_session.commit()
    resp = db_client.put(
        f"/api/v1/contracts/{contract.id}/signers/{s1.id}",
        json={"signingOrder": 3},
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 200
    assert resp.json()["signingOrder"] == 3


def test_update_signer_reorder_blocked_after_first_signature(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, order=1, status="Signed")
    _seed_signer(db_session, contract.id, order=2)
    db_session.commit()
    resp = db_client.put(
        f"/api/v1/contracts/{contract.id}/signers/{s1.id}",
        json={"signingOrder": 5},
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "Signing order cannot be changed once signing has started."


def test_update_signer_other_fields_blocked_after_first_signature(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, order=1, status="Signed")
    _seed_signer(db_session, contract.id, order=2)
    db_session.commit()
    resp = db_client.put(
        f"/api/v1/contracts/{contract.id}/signers/{s1.id}",
        json={"signerName": "New Name"},
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 403


def test_update_signer_duplicate_order_400(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, order=1)
    _seed_signer(db_session, contract.id, order=2)
    db_session.commit()
    resp = db_client.put(
        f"/api/v1/contracts/{contract.id}/signers/{s1.id}",
        json={"signingOrder": 2},
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 400


def test_update_signer_not_found_404(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    resp = db_client.put(
        f"/api/v1/contracts/{contract.id}/signers/{uuid.uuid4()}",
        json={"signerName": "X"},
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 404


# ---- Delete signer (UC7-BR-004, UC7-BR-010) ----------------------------------------------


def test_delete_signer_allowed_before_signing(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, order=1)
    db_session.commit()
    resp = db_client.delete(
        f"/api/v1/contracts/{contract.id}/signers/{s1.id}", headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 200
    listing = db_client.get(
        f"/api/v1/contracts/{contract.id}/signers", headers=_headers(CONTRACT_OWNER, owner.id)
    ).json()
    assert listing["signers"] == []


def test_delete_signer_blocked_after_first_signature(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    s1 = _seed_signer(db_session, contract.id, order=1, status="Signed")
    db_session.commit()
    resp = db_client.delete(
        f"/api/v1/contracts/{contract.id}/signers/{s1.id}", headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 403


# ---- Send for signature (UC7-BR-002, UC7-BR-015, UC7-AF-005, UC7-MF-001) -----------------


def test_send_for_signature_blocked_when_no_signers(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers/send", json={}, headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 400


def test_send_for_signature_blocked_when_precondition_not_met(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session, contract_status="Draft")
    _seed_signer(db_session, contract.id, order=1)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers/send", json={}, headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 409


def test_send_for_signature_happy_path_transitions_contract_and_first_signer(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, order=1)
    _seed_signer(db_session, contract.id, order=2)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers/send", json={}, headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contractStatus"] == "Sent"
    assert body["errorMessage"] is None
    by_order = {s["signingOrder"]: s for s in body["signers"]}
    assert by_order[1]["signerStatus"] == "Sent"
    assert by_order[1]["linkExpiresAt"] is not None
    assert by_order[2]["signerStatus"] == "Pending"


def test_send_for_signature_integrated_provider_connection_failure(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, order=1, method="DocuSign")
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers/send", json={}, headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contractStatus"] == "SignatureConnectionFailed"
    assert "Unable to connect" in body["errorMessage"]
    assert body["signers"][0]["signerStatus"] == "Pending"

    # contract status is unchanged and the Contract Owner can retry.
    db_session.refresh(contract)
    assert contract.status == "Ready For Signature"


def test_send_for_signature_retry_with_inbuilt_option_succeeds(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, order=1, method="DocuSign")
    db_session.commit()
    db_client.post(
        f"/api/v1/contracts/{contract.id}/signers/send", json={}, headers=_headers(CONTRACT_OWNER, owner.id)
    )
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers/send",
        json={"signatureMethod": "In-built E-signature"},
        headers=_headers(CONTRACT_OWNER, owner.id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contractStatus"] == "Sent"
    assert body["signers"][0]["signatureMethod"] == "In-built E-signature"


def test_send_for_signature_non_owner_403(db_session, db_client):
    tenant, owner, other_owner, _, _, contract = _setup(db_session)
    _seed_signer(db_session, contract.id, order=1)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers/send",
        json={},
        headers=_headers(CONTRACT_OWNER, other_owner.id),
    )
    assert resp.status_code == 403


def test_send_for_signature_blocked_when_executed(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session, contract_status="Executed")
    _seed_signer(db_session, contract.id, order=1)
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract.id}/signers/send", json={}, headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 403


# ---- Audit certificate (UC7-BR-005, UC7-BR-009, UC7-BR-019, UC7-FV-005) ------------------


def test_audit_certificate_not_available_before_executed(db_session, db_client):
    tenant, owner, _, _, _, contract = _setup(db_session, contract_status="Sent")
    _seed_signer(db_session, contract.id, order=1)
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract.id}/audit-certificate", headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 404


def test_audit_certificate_available_once_executed(db_session, db_client):
    tenant, owner, _, legal, _, contract = _setup(db_session, contract_status="Executed")
    _seed_signer(db_session, contract.id, order=1, status="Signed")
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract.id}/audit-certificate", headers=_headers(CONTRACT_OWNER, owner.id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contractId"] == str(contract.id)
    assert body["downloadUrl"]
    assert len(body["signers"]) == 1
    assert body["signers"][0]["signerStatus"] == "Signed"

    # Legal Reviewer can also download (read-only, no ownership restriction).
    resp2 = db_client.get(
        f"/api/v1/contracts/{contract.id}/audit-certificate", headers=_headers(LEGAL_REVIEWER, legal.id)
    )
    assert resp2.status_code == 200


def test_audit_certificate_non_owner_contract_owner_403(db_session, db_client):
    tenant, owner, other_owner, _, _, contract = _setup(db_session, contract_status="Executed")
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract.id}/audit-certificate",
        headers=_headers(CONTRACT_OWNER, other_owner.id),
    )
    assert resp.status_code == 403


def test_audit_certificate_disallowed_role_403(db_session, db_client):
    tenant, owner, _, _, admin, contract = _setup(db_session, contract_status="Executed")
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract.id}/audit-certificate", headers=_headers(TENANT_ADMIN, admin.id)
    )
    assert resp.status_code == 403
