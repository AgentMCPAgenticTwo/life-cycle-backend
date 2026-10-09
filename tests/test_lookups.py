"""Exercises every endpoint this task owns (`/api/v1/dashboard/*`, `/api/v1/users`) against a
real in-memory database: the role matrix, tenant isolation, the empty/no-match dashboard
messages (UC1-AF-001/002/003/004), the overlapping 30/60/90-day expiring windows (UC1-BR-002),
the role-scoped My Tasks and High Risk panels (UC1-BR-003/004/010/011/013), and the Contract
Owner dropdown (UC2-BR-003/012).
"""
import uuid
from datetime import date, timedelta

from app.models.contract import Contract, ContractTask
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.user import User

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
APPROVER = "APPROVER"
SIGNER = "SIGNER"


def _headers(role: str, user_id: uuid.UUID) -> dict:
    return {"X-User-Role": role, "X-User-Id": str(user_id)}


def _seed_tenant(db_session, *, high_risk_threshold: int = 70) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    seed_id = uuid.uuid4()
    db_session.add(
        Tenant(
            id=tenant_id,
            name="Acme Co",
            high_risk_threshold=high_risk_threshold,
            created_by=seed_id,
            updated_by=seed_id,
        )
    )
    db_session.commit()
    return tenant_id


def _seed_user(db_session, tenant_id: uuid.UUID, role: str, *, name: str | None = None) -> uuid.UUID:
    user_id = uuid.uuid4()
    label = name or f"{role.title()} User"
    db_session.add(
        User(
            id=user_id,
            tenant_id=tenant_id,
            name=label,
            email=f"{user_id}@acme.test",
            role=role,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()
    return user_id


def _seed_counterparty(db_session, tenant_id: uuid.UUID, admin_id: uuid.UUID, *, name: str = "Globex Contact") -> uuid.UUID:
    counterparty_id = uuid.uuid4()
    db_session.add(
        Counterparty(
            id=counterparty_id,
            tenant_id=tenant_id,
            name=name,
            email="contact@globex.test",
            company="Globex Corp",
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()
    return counterparty_id


def _seed_contract(
    db_session,
    tenant_id: uuid.UUID,
    admin_id: uuid.UUID,
    counterparty_id: uuid.UUID,
    owner_id: uuid.UUID,
    *,
    status: str = "Draft",
    end_date: date | None = None,
    risk_score: int | None = None,
    contract_type: str = "NDA",
    department: str | None = None,
) -> uuid.UUID:
    contract_id = uuid.uuid4()
    today = date(2026, 10, 8)
    db_session.add(
        Contract(
            id=contract_id,
            tenant_id=tenant_id,
            contract_name=f"Contract {contract_id}",
            contract_type=contract_type,
            industry="Product",
            department=department,
            counterparty_id=counterparty_id,
            contract_owner_id=owner_id,
            contract_value=10000,
            currency="USD",
            start_date=today,
            end_date=end_date or (today + timedelta(days=365)),
            renewal_type="None",
            assigned_date=today,
            due_date=today + timedelta(days=30),
            status=status,
            risk_score=risk_score,
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()
    return contract_id


def _seed_task(
    db_session, contract_id: uuid.UUID, assignee_id: uuid.UUID, admin_id: uuid.UUID, *, role: str, is_current: bool = True
) -> None:
    db_session.add(
        ContractTask(
            id=uuid.uuid4(),
            contract_id=contract_id,
            assignee_user_id=assignee_id,
            assignment_role=role,
            due_date=date(2026, 11, 1),
            is_current=is_current,
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()


# ---- auth matrix -----------------------------------------------------------------------


def test_summary_missing_role_header_is_401(db_client):
    resp = db_client.get("/api/v1/dashboard/summary")
    assert resp.status_code == 401
    assert "error" in resp.json() and "details" in resp.json()


def test_high_risk_blocks_signer(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    signer_id = _seed_user(db_session, tenant_id, SIGNER)
    resp = db_client.get(
        "/api/v1/dashboard/high-risk-contracts", headers=_headers(SIGNER, signer_id)
    )
    assert resp.status_code == 403


def test_users_blocks_legal_reviewer(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    resp = db_client.get("/api/v1/users", headers=_headers(LEGAL_REVIEWER, reviewer_id))
    assert resp.status_code == 403


# ---- dashboard summary: empty state / counts / expiring windows (UC1-AF-001, BR-001/002) ----


def test_summary_empty_tenant_shows_zero_counts_and_message(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.get("/api/v1/dashboard/summary", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalContractsCount"] == 0
    assert body["inDraftCount"] == 0
    assert body["expiring30DaysCount"] == 0
    assert body["noContractsMessage"] == "No contracts yet. Click New Contract to get started."
    assert body["noMatchMessage"] is None


def test_summary_counts_reflect_exact_statuses(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, status="Draft")
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, status="In Negotiation")
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, status="Executed")
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, status="Executed")

    resp = db_client.get("/api/v1/dashboard/summary", headers=_headers(TENANT_ADMIN, admin_id))
    body = resp.json()
    assert body["totalContractsCount"] == 4
    assert body["inDraftCount"] == 1
    assert body["inNegotiationCount"] == 1
    assert body["executedCount"] == 2
    assert body["pendingApprovalCount"] == 0


def test_summary_expiring_windows_overlap(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    today = date(2026, 10, 8)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, end_date=today + timedelta(days=20))
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, end_date=today + timedelta(days=45))
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, end_date=today + timedelta(days=85))

    resp = db_client.get("/api/v1/dashboard/summary", headers=_headers(TENANT_ADMIN, admin_id))
    body = resp.json()
    # 20-day contract counts in all three windows; 45-day in 60/90 only; 85-day in 90 only.
    assert body["expiring30DaysCount"] == 1
    assert body["expiring60DaysCount"] == 2
    assert body["expiring90DaysCount"] == 3


def test_summary_no_match_message_when_filters_match_nothing(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, contract_type="NDA")

    resp = db_client.get(
        "/api/v1/dashboard/summary",
        params={"contractType": "MSA"},
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    body = resp.json()
    assert body["totalContractsCount"] == 0
    assert body["noMatchMessage"] == "No contracts match the selected filters"
    assert body["noContractsMessage"] is None


def test_summary_scoped_to_tenant(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id)

    other_tenant_id = _seed_tenant(db_session)
    other_admin_id = _seed_user(db_session, other_tenant_id, TENANT_ADMIN)
    other_owner_id = _seed_user(db_session, other_tenant_id, CONTRACT_OWNER)
    other_cp_id = _seed_counterparty(db_session, other_tenant_id, other_admin_id)
    _seed_contract(db_session, other_tenant_id, other_admin_id, other_cp_id, other_owner_id)
    _seed_contract(db_session, other_tenant_id, other_admin_id, other_cp_id, other_owner_id)

    resp = db_client.get("/api/v1/dashboard/summary", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.json()["totalContractsCount"] == 1


# ---- My Tasks: empty state, assignment scoping, Contract Owner scoping (AF-002, BR-003/011) --


def test_my_tasks_empty_shows_message(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    resp = db_client.get("/api/v1/dashboard/my-tasks", headers=_headers(LEGAL_REVIEWER, reviewer_id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["emptyMessage"] == "You have no pending tasks"


def test_my_tasks_shows_only_current_assignee(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    other_reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    contract_id = _seed_contract(
        db_session, tenant_id, admin_id, cp_id, owner_id, status="In Negotiation"
    )
    _seed_task(db_session, contract_id, reviewer_id, admin_id, role="LEGAL_REVIEWER")

    resp = db_client.get("/api/v1/dashboard/my-tasks", headers=_headers(LEGAL_REVIEWER, reviewer_id))
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["contractId"] == str(contract_id)
    assert body["items"][0]["counterparty"] == "Globex Contact"

    resp_other = db_client.get(
        "/api/v1/dashboard/my-tasks", headers=_headers(LEGAL_REVIEWER, other_reviewer_id)
    )
    assert resp_other.json()["items"] == []


def test_my_tasks_ignores_non_current_task(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    approver_id = _seed_user(db_session, tenant_id, APPROVER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    contract_id = _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id)
    _seed_task(db_session, contract_id, approver_id, admin_id, role="APPROVER", is_current=False)

    resp = db_client.get("/api/v1/dashboard/my-tasks", headers=_headers(APPROVER, approver_id))
    assert resp.json()["items"] == []


def test_my_tasks_contract_owner_sees_owned_open_contracts(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    other_owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, status="Draft")
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, status="Executed")
    _seed_contract(db_session, tenant_id, admin_id, cp_id, other_owner_id, status="Draft")

    resp = db_client.get("/api/v1/dashboard/my-tasks", headers=_headers(CONTRACT_OWNER, owner_id))
    body = resp.json()
    # Only the owner's own non-Executed contract -- not the Executed one, not the other owner's.
    assert len(body["items"]) == 1


# ---- High Risk: threshold, role scoping, ordering, empty state (BR-004/010/011, FV-003) -----


def test_high_risk_default_threshold_and_ordering(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, risk_score=65)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, risk_score=75)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, risk_score=90)

    resp = db_client.get(
        "/api/v1/dashboard/high-risk-contracts", headers=_headers(TENANT_ADMIN, admin_id)
    )
    body = resp.json()
    assert len(body["items"]) == 2
    assert [item["riskScore"] for item in body["items"]] == [90, 75]


def test_high_risk_contract_owner_scoped_to_own_contracts(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    other_owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, risk_score=95)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, other_owner_id, risk_score=99)

    resp = db_client.get(
        "/api/v1/dashboard/high-risk-contracts", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["riskScore"] == 95


def test_high_risk_empty_shows_message(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.get(
        "/api/v1/dashboard/high-risk-contracts", headers=_headers(TENANT_ADMIN, admin_id)
    )
    body = resp.json()
    assert body["items"] == []
    assert body["emptyMessage"] == "No high risk contracts found"


def test_high_risk_respects_custom_tenant_threshold(db_client, db_session):
    tenant_id = _seed_tenant(db_session, high_risk_threshold=90)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    cp_id = _seed_counterparty(db_session, tenant_id, admin_id)
    _seed_contract(db_session, tenant_id, admin_id, cp_id, owner_id, risk_score=80)

    resp = db_client.get(
        "/api/v1/dashboard/high-risk-contracts", headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.json()["items"] == []


# ---- filter options: populated even with no data, tenant scoped (UC1-AF-001, BR-006) --------


def test_filter_options_populated_for_empty_tenant(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.get("/api/v1/dashboard/filters", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 200
    body = resp.json()
    assert "NDA" in body["contractTypes"]
    assert body["departments"] == []
    assert body["counterparties"] == []
    assert body["owners"] == []


def test_filter_options_scoped_to_tenant(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER, name="Dana Owner")
    _seed_counterparty(db_session, tenant_id, admin_id, name="Initech")

    other_tenant_id = _seed_tenant(db_session)
    other_admin_id = _seed_user(db_session, other_tenant_id, TENANT_ADMIN)
    _seed_user(db_session, other_tenant_id, CONTRACT_OWNER, name="Other Owner")
    _seed_counterparty(db_session, other_tenant_id, other_admin_id, name="Other Corp")

    resp = db_client.get("/api/v1/dashboard/filters", headers=_headers(TENANT_ADMIN, admin_id))
    body = resp.json()
    assert [c["name"] for c in body["counterparties"]] == ["Initech"]
    assert [o["name"] for o in body["owners"]] == ["Dana Owner"]


# ---- /api/v1/users: Contract Owner dropdown (UC2-BR-003/012) ---------------------------------


def test_users_filters_by_role(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER, name="Dana Owner")
    _seed_user(db_session, tenant_id, LEGAL_REVIEWER)

    resp = db_client.get(
        "/api/v1/users", params={"role": "CONTRACT_OWNER"}, headers=_headers(TENANT_ADMIN, admin_id)
    )
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == str(owner_id)
    assert body["items"][0]["role"] == "CONTRACT_OWNER"


def test_users_scoped_to_tenant(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    _seed_user(db_session, tenant_id, CONTRACT_OWNER)

    other_tenant_id = _seed_tenant(db_session)
    other_admin_id = _seed_user(db_session, other_tenant_id, TENANT_ADMIN)
    _seed_user(db_session, other_tenant_id, CONTRACT_OWNER)

    resp = db_client.get(
        "/api/v1/users", params={"role": "CONTRACT_OWNER"}, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert len(resp.json()["items"]) == 1
