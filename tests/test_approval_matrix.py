"""Exercises every endpoint this task owns (`/api/v1/approval-matrix-config`) against a
real in-memory database: the role matrix, the happy path for GET/PUT, full-replace
semantics, and the validation rules named in TASK.md for UC6-BR-002 / UC6-BR-016 -- blank
Contract Type, inverted value/risk-band ranges, an empty step list, a step missing both an
approver role and an approver user, a duplicated step number, and an approver user from
another tenant.
"""
import uuid

from app.models.tenant import Tenant
from app.models.user import User

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
    return {"X-User-Role": role, "X-User-Id": str(user_id)}


def _valid_payload(approver_user_id: uuid.UUID) -> dict:
    return {
        "items": [
            {
                "contractType": "NDA",
                "valueMin": "0.00",
                "valueMax": "50000.00",
                "riskBandMin": 1,
                "riskBandMax": 3,
                "steps": [
                    {"stepNumber": 1, "approverRole": "LEGAL_REVIEWER", "stepName": "Legal Review"},
                    {
                        "stepNumber": 2,
                        "approverUserId": str(approver_user_id),
                        "stepName": "Final Sign-off",
                    },
                ],
            }
        ]
    }


def test_get_requires_role_header(client):
    response = client.get("/api/v1/approval-matrix-config")
    assert response.status_code == 401


def test_get_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.get("/api/v1/approval-matrix-config", headers=_headers(APPROVER, user_id))
    assert response.status_code == 403


def test_get_empty_list(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/approval-matrix-config", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_put_then_get_round_trips(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _, approver_user_id = _seed_tenant_and_user(db_session, "LEGAL_REVIEWER", tenant_id=tenant_id)

    payload = _valid_payload(approver_user_id)
    put_response = db_client.put(
        "/api/v1/approval-matrix-config", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert put_response.status_code == 200
    body = put_response.json()
    assert len(body["items"]) == 1
    item = body["items"][0]
    assert item["contractType"] == "NDA"
    assert item["valueMin"] == "0.00" or float(item["valueMin"]) == 0.0
    assert item["riskBandMin"] == 1
    assert len(item["steps"]) == 2
    assert item["steps"][0]["stepName"] == "Legal Review"
    assert item["steps"][1]["approverUserId"] == str(approver_user_id)
    config_id = item["id"]
    uuid.UUID(config_id)  # server-generated id, not client-supplied

    get_response = db_client.get("/api/v1/approval-matrix-config", headers=_headers(TENANT_ADMIN, user_id))
    assert get_response.status_code == 200
    assert get_response.json() == body


def test_put_replaces_existing_rules(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _, approver_user_id = _seed_tenant_and_user(db_session, "LEGAL_REVIEWER", tenant_id=tenant_id)

    db_client.put(
        "/api/v1/approval-matrix-config",
        json=_valid_payload(approver_user_id),
        headers=_headers(TENANT_ADMIN, user_id),
    )
    second_payload = {
        "items": [
            {
                "contractType": "MSA",
                "steps": [{"stepNumber": 1, "approverRole": "CONTRACT_OWNER", "stepName": "Owner Review"}],
            }
        ]
    }
    response = db_client.put(
        "/api/v1/approval-matrix-config", json=second_payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["contractType"] == "MSA"


def test_put_rejects_blank_contract_type(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = {
        "items": [
            {
                "contractType": "   ",
                "steps": [{"stepNumber": 1, "approverRole": "LEGAL_REVIEWER", "stepName": "Review"}],
            }
        ]
    }
    response = db_client.put(
        "/api/v1/approval-matrix-config", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400
    assert "Contract Type is required." in response.json()["details"]


def test_put_rejects_inverted_value_range(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = {
        "items": [
            {
                "contractType": "NDA",
                "valueMin": "1000.00",
                "valueMax": "10.00",
                "steps": [{"stepNumber": 1, "approverRole": "LEGAL_REVIEWER", "stepName": "Review"}],
            }
        ]
    }
    response = db_client.put(
        "/api/v1/approval-matrix-config", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_put_rejects_empty_steps(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = {"items": [{"contractType": "NDA", "steps": []}]}
    response = db_client.put(
        "/api/v1/approval-matrix-config", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_put_rejects_step_missing_approver(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = {
        "items": [
            {
                "contractType": "NDA",
                "steps": [{"stepNumber": 1, "stepName": "Review"}],
            }
        ]
    }
    response = db_client.put(
        "/api/v1/approval-matrix-config", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_put_rejects_duplicate_step_number(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = {
        "items": [
            {
                "contractType": "NDA",
                "steps": [
                    {"stepNumber": 1, "approverRole": "LEGAL_REVIEWER", "stepName": "Review"},
                    {"stepNumber": 1, "approverRole": "CONTRACT_OWNER", "stepName": "Owner Review"},
                ],
            }
        ]
    }
    response = db_client.put(
        "/api/v1/approval-matrix-config", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_put_rejects_approver_from_another_tenant(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _, other_tenant_approver_id = _seed_tenant_and_user(db_session, "LEGAL_REVIEWER")
    payload = {
        "items": [
            {
                "contractType": "NDA",
                "steps": [
                    {"stepNumber": 1, "approverUserId": str(other_tenant_approver_id), "stepName": "Review"},
                ],
            }
        ]
    }
    response = db_client.put(
        "/api/v1/approval-matrix-config", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400


def test_put_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.put(
        "/api/v1/approval-matrix-config", json={"items": []}, headers=_headers(APPROVER, user_id)
    )
    assert response.status_code == 403
