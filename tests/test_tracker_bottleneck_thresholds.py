"""Exercises `GET /api/v1/tracker/bottleneck-thresholds` (T-TRACKER-BOTTLENECK-THRESHOLDS-API):
the role matrix, the four-stage default thresholds (UC10-BR-002), and tenant overrides.
"""
import uuid

from app.models.tenant import Tenant
from app.models.tracker import TenantBottleneckThreshold
from app.models.user import User

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
    return {"X-User-Role": role, "X-User-Id": str(user_id)}


def test_requires_role_header(client):
    response = client.get("/api/v1/tracker/bottleneck-thresholds")
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
