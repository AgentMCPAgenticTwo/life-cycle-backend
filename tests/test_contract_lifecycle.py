"""Exercises every endpoint this task owns under `/api/v1/contracts/{contractId}/...` (document,
versions, activity-log, folder-tags, obligations, renewal, renew, amend, terminate) plus
`/api/v1/folder-tags` -- see TASK.md's stories UC8-*/UC9-* (T-CONTRACTS-API).

`GET /api/v1/contracts` and `GET /api/v1/contracts/{contractId}` are intentionally not covered
here -- see this task's `blockers` for why.
"""
import uuid
from datetime import date, timedelta

from app.models.contract import Contract
from app.models.contract_lifecycle import (
    ActivityLogEntry,
    ContractAssignment,
    ContractDocument,
    ContractVersion,
    FolderTag,
    Obligation,
)
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
APPROVER = "APPROVER"


def _headers(role: str, user_id) -> dict:
    return auth_headers(role, user_id)


def _seed_tenant(db_session) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    seed_id = uuid.uuid4()
    db_session.add(
        Tenant(id=tenant_id, name="Acme Co", high_risk_threshold=70, created_by=seed_id, updated_by=seed_id)
    )
    db_session.commit()
    return tenant_id


def _seed_user(db_session, tenant_id: uuid.UUID, role: str, *, name: str | None = None) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(
        User(
            id=user_id,
            tenant_id=tenant_id,
            name=name or f"{role.title()} User",
            email=f"{user_id}@acme.test",
            role=role,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()
    return user_id


def _seed_contract(db_session, tenant_id: uuid.UUID, owner_id: uuid.UUID, **overrides) -> uuid.UUID:
    counterparty_id = uuid.uuid4()
    db_session.add(
        Counterparty(
            id=counterparty_id,
            tenant_id=tenant_id,
            name="Globex",
            email="contact@globex.test",
            company="Globex Corp",
            created_by=owner_id,
            updated_by=owner_id,
        )
    )
    contract_id = uuid.uuid4()
    defaults = dict(
        id=contract_id,
        tenant_id=tenant_id,
        contract_name="Master Services Agreement",
        contract_type="MSA",
        industry="Service",
        counterparty_id=counterparty_id,
        counterparty="Globex Corp",
        contract_owner_id=owner_id,
        owner_id=owner_id,
        contract_value="100000.00",
        value="100000.00",
        currency="USD",
        start_date=date(2025, 1, 1),
        end_date=date(2027, 1, 1),
        renewal_type="Manual",
        notice_period_text="30 days",
        assigned_date=date(2025, 1, 1),
        due_date=date(2027, 1, 1),
        status="Executed",
        renewal_action_in_progress=False,
        created_by=owner_id,
        updated_by=owner_id,
    )
    defaults.update(overrides)
    db_session.add(Contract(**defaults))
    db_session.commit()
    return contract_id


def _assign(db_session, contract_id: uuid.UUID, user_id: uuid.UUID, role: str) -> None:
    db_session.add(
        ContractAssignment(
            id=uuid.uuid4(), contract_id=contract_id, user_id=user_id, role=role,
            created_by=user_id, updated_by=user_id,
        )
    )
    db_session.commit()


# ------------------------------------------------------------------------------- Document ---


def test_get_document_requires_auth(db_client):
    resp = db_client.get(f"/api/v1/contracts/{uuid.uuid4()}/document")
    assert resp.status_code == 401


def test_get_document_wrong_role_is_403(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    other_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/document", headers=_headers(CONTRACT_OWNER, other_id)
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "You do not have permission to view this contract."


def test_get_document_missing_contract_is_404(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.get(
        f"/api/v1/contracts/{uuid.uuid4()}/document", headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 404


def test_get_document_happy_path(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    db_session.add(
        ContractDocument(
            id=uuid.uuid4(), contract_id=contract_id, file_name="msa.pdf", file_type="pdf",
            file_size_bytes=1024, storage_path="/files/msa.pdf", is_corrupted_or_missing=False,
            created_by=owner_id, updated_by=owner_id,
        )
    )
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/document", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contractId"] == str(contract_id)
    assert body["fileName"] == "msa.pdf"
    assert body["downloadEnabled"] is True
    assert body["isOversized"] is False


def test_download_corrupted_document_returns_error_message(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    db_session.add(
        ContractDocument(
            id=uuid.uuid4(), contract_id=contract_id, file_name="msa.pdf", file_type="pdf",
            file_size_bytes=1024, storage_path=None, is_corrupted_or_missing=True,
            created_by=owner_id, updated_by=owner_id,
        )
    )
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/document/download", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is False
    assert body["errorMessage"] == "This document could not be retrieved. Please contact your administrator."


def test_download_oversized_document_is_disabled(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    db_session.add(
        ContractDocument(
            id=uuid.uuid4(), contract_id=contract_id, file_name="big.pdf", file_type="pdf",
            file_size_bytes=50 * 1024 * 1024, storage_path="/files/big.pdf", is_corrupted_or_missing=False,
            created_by=owner_id, updated_by=owner_id,
        )
    )
    db_session.commit()
    doc_resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/document", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert doc_resp.json()["unavailableComment"] == "File unavailable"
    dl_resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/document/download", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert dl_resp.json() == {"success": False, "fileUrl": None, "errorMessage": "File unavailable"}


# ------------------------------------------------------------------------------- Versions ---


def test_list_versions(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    db_session.add(
        ContractVersion(
            id=uuid.uuid4(), contract_id=contract_id, version_number=1, change_summary="Initial",
            created_by=owner_id, updated_by=owner_id,
        )
    )
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/versions", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalCount"] == 1
    assert body["items"][0]["versionNumber"] == 1
    assert body["items"][0]["createdBy"] == "Contract_Owner User"


# ---------------------------------------------------------------------------- Activity Log ---


def test_activity_log_is_immutable_and_populated_by_tag_action(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    tag_id = uuid.uuid4()
    db_session.add(
        FolderTag(id=tag_id, tenant_id=tenant_id, name="High Priority", kind="TAG",
                   created_by=owner_id, updated_by=owner_id)
    )
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/folder-tags",
        json={"folderTagIds": [str(tag_id)]},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 200
    assert resp.json()["folderTags"][0]["name"] == "High Priority"

    log_resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/activity-log", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert log_resp.status_code == 200
    body = log_resp.json()
    assert body["totalCount"] == 1
    assert body["items"][0]["actionType"] == "TAG"


def test_assign_folder_tag_requires_ownership(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    other_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    tag_id = uuid.uuid4()
    db_session.add(
        FolderTag(id=tag_id, tenant_id=tenant_id, name="Legal", kind="FOLDER",
                   created_by=owner_id, updated_by=owner_id)
    )
    db_session.commit()
    resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/folder-tags",
        json={"folderTagIds": [str(tag_id)]},
        headers=_headers(CONTRACT_OWNER, other_id),
    )
    assert resp.status_code == 403


def test_list_folder_tag_options(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    db_session.add(
        FolderTag(id=uuid.uuid4(), tenant_id=tenant_id, name="Vendor", kind="FOLDER",
                   created_by=admin_id, updated_by=admin_id)
    )
    db_session.commit()
    resp = db_client.get("/api/v1/folder-tags", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 200
    assert any(item["name"] == "Vendor" for item in resp.json())


# ----------------------------------------------------------------------------- Obligations ---


def test_obligations_blocked_for_non_executed_contract(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id, status="Draft")
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/obligations", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "Obligations are available only after a contract is fully executed"


def test_create_obligation_validates_due_date_and_type(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    past = (date.today() - timedelta(days=1)).isoformat()
    resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/obligations",
        json={
            "obligationDescription": "Deliver report",
            "obligationType": "Reporting",
            "owner": str(owner_id),
            "dueDate": past,
            "status": "Pending",
        },
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Due date cannot be in the past"


def test_create_obligation_happy_path_and_accept(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    future = (date.today() + timedelta(days=10)).isoformat()
    resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/obligations",
        json={
            "obligationDescription": "Deliver report",
            "obligationType": "Reporting",
            "owner": str(owner_id),
            "dueDate": future,
            "status": "Pending",
        },
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["source"] == "Manually Added"
    assert body["confirmationLabel"] == "Confirmed"
    obligation_id = body["obligationId"]

    accept_resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/obligations/{obligation_id}/accept",
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert accept_resp.status_code == 200
    assert accept_resp.json()["confirmationLabel"] == "Confirmed"


def test_obligation_status_transition_rules(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    obligation_id = uuid.uuid4()
    db_session.add(
        Obligation(
            id=obligation_id, contract_id=contract_id, obligation_description="Pay invoice",
            obligation_type="Payment Milestone", owner_id=owner_id,
            due_date=date.today() + timedelta(days=5), status="Pending", source="AI Extracted",
            confirmation_label="AI Suggested", created_by=owner_id, updated_by=owner_id,
        )
    )
    db_session.commit()

    bad_resp = db_client.patch(
        f"/api/v1/contracts/{contract_id}/obligations/{obligation_id}",
        json={"status": "Completed"},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert bad_resp.status_code == 409

    ok_resp = db_client.patch(
        f"/api/v1/contracts/{contract_id}/obligations/{obligation_id}",
        json={"status": "In Progress"},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert ok_resp.status_code == 200
    assert ok_resp.json()["status"] == "In Progress"
    assert ok_resp.json()["confirmationLabel"] == "Confirmed"

    missing_evidence_resp = db_client.patch(
        f"/api/v1/contracts/{contract_id}/obligations/{obligation_id}",
        json={"status": "Completed"},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert missing_evidence_resp.status_code == 400

    complete_resp = db_client.patch(
        f"/api/v1/contracts/{contract_id}/obligations/{obligation_id}",
        json={"status": "Completed", "evidenceReference": "invoice-123.pdf"},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert complete_resp.status_code == 200
    assert complete_resp.json()["status"] == "Completed"


def test_overdue_obligation_auto_transitions_on_read(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    db_session.add(
        Obligation(
            id=uuid.uuid4(), contract_id=contract_id, obligation_description="Late task",
            obligation_type="Deliverable", owner_id=owner_id,
            due_date=date.today() - timedelta(days=1), status="Pending", source="Manually Added",
            confirmation_label="Confirmed", created_by=owner_id, updated_by=owner_id,
        )
    )
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/obligations", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["status"] == "Overdue"


def test_legal_reviewer_sees_obligations_read_only(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    _assign(db_session, contract_id, reviewer_id, LEGAL_REVIEWER)
    db_session.add(
        Obligation(
            id=uuid.uuid4(), contract_id=contract_id, obligation_description="Task",
            obligation_type="SLA", owner_id=owner_id, due_date=date.today() + timedelta(days=5),
            status="Pending", source="AI Extracted", confirmation_label="AI Suggested",
            created_by=owner_id, updated_by=owner_id,
        )
    )
    db_session.commit()
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/obligations", headers=_headers(LEGAL_REVIEWER, reviewer_id)
    )
    assert resp.status_code == 200
    assert resp.json()["items"][0]["readOnly"] is True


def test_approver_blocked_from_obligations_and_renewal(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    approver_id = _seed_user(db_session, tenant_id, APPROVER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    _assign(db_session, contract_id, approver_id, APPROVER)
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/obligations", headers=_headers(APPROVER, approver_id)
    )
    assert resp.status_code == 403
    resp2 = db_client.get(
        f"/api/v1/contracts/{contract_id}/renewal", headers=_headers(APPROVER, approver_id)
    )
    assert resp2.status_code == 403


# --------------------------------------------------------------------------------- Renewal ---


def test_renewal_panel_shows_alert_at_90_days(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    end_date = date.today() + timedelta(days=90)
    contract_id = _seed_contract(
        db_session, tenant_id, owner_id, end_date=end_date, notice_period_text="15 days"
    )
    resp = db_client.get(
        f"/api/v1/contracts/{contract_id}/renewal", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["renewalAlertBanner"] is not None
    assert body["alertThresholdDays"] == 90
    assert body["renewEnabled"] is True
    assert body["amendEnabled"] is True
    assert body["terminateEnabled"] is True


def test_renew_creates_linked_contract_and_transitions_status(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/renew", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["originalContractStatus"] == "Renewed"
    assert body["linkedContractId"] == body["linkedContractReference"]

    # UC9-BR-008: a second Renew/Amend/Terminate attempt is blocked once the original is no
    # longer Executed/Active.
    second_resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/renew", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert second_resp.status_code == 409


def test_amend_creates_linked_contract(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/amend", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 200
    assert resp.json()["originalContractStatus"] == "Amended"


def test_terminate_requires_reason_and_future_date(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)

    missing_reason = db_client.post(
        f"/api/v1/contracts/{contract_id}/terminate",
        json={"terminationReason": "", "effectiveTerminationDate": date.today().isoformat()},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert missing_reason.status_code == 400
    assert missing_reason.json()["error"] == "Termination reason is required"

    past_date = db_client.post(
        f"/api/v1/contracts/{contract_id}/terminate",
        json={
            "terminationReason": "Breach of contract",
            "effectiveTerminationDate": (date.today() - timedelta(days=1)).isoformat(),
        },
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert past_date.status_code == 400

    ok = db_client.post(
        f"/api/v1/contracts/{contract_id}/terminate",
        json={
            "terminationReason": "Breach of contract",
            "effectiveTerminationDate": (date.today() + timedelta(days=1)).isoformat(),
        },
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["originalContractStatus"] == "Terminated"
    assert body["terminationReason"] == "Breach of contract"


def test_renew_disabled_for_non_executed_contract(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, owner_id, status="Draft")
    resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/renew", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 409


def test_tenant_admin_can_act_on_contracts_it_does_not_own(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    contract_id = _seed_contract(db_session, tenant_id, owner_id)
    resp = db_client.post(
        f"/api/v1/contracts/{contract_id}/amend", headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 200
