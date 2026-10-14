"""Exercises `GET /api/v1/tracker/bottleneck-thresholds` (T-TRACKER-BOTTLENECK-THRESHOLDS-API):
the role matrix, the four-stage default thresholds (UC10-BR-002), and tenant overrides.
"""
import uuid

from app.models.tenant import Tenant
from app.models.tracker import TenantBottleneckThreshold
from app.models.user import User
from tests.conftest import auth_headers

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"


def _seed_tenant_and_user(db_session, role: str) -> tuple[uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
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
    return auth_headers(role, user_id)


def test_requires_role_header(db_client):
    response = db_client.get("/api/v1/tracker/bottleneck-thresholds")
    assert response.status_code == 401


def test_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER)
    response = db_client.get("/api/v1/tracker/bottleneck-thresholds", headers=_headers(CONTRACT_OWNER, user_id))
    assert response.status_code == 403


def test_defaults_returned_when_no_overrides_configured(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/tracker/bottleneck-thresholds", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    body = response.json()
    assert body == [
        {"stage": "Drafting", "thresholdDays": 5},
        {"stage": "Negotiation", "thresholdDays": 5},
        {"stage": "Approval", "thresholdDays": 3},
        {"stage": "Signature", "thresholdDays": 3},
    ]


def test_tenant_override_replaces_default_for_that_stage_only(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
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

    response = db_client.get("/api/v1/tracker/bottleneck-thresholds", headers=_headers(TENANT_ADMIN, user_id))
    body = response.json()
    by_stage = {row["stage"]: row["thresholdDays"] for row in body}
    assert by_stage["Drafting"] == 10
    assert by_stage["Negotiation"] == 5
    assert by_stage["Approval"] == 3
    assert by_stage["Signature"] == 3


def test_thresholds_are_tenant_scoped(db_client, db_session):
    tenant_a, user_a = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    tenant_b, user_b = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_session.add(
        TenantBottleneckThreshold(
            id=uuid.uuid4(),
            tenant_id=tenant_a,
            stage="Signature",
            threshold_days=7,
            created_by=user_a,
            updated_by=user_a,
        )
    )
    db_session.commit()

    response_b = db_client.get("/api/v1/tracker/bottleneck-thresholds", headers=_headers(TENANT_ADMIN, user_b))
    by_stage_b = {row["stage"]: row["thresholdDays"] for row in response_b.json()}
    assert by_stage_b["Signature"] == 3


def test_put_saves_thresholds_and_returns_array(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    headers = _headers(TENANT_ADMIN, user_id)

    response = db_client.put(
        "/api/v1/tracker/bottleneck-thresholds",
        json=[
            {"stage": "Drafting", "thresholdDays": 9},
            {"stage": "Approval", "thresholdDays": 2},
        ],
        headers=headers,
    )
    assert response.status_code == 200
    by_stage = {row["stage"]: row["thresholdDays"] for row in response.json()}
    assert by_stage["Drafting"] == 9
    assert by_stage["Approval"] == 2
    assert by_stage["Negotiation"] == 5

    reread = db_client.get("/api/v1/tracker/bottleneck-thresholds", headers=headers).json()
    assert {row["stage"]: row["thresholdDays"] for row in reread}["Drafting"] == 9


def test_put_rejects_non_positive_days(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    headers = _headers(TENANT_ADMIN, user_id)
    response = db_client.put(
        "/api/v1/tracker/bottleneck-thresholds",
        json=[{"stage": "Drafting", "thresholdDays": 0}],
        headers=headers,
    )
    assert response.status_code == 400

    unchanged = db_client.get("/api/v1/tracker/bottleneck-thresholds", headers=headers).json()
    assert {row["stage"]: row["thresholdDays"] for row in unchanged}["Drafting"] == 5


def test_put_rejects_unknown_stage(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.put(
        "/api/v1/tracker/bottleneck-thresholds",
        json=[{"stage": "Archiving", "thresholdDays": 4}],
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400


def test_put_rejects_disallowed_role(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER)
    response = db_client.put(
        "/api/v1/tracker/bottleneck-thresholds",
        json=[{"stage": "Drafting", "thresholdDays": 4}],
        headers=_headers(CONTRACT_OWNER, user_id),
    )
    assert response.status_code == 403


def test_put_requires_role_header(db_client):
    response = db_client.put(
        "/api/v1/tracker/bottleneck-thresholds",
        json=[{"stage": "Drafting", "thresholdDays": 4}],
    )
    assert response.status_code == 401
