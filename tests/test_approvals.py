"""Exercises every endpoint this task owns (`/api/v1/approvals`) against a real in-memory
database: the role matrix, visibility per role, the Approve/Reject/Send Back action with its
sequence/comments/ownership rules, delegation eligibility, and the immutable history tab --
see TASK.md's stories UC6-AF-001..006, UC6-BR-001..024, UC6-FV-001, UC6-MF-001.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from app.models.approval import (
    Approval,
    ApprovalDelegation,
    ApprovalMatrixConfig,
    ApprovalMatrixStep,
    ApprovalStepInstance,
)
from app.models.contract import Contract
from app.models.contract_lifecycle import ActivityLogEntry
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers

APPROVER = "APPROVER"
TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
SIGNER = "SIGNER"


def _headers(role: str, user_id: uuid.UUID) -> dict:
    return auth_headers(role, user_id)


def _seed_user(db_session, tenant_id: uuid.UUID, role: str, name: str | None = None) -> User:
    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name=name or f"{role.title()} User",
        email=f"{role.lower()}-{uuid.uuid4()}@acme.test",
        role=role,
        created_by=uuid.uuid4(),
        updated_by=uuid.uuid4(),
    )
    db_session.add(user)
    return user


def _seed_tenant(db_session) -> Tenant:
    tenant = Tenant(id=uuid.uuid4(), name="Acme Co", high_risk_threshold=70, created_by=uuid.uuid4(), updated_by=uuid.uuid4())
    db_session.add(tenant)
    return tenant


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


def _seed_contract(db_session, tenant_id: uuid.UUID, owner_id: uuid.UUID, counterparty_id: uuid.UUID) -> Contract:
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
        status="Pending Approval",
        risk_score=42,
        created_by=owner_id,
        updated_by=owner_id,
    )
    db_session.add(contract)
    return contract


def _seed_approval(
    db_session,
    contract: Contract,
    owner_id: uuid.UUID,
    *,
    config_id=None,
    current_step_number: int = 1,
    total_steps: int = 2,
    status: str = "PendingApproval",
) -> Approval:
    approval = Approval(
        id=uuid.uuid4(),
        contract_id=contract.id,
        contract_owner_id=owner_id,
        config_id=config_id,
        current_step_number=current_step_number,
        total_steps=total_steps,
        status=status,
        ai_risk_score=55,
        key_terms_summary="Net 30 payment terms.",
        deviations_from_standard="Liability cap raised to 2x fees.",
        created_by=owner_id,
        updated_by=owner_id,
    )
    db_session.add(approval)
    return approval


def _seed_step_instance(db_session, approval: Approval, step_number: int, approver_id: uuid.UUID, status: str = "Pending") -> ApprovalStepInstance:
    instance = ApprovalStepInstance(
        id=uuid.uuid4(),
        approval_id=approval.id,
        step_number=step_number,
        approver_user_id=approver_id,
        status=status,
        created_by=approver_id,
        updated_by=approver_id,
    )
    db_session.add(instance)
    return instance


def _setup_basic(db_session, *, current_step_number: int = 1, total_steps: int = 2, status: str = "PendingApproval"):
    tenant = _seed_tenant(db_session)
    owner = _seed_user(db_session, tenant.id, CONTRACT_OWNER)
    approver = _seed_user(db_session, tenant.id, APPROVER, name="Finance Approver")
    cp = _seed_counterparty(db_session, tenant.id)
    contract = _seed_contract(db_session, tenant.id, owner.id, cp.id)
    approval = _seed_approval(
        db_session, contract, owner.id, current_step_number=current_step_number, total_steps=total_steps, status=status
    )
    db_session.commit()
    _seed_step_instance(db_session, approval, current_step_number, approver.id)
    db_session.commit()
    return tenant, owner, approver, contract, approval


# ---- role / auth matrix ----------------------------------------------------------------


def test_list_requires_role_header(db_client):
    assert db_client.get("/api/v1/approvals").status_code == 401


def test_list_rejects_signer_role(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    # Authentication resolves the caller from `users`, so the SIGNER has to be a real row --
    # a bare random uuid is a 401 before the role check under test is reached.
    signer = _seed_user(db_session, tenant.id, SIGNER)
    db_session.commit()
    response = db_client.get("/api/v1/approvals", headers=_headers(SIGNER, signer.id))
    assert response.status_code == 403


def test_actions_rejects_non_approver_roles(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(TENANT_ADMIN, owner.id),
    )
    assert response.status_code == 403


# ---- list -------------------------------------------------------------------------------


def test_list_empty_state_for_approver(db_client, db_session):
    tenant = _seed_tenant(db_session)
    user = _seed_user(db_session, tenant.id, APPROVER)
    db_session.commit()
    response = db_client.get("/api/v1/approvals", headers=_headers(APPROVER, user.id))
    assert response.status_code == 200
    body = response.json()
    assert body["isEmpty"] is True
    assert body["emptyMessage"] == "No contracts are currently awaiting your approval."
    assert body["items"] == []


def test_list_shows_pending_approval_to_assigned_approver(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    response = db_client.get("/api/v1/approvals", headers=_headers(APPROVER, approver.id))
    assert response.status_code == 200
    body = response.json()
    assert body["isEmpty"] is False
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["contractTitle"] == "Master Services Agreement"
    assert item["counterpartyName"] == "Globex"
    assert item["status"] == "PendingApproval"


def test_list_hides_from_unrelated_approver(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    other_approver = _seed_user(db_session, tenant.id, APPROVER)
    db_session.commit()
    response = db_client.get("/api/v1/approvals", headers=_headers(APPROVER, other_approver.id))
    assert response.status_code == 200
    assert response.json()["isEmpty"] is True


def test_list_scopes_contract_owner_to_own_contracts(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    response = db_client.get("/api/v1/approvals", headers=_headers(CONTRACT_OWNER, owner.id))
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_list_is_tenant_wide_for_tenant_admin(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    admin = _seed_user(db_session, tenant.id, TENANT_ADMIN)
    db_session.commit()
    response = db_client.get("/api/v1/approvals", headers=_headers(TENANT_ADMIN, admin.id))
    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


# ---- detail -----------------------------------------------------------------------------


def test_get_detail_not_found(db_client, db_session):
    tenant = _seed_tenant(db_session)
    admin = _seed_user(db_session, tenant.id, TENANT_ADMIN)
    db_session.commit()
    response = db_client.get(f"/api/v1/approvals/{uuid.uuid4()}", headers=_headers(TENANT_ADMIN, admin.id))
    assert response.status_code == 404


def test_get_detail_blocks_other_contract_owners(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    other_owner = _seed_user(db_session, tenant.id, CONTRACT_OWNER)
    db_session.commit()
    response = db_client.get(
        f"/api/v1/approvals/{approval.id}", headers=_headers(CONTRACT_OWNER, other_owner.id)
    )
    assert response.status_code == 403


def test_get_detail_fields_and_eligibility_for_current_approver(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, current_step_number=1, total_steps=3)
    response = db_client.get(f"/api/v1/approvals/{approval.id}", headers=_headers(APPROVER, approver.id))
    assert response.status_code == 200
    body = response.json()
    assert body["contractTitle"] == "Master Services Agreement"
    assert body["contractType"] == "MSA"
    assert body["counterpartyName"] == "Globex"
    assert body["keyTermsSummary"] == "Net 30 payment terms."
    assert body["deviationsFromStandard"] == "Liability cap raised to 2x fees."
    assert body["aiRiskScore"] == 55
    assert body["approvalMatrixStepLabel"] == "Step 1 of 3 – Step 1"
    assert body["approvalMatrixStepNumber"] == 1
    assert body["approvalMatrixTotalSteps"] == 3
    assert body["currentApproverId"] == str(approver.id)
    assert body["isCurrentUserApprover"] is True
    assert body["isStepActionable"] is True
    assert body["canApprove"] is True
    assert body["canReject"] is True
    assert body["canSendBack"] is True
    assert body["canDelegate"] is True


def test_get_detail_disables_actions_for_out_of_sequence_approver(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, current_step_number=1, total_steps=2)
    later_approver = _seed_user(db_session, tenant.id, APPROVER)
    db_session.commit()
    response = db_client.get(f"/api/v1/approvals/{approval.id}", headers=_headers(APPROVER, later_approver.id))
    assert response.status_code == 200
    body = response.json()
    assert body["isCurrentUserApprover"] is False
    assert body["canApprove"] is False
    assert body["canReject"] is False
    assert body["canSendBack"] is False
    assert body["canDelegate"] is False


# ---- actions ----------------------------------------------------------------------------


def test_action_rejects_blank_comments_for_reject(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Reject", "comments": "   "},
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 400
    assert "Comments are required when rejecting or sending back a contract." in response.json()["details"]


def test_action_rejects_blank_comments_for_send_back(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "SendBack"},
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 400


def test_action_approve_without_comments_is_accepted(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, current_step_number=1, total_steps=2)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "PendingApproval"
    assert body["approvalMatrixStepNumber"] == 2
    assert body["contractStatus"] == "PendingApproval"


def test_action_approve_final_step_transitions_to_pending_signature(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, current_step_number=2, total_steps=2)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Approved"
    assert body["contractStatus"] == "PendingSignature"
    db_session.expire_all()
    assert db_session.get(Contract, contract.id).status == "Pending Signature"
    log = db_session.query(ActivityLogEntry).filter(ActivityLogEntry.contract_id == contract.id).all()
    assert [e.details for e in log] == [
        "Status changed from Pending Approval to Pending Signature: all approval steps approved"
    ]


def test_action_reject_terminates_workflow(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Reject", "comments": "Non-standard liability terms."},
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "Rejected"
    assert body["contractStatus"] == "Rejected"

    second = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, approver.id),
    )
    assert second.status_code == 409


def test_action_send_back_closes_approval_and_returns_contract_to_negotiation(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, current_step_number=2, total_steps=2)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "SendBack", "comments": "Please clarify indemnification."},
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 200
    body = response.json()
    # The request is closed, not reset: it stays in history and the next Mark as Agreed
    # opens a new one from Step 1.
    assert body["status"] == "SentBack"
    assert body["contractStatus"] == "InNegotiation"

    again = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, approver.id),
    )
    assert again.status_code == 409


def test_action_intermediate_approve_keeps_contract_pending_approval(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, current_step_number=1, total_steps=2)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 200
    assert response.json()["contractStatus"] == "PendingApproval"
    db_session.expire_all()
    assert db_session.get(Contract, contract.id).status == "Pending Approval"


def test_action_blocks_out_of_sequence_approver(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, current_step_number=1, total_steps=2)
    later_approver = _seed_user(db_session, tenant.id, APPROVER)
    db_session.commit()
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, later_approver.id),
    )
    assert response.status_code == 403
    assert "not yet available" in response.json()["error"]


def test_action_blocks_contract_owner_self_approval(db_client, db_session):
    tenant = _seed_tenant(db_session)
    owner = _seed_user(db_session, tenant.id, APPROVER, name="Owner Acting As Approver")
    cp = _seed_counterparty(db_session, tenant.id)
    contract = _seed_contract(db_session, tenant.id, owner.id, cp.id)
    approval = _seed_approval(db_session, contract, owner.id, current_step_number=1, total_steps=1)
    db_session.commit()
    _seed_step_instance(db_session, approval, 1, owner.id)
    db_session.commit()

    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, owner.id),
    )
    assert response.status_code == 403


def test_action_blocks_on_stale_status(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, status="Rejected")
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 409
    assert "refresh" in response.json()["error"]


# ---- delegation -------------------------------------------------------------------------


def test_delegate_rejects_ineligible_user(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    ineligible = _seed_user(db_session, tenant.id, LEGAL_REVIEWER)
    db_session.commit()
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/delegate",
        json={
            "delegateToUserId": str(ineligible.id),
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
        },
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 400
    assert "not an eligible Approver" in response.json()["error"]


def test_delegate_rejects_contract_owner_as_delegate(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/delegate",
        json={
            "delegateToUserId": str(owner.id),
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
        },
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 400


def test_delegate_assigns_eligible_approver_and_action_logged_against_delegate(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session, current_step_number=1, total_steps=2)
    delegate = _seed_user(db_session, tenant.id, APPROVER, name="Delegate Approver")
    db_session.commit()

    today = date.today()
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/delegate",
        json={
            "delegateToUserId": str(delegate.id),
            "startDate": (today - timedelta(days=1)).isoformat(),
            "endDate": (today + timedelta(days=5)).isoformat(),
        },
        headers=_headers(APPROVER, approver.id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["delegateToUserId"] == str(delegate.id)
    assert body["delegateToName"] == "Delegate Approver"

    approve_response = db_client.post(
        f"/api/v1/approvals/{approval.id}/actions",
        json={"actionType": "Approve"},
        headers=_headers(APPROVER, delegate.id),
    )
    assert approve_response.status_code == 200

    history = db_client.get(
        f"/api/v1/approvals/{approval.id}/history", headers=_headers(APPROVER, approver.id)
    )
    assert history.status_code == 200
    actions = [item["action"] for item in history.json()["items"]]
    assert "Delegate" in actions
    assert "Approve" in actions
    approve_entry = next(item for item in history.json()["items"] if item["action"] == "Approve")
    assert approve_entry["actorId"] == str(delegate.id)
    assert approve_entry["actingAsDelegateForUserId"] == str(approver.id)


def test_delegate_blocked_when_actor_not_current_approver(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    other = _seed_user(db_session, tenant.id, APPROVER)
    db_session.commit()
    response = db_client.post(
        f"/api/v1/approvals/{approval.id}/delegate",
        json={
            "delegateToUserId": str(approver.id),
            "startDate": "2026-01-01",
            "endDate": "2026-01-31",
        },
        headers=_headers(APPROVER, other.id),
    )
    assert response.status_code == 403


# ---- history ------------------------------------------------------------------------------


def test_history_requires_role_header(db_client):
    assert db_client.get(f"/api/v1/approvals/{uuid.uuid4()}/history").status_code == 401


def test_history_empty_before_any_action(db_client, db_session):
    tenant, owner, approver, contract, approval = _setup_basic(db_session)
    admin = _seed_user(db_session, tenant.id, TENANT_ADMIN)
    db_session.commit()
    response = db_client.get(
        f"/api/v1/approvals/{approval.id}/history", headers=_headers(TENANT_ADMIN, admin.id)
    )
    assert response.status_code == 200
    assert response.json()["items"] == []
    assert response.json()["totalCount"] == 0
