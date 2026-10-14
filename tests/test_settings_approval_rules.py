"""Exercises every endpoint this task owns (`/api/v1/settings/approval-rules`): the role
matrix, the happy path for GET/POST, and the validation rules named in TASK.md
(T-SETTINGS-APPROVAL-RULES-API) for UC11-AF-003 (required fields), UC11-FV-002 (numeric,
non-negative Value Threshold) and UC11-BR-004 (duplicate Contract Type + Value Threshold).
"""
import uuid

from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers

TENANT_ADMIN = "TENANT_ADMIN"
APPROVER = "APPROVER"


def _seed_tenant_and_user(db_session, role: str, tenant_id: uuid.UUID | None = None) -> tuple[uuid.UUID, uuid.UUID]:
    is_new_tenant = tenant_id is None
    tenant_id = tenant_id or uuid.uuid4()
    user_id = uuid.uuid4()
    if is_new_tenant:
        db_session.add(
            Tenant(
                id=tenant_id,
                name="Acme Co",
                high_risk_threshold=70,
                created_by=user_id,
                updated_by=user_id,
            )
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
    return auth_headers(role, user_id)


def _valid_payload(**overrides) -> dict:
    payload = {"contractType": "Product", "valueThreshold": 50000, "approverRole": "Approver"}
    payload.update(overrides)
    return payload


def test_get_requires_role_header(db_client):
    response = db_client.get("/api/v1/settings/approval-rules")
    assert response.status_code == 401


def test_get_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.get("/api/v1/settings/approval-rules", headers=_headers(APPROVER, user_id))
    assert response.status_code == 403


def test_get_empty_list(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/settings/approval-rules", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert body["totalCount"] == 0


def test_post_then_get_round_trips(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/settings/approval-rules", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 201
    body = response.json()
    assert body["contractType"] == "Product"
    assert float(body["valueThreshold"]) == 50000
    assert body["approverRole"] == "Approver"
    rule_id = body["id"]
    uuid.UUID(rule_id)  # server-generated id, not client-supplied
    assert response.headers["location"] == f"/api/v1/settings/approval-rules/{rule_id}"

    list_response = db_client.get("/api/v1/settings/approval-rules", headers=_headers(TENANT_ADMIN, user_id))
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["totalCount"] == 1
    assert list_body["items"][0]["id"] == rule_id


def test_post_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.post(
        "/api/v1/settings/approval-rules", json=_valid_payload(), headers=_headers(APPROVER, user_id)
    )
    assert response.status_code == 403


def test_post_rejects_missing_contract_type(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(contractType=None)
    response = db_client.post(
        "/api/v1/settings/approval-rules", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400
    assert "Please complete all required fields" in response.json()["details"]


def test_post_rejects_missing_approver_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(approverRole=None)
    response = db_client.post(
        "/api/v1/settings/approval-rules", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400
    assert "Please complete all required fields" in response.json()["details"]


def test_post_rejects_missing_value_threshold(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(valueThreshold=None)
    response = db_client.post(
        "/api/v1/settings/approval-rules", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400
    assert "Please complete all required fields" in response.json()["details"]


def test_post_rejects_negative_value_threshold(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(valueThreshold=-100)
    response = db_client.post(
        "/api/v1/settings/approval-rules", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_post_rejects_non_numeric_value_threshold(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(valueThreshold="not-a-number")
    response = db_client.post(
        "/api/v1/settings/approval-rules", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_post_rejects_invalid_contract_type_enum(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(contractType="Other")
    response = db_client.post(
        "/api/v1/settings/approval-rules", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_post_rejects_duplicate_contract_type_and_threshold(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.post(
        "/api/v1/settings/approval-rules", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    )
    response = db_client.post(
        "/api/v1/settings/approval-rules",
        json=_valid_payload(approverRole="Legal Reviewer"),
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 409


def test_post_allows_same_threshold_for_different_contract_type(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.post(
        "/api/v1/settings/approval-rules", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    )
    response = db_client.post(
        "/api/v1/settings/approval-rules",
        json=_valid_payload(contractType="Service"),
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 201


def test_get_scopes_rules_by_tenant(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    other_tenant_id, other_user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.post(
        "/api/v1/settings/approval-rules", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    )
    response = db_client.get(
        "/api/v1/settings/approval-rules", headers=_headers(TENANT_ADMIN, other_user_id)
    )
    assert response.status_code == 200
    assert response.json()["totalCount"] == 0
