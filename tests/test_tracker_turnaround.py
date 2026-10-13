"""Exercises `GET /api/v1/tracker/turnaround` and
`PUT /api/v1/tracker/turnaround/{contractId}/estimated-override` (T-TRACKER-TURNAROUND-API):
the role matrix, Period/Date-Range validation (UC10-FV-001), the three empty-state tiers
(UC10-AF-001/003/005), the BR-4 'Not Set'/exclusion rule, the BR-3 variance color coding,
role-scoped visibility (UC10-BR-005/009/010/011), and the BR-7 override audit log.
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.tracker import ContractLifecycleStageHistory, ContractOwner, ContractTurnaroundMetrics, TurnaroundOverrideLog
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


def _seed_metrics(
    db_session,
    tenant_id: uuid.UUID,
    contract_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    estimated: float | None,
    source: str | None,
    actual: float | None,
    excluded: bool,
) -> ContractTurnaroundMetrics:
    row = ContractTurnaroundMetrics(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contract_id=contract_id,
        estimated_turnaround_days=estimated,
        estimated_turnaround_source=source,
        actual_turnaround_days=actual,
        excluded_from_averages=excluded,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(row)
    db_session.commit()
    return row


def test_requires_role_header(client):
    response = client.get("/api/v1/tracker/turnaround?period=Monthly")
    assert response.status_code == 401


def test_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, EXTERNAL_PARTY)
    response = db_client.get(
        "/api/v1/tracker/turnaround", params={"period": "Monthly"}, headers=_headers(EXTERNAL_PARTY, user_id)
    )
    assert response.status_code == 403


def test_missing_period_without_date_range_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/tracker/turnaround", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 400
    assert "Period selection is required." in response.json()["details"]


def test_invalid_period_enum_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get(
        "/api/v1/tracker/turnaround", params={"period": "Yearly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_date_range_from_not_earlier_than_to_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get(
        "/api/v1/tracker/turnaround",
        params={"dateRangeFrom": "2026-01-10", "dateRangeTo": "2026-01-01"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400
    assert "Date Range From must be earlier than Date Range To." in response.json()["details"]


def test_empty_tenant_shows_no_contract_data_message(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get(
        "/api/v1/tracker/turnaround", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
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
        "/api/v1/tracker/turnaround",
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
        "/api/v1/tracker/turnaround",
        params={"period": "Monthly", "contractTypeFilter": "NDA"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["isEmpty"] is True
    assert body["emptyStateMessage"] == "No records match the selected filters."


def test_contract_with_no_metrics_row_shows_not_set_and_excluded(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, name="NDA with Initech", status="Draft")
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=1)

    response = db_client.get(
        "/api/v1/tracker/turnaround", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 1
    row = body["rows"][0]
    assert row["contractId"] == str(contract.id)
    assert row["contractName"] == "NDA with Initech"
    assert row["contractType"] == "MSA"
    assert row["estimatedTurnaround"] is None
    assert row["estimatedTurnaroundNotSet"] is True
    assert row["estimatedTurnaroundSource"] == "NOT_SET"
    assert row["variance"] is None
    assert row["varianceColor"] is None
    assert row["excludedFromAverages"] is True


def test_positive_variance_is_red_and_delayed(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, status="Draft")
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=1)
    _seed_metrics(
        db_session, tenant_id, contract.id, user_id,
        estimated=10, source="UC2_TARGET_COMPLETION_DATE", actual=15, excluded=False,
    )

    response = db_client.get(
        "/api/v1/tracker/turnaround", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    row = response.json()["rows"][0]
    assert float(row["estimatedTurnaround"]) == 10
    assert float(row["actualTurnaround"]) == 15
    assert float(row["variance"]) == 5
    assert row["varianceColor"] == "RED"
    assert row["excludedFromAverages"] is False


def test_negative_or_zero_variance_is_green(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id, status="Draft")
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=1)
    _seed_metrics(
        db_session, tenant_id, contract.id, user_id,
        estimated=10, source="AI_SUGGESTED", actual=8, excluded=False,
    )

    response = db_client.get(
        "/api/v1/tracker/turnaround", params={"period": "Monthly"}, headers=_headers(TENANT_ADMIN, user_id)
    )
    row = response.json()["rows"][0]
    assert row["varianceColor"] == "GREEN"
    assert row["estimatedTurnaroundSource"] == "AI_SUGGESTED"


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
        "/api/v1/tracker/turnaround", params={"period": "Monthly"}, headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 1
    assert body["rows"][0]["contractName"] == "Owned by me"


def test_pagination_fields_echo_request(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id)
    _seed_stage_history(db_session, tenant_id, contract.id, user_id, stage="Drafting", days_ago=1)

    response = db_client.get(
        "/api/v1/tracker/turnaround",
        params={"period": "Monthly", "page": 1, "pageSize": 5},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    body = response.json()
    assert body["page"] == 1
    assert body["pageSize"] == 5


# --- PUT /api/v1/tracker/turnaround/{contractId}/estimated-override ---------------------


def test_override_requires_role_header(client):
    response = client.put(
        f"/api/v1/tracker/turnaround/{uuid.uuid4()}/estimated-override",
        json={"newEstimatedTurnaround": 5, "overriddenBy": str(uuid.uuid4()), "overrideTimestamp": "2026-01-01T00:00:00Z"},
    )
    assert response.status_code == 401


def test_override_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, EXTERNAL_PARTY)
    response = db_client.put(
        f"/api/v1/tracker/turnaround/{uuid.uuid4()}/estimated-override",
        json={"newEstimatedTurnaround": 5, "overriddenBy": str(user_id), "overrideTimestamp": "2026-01-01T00:00:00Z"},
        headers=_headers(EXTERNAL_PARTY, user_id),
    )
    assert response.status_code == 403


def test_override_missing_contract_is_404(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.put(
        f"/api/v1/tracker/turnaround/{uuid.uuid4()}/estimated-override",
        json={"newEstimatedTurnaround": 5, "overriddenBy": str(user_id), "overrideTimestamp": "2026-01-01T00:00:00Z"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 404


def test_override_malformed_contract_id_is_400(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.put(
        "/api/v1/tracker/turnaround/not-a-uuid/estimated-override",
        json={"newEstimatedTurnaround": 5, "overriddenBy": str(user_id), "overrideTimestamp": "2026-01-01T00:00:00Z"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400


def test_contract_owner_cannot_override_contract_they_do_not_own(db_client, db_session):
    tenant_id, admin_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _, owner_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER, tenant_id)
    contract = _seed_contract(db_session, tenant_id, admin_id)

    response = db_client.put(
        f"/api/v1/tracker/turnaround/{contract.id}/estimated-override",
        json={"newEstimatedTurnaround": 5, "overriddenBy": str(owner_id), "overrideTimestamp": "2026-01-01T00:00:00Z"},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert response.status_code == 403


def test_override_creates_metrics_row_and_audit_log_when_none_existed(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id)

    response = db_client.put(
        f"/api/v1/tracker/turnaround/{contract.id}/estimated-override",
        json={
            "newEstimatedTurnaround": 12,
            "overrideReason": "Renegotiated timeline",
            "overriddenBy": str(user_id),
            "overrideTimestamp": "2026-01-01T00:00:00Z",
        },
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert float(body["estimatedTurnaround"]) == 12
    assert body["estimatedTurnaroundNotSet"] is False
    assert body["excludedFromAverages"] is False

    log = db_session.query(TurnaroundOverrideLog).filter(TurnaroundOverrideLog.contract_id == contract.id).one()
    assert float(log.new_value) == 12
    assert log.override_user_id == user_id
    assert log.decision == "OVERRIDDEN"


def test_override_existing_ai_suggested_value_logs_original(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id)
    _seed_metrics(
        db_session, tenant_id, contract.id, user_id,
        estimated=10, source="AI_SUGGESTED", actual=None, excluded=True,
    )

    response = db_client.put(
        f"/api/v1/tracker/turnaround/{contract.id}/estimated-override",
        json={
            "newEstimatedTurnaround": 20,
            "overriddenBy": str(user_id),
            "overrideTimestamp": "2026-01-01T00:00:00Z",
        },
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert float(body["estimatedTurnaround"]) == 20
    assert body["excludedFromAverages"] is False

    log = db_session.query(TurnaroundOverrideLog).filter(TurnaroundOverrideLog.contract_id == contract.id).one()
    assert float(log.original_ai_value) == 10
    assert float(log.new_value) == 20
