"""Exercises `GET /api/v1/tracker/bottleneck` (T-TRACKER-BOTTLENECK-API): the role matrix,
Period/Date-Range validation (UC10-FV-001), the three empty-state tiers (UC10-AF-001/003/005),
the stuck-flag threshold calculation (UC10-BR-002/GC-003) including a tenant override, and
role-scoped visibility (UC10-BR-005/009/010/011).
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.tracker import ContractLifecycleStageHistory, ContractOwner, TenantBottleneckThreshold
from app.models.user import User

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
APPROVER = "APPROVER"
EXTERNAL_PARTY = "EXTERNAL_PARTY"


def _seed_tenant_and_user(db_session, role: str, tenant_id: uuid.UUID | None = None) -> tuple[uuid.UUID, uuid.UUID]:
    is_new_tenant = tenant_id is None
    tenant_id = tenant_id or uuid.uuid4()
    user_id = uuid.uuid4()
    if is_new_tenant:
        db_session.add(
            Tenant(id=tenant_id, name="Acme Co", high_risk_threshold=70, created_by=user_id, updated_by=user_id)
        )
    db_session.add(
        User(
            id=user_id,
            tenant_id=tenant_id,
            name=f"{role.title()} User",
            email=f"{role.lower()}-{user_id}@acme.test",
            role=role,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()
    return tenant_id, user_id


def _headers(role: str, user_id: uuid.UUID) -> dict:
    return {"X-User-Role": role, "X-User-Id": str(user_id)}


def _seed_contract(
    db_session,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    name: str = "MSA with Globex",
    contract_type: str = "MSA",
    status: str = "Draft",
    owner_id: uuid.UUID | None = None,
) -> Contract:
    counterparty = Counterparty(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Globex",
        email=f"globex-{uuid.uuid4()}@example.test",
        company="Globex Corp",
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(counterparty)
    db_session.flush()

    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contract_name=name,
        contract_type=contract_type,
        industry="Technology",
        counterparty_id=counterparty.id,
        contract_owner_id=owner_id or actor_id,
        owner_id=owner_id or actor_id,
        contract_value=1000,
        currency="USD",
        renewal_type="Manual",
        assigned_date=datetime.now(timezone.utc).date(),
        due_date=datetime.now(timezone.utc).date(),
        status=status,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(contract)
    db_session.commit()
    return contract


def _seed_stage_history(
    db_session,
    tenant_id: uuid.UUID,
    contract_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    stage: str,
    days_ago: int,
) -> ContractLifecycleStageHistory:
    row = ContractLifecycleStageHistory(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contract_id=contract_id,
        stage=stage,
        stage_start_date=datetime.now(timezone.utc) - timedelta(days=days_ago),
        stage_end_date=None,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(row)
    db_session.commit()
    return row


def _seed_owner_role(db_session, tenant_id: uuid.UUID, contract_id: uuid.UUID, user_id: uuid.UUID, role: str, actor_id: uuid.UUID) -> None:
    db_session.add(
        ContractOwner(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            contract_id=contract_id,
            user_id=user_id,
            role=role,
            created_by=actor_id,
            updated_by=actor_id,
        )
    )
    db_session.commit()


def test_requires_role_header(client):
    response = client.get("/api/v1/tracker/bottleneck?period=Monthly")
    assert response.status_code == 401


def test_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, EXTERNAL_PARTY)
    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Monthly"}, headers=_headers(EXTERNAL_PARTY, user_id)
    )
    assert response.status_code == 403


def test_missing_period_without_date_range_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/tracker/bottleneck", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 400
    assert "Period selection is required." in response.json()["details"]


def test_invalid_period_enum_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Yearly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_date_range_from_not_earlier_than_to_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get(
        "/api/v1/tracker/bottleneck",
        params={"dateRangeFrom": "2026-01-10", "dateRangeTo": "2026-01-01"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400
    assert "Date Range From must be earlier than Date Range To." in response.json()["details"]


def test_empty_tenant_shows_no_contract_data_message(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["isEmpty"] is True
    assert body["emptyStateMessage"] == "No contract data available to display."
    assert body["rows"] == []
    assert body["totalCount"] == 0


def test_date_range_with_no_matching_contracts_shows_no_records_for_period(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, status="Draft")
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=1)

    far_past_from = (datetime.now(timezone.utc) - timedelta(days=400)).date().isoformat()
    far_past_to = (datetime.now(timezone.utc) - timedelta(days=390)).date().isoformat()
    response = db_client.get(
        "/api/v1/tracker/bottleneck",
        params={"dateRangeFrom": far_past_from, "dateRangeTo": far_past_to},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["isEmpty"] is True
    assert body["emptyStateMessage"] == "No records found for the selected period."


def test_conflicting_filters_show_no_records_match_message(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, contract_type="MSA", status="Draft")
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=1)

    response = db_client.get(
        "/api/v1/tracker/bottleneck",
        params={"period": "Monthly", "contractTypeFilter": "NDA"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["isEmpty"] is True
    assert body["emptyStateMessage"] == "No records match the selected filters."


def test_happy_path_returns_bottleneck_row_fields(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, name="NDA with Initech", status="Draft")
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=1)

    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["isEmpty"] is False
    assert body["totalCount"] == 1
    row = body["rows"][0]
    assert row["contractId"] == str(contract.id)
    assert row["contractName"] == "NDA with Initech"
    assert row["currentStage"] == "Drafting"
    assert row["daysInCurrentStage"] == 1
    assert row["stuckFlag"] == "No"


def test_default_threshold_flags_stuck_contract(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, status="Draft")
    # Default threshold for Drafting is 5 days -- 6 days in stage exceeds it.
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=6)

    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    row = response.json()["rows"][0]
    assert row["stuckFlag"] == "Yes"


def test_tenant_override_threshold_changes_stuck_flag(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, status="Draft")
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=6)
    db_session.add(
        TenantBottleneckThreshold(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            stage="Drafting",
            threshold_days=10,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()

    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    row = response.json()["rows"][0]
    assert row["stuckFlag"] == "No"


def test_approval_stage_uses_three_day_default_threshold(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, status="PendingApproval")
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Approval", days_ago=4)

    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    row = response.json()["rows"][0]
    assert row["currentStage"] == "Approval"
    assert row["stuckFlag"] == "Yes"


def test_contract_owner_sees_only_contracts_they_own(db_client, db_session):
    tenant_id, admin_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _, owner_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER, tenant_id)
    _, other_owner_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER, tenant_id)

    owned_contract = _seed_contract(db_session, tenant_id, admin_id, name="Owned by me")
    _seed_stage_history(db_session, tenant_id, owned_contract.id, admin_id, stage="Drafting", days_ago=1)
    _seed_owner_role(db_session, tenant_id, owned_contract.id, owner_id, "CONTRACT_OWNER", admin_id)

    other_contract = _seed_contract(db_session, tenant_id, admin_id, name="Owned by someone else")
    _seed_stage_history(db_session, tenant_id, other_contract.id, admin_id, stage="Drafting", days_ago=1)
    _seed_owner_role(db_session, tenant_id, other_contract.id, other_owner_id, "CONTRACT_OWNER", admin_id)

    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Monthly"}, headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 1
    assert body["rows"][0]["contractName"] == "Owned by me"


def test_contract_owner_with_no_owned_contracts_sees_empty_state(db_client, db_session):
    tenant_id, admin_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _, owner_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER, tenant_id)
    contract = _seed_contract(db_session, tenant_id, admin_id)
    _seed_stage_history(db_session, tenant_id, contract.id, admin_id, stage="Drafting", days_ago=1)

    response = db_client.get(
        "/api/v1/tracker/bottleneck", params={"period": "Monthly"}, headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["isEmpty"] is True
    assert body["emptyStateMessage"] == "No contract data available to display."


def test_pagination_fields_echo_request(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id)
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=1)

    response = db_client.get(
        "/api/v1/tracker/bottleneck",
        params={"period": "Monthly", "page": 1, "pageSize": 5},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    body = response.json()
    assert body["page"] == 1
    assert body["pageSize"] == 5
