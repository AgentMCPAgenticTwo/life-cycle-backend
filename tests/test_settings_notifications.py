"""Exercises every endpoint this task owns (`/api/v1/settings/notifications`): the role
matrix, the GET seeding/listing of status-change events defaulted to On (UC11-BR-007), the
PUT happy path that updates one toggle without disturbing the other (UC11-FV-004), persisted
Off values surviving a reload, and the unknown-event 404 -- see TASK.md
(T-SETTINGS-NOTIFICATIONS-API).
"""
import uuid

from app.models.tenant import Tenant
from app.models.tracker import TenantNotificationSetting
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


def test_get_requires_role_header(client):
    response = client.get("/api/v1/settings/notifications")
    assert response.status_code == 401


def test_get_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.get("/api/v1/settings/notifications", headers=_headers(APPROVER, user_id))
    assert response.status_code == 403


def test_get_seeds_all_events_with_both_toggles_on(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/settings/notifications", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    body = response.json()
    assert len(body) > 0
    names = {item["eventName"] for item in body}
    assert "Contract Sent for Approval" in names
    assert "Contract Signed" in names
    for item in body:
        assert item["emailToggle"] is True
        assert item["inAppToggle"] is True


def test_get_does_not_duplicate_events_on_repeat_calls(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    first = db_client.get("/api/v1/settings/notifications", headers=_headers(TENANT_ADMIN, user_id))
    second = db_client.get("/api/v1/settings/notifications", headers=_headers(TENANT_ADMIN, user_id))
    assert len(first.json()) == len(second.json())


def test_put_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.put(
        "/api/v1/settings/notifications/Contract Signed",
        json={"emailToggle": False},
        headers=_headers(APPROVER, user_id),
    )
    assert response.status_code == 403


def test_put_requires_role_header(client):
    response = client.put("/api/v1/settings/notifications/Contract Signed", json={"emailToggle": False})
    assert response.status_code == 401


def test_put_unknown_event_name_returns_404(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.put(
        "/api/v1/settings/notifications/Not A Real Event",
        json={"emailToggle": False},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 404


def test_put_toggles_email_without_affecting_in_app(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.get("/api/v1/settings/notifications", headers=_headers(TENANT_ADMIN, user_id))
    response = db_client.put(
        "/api/v1/settings/notifications/Contract Signed",
        json={"emailToggle": False},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eventName"] == "Contract Signed"
    assert body["emailToggle"] is False
    assert body["inAppToggle"] is True


def test_put_toggles_in_app_without_affecting_email(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.get("/api/v1/settings/notifications", headers=_headers(TENANT_ADMIN, user_id))
    response = db_client.put(
        "/api/v1/settings/notifications/Contract Signed",
        json={"inAppToggle": False},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["emailToggle"] is True
    assert body["inAppToggle"] is False


def test_put_off_value_persists_across_reload(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.put(
        "/api/v1/settings/notifications/Contract Renewed",
        json={"emailToggle": False, "inAppToggle": False},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    response = db_client.get("/api/v1/settings/notifications", headers=_headers(TENANT_ADMIN, user_id))
    renewed = next(i for i in response.json() if i["eventName"] == "Contract Renewed")
    assert renewed["emailToggle"] is False
    assert renewed["inAppToggle"] is False


def test_get_scopes_notifications_by_tenant(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.put(
        "/api/v1/settings/notifications/Contract Approved",
        json={"emailToggle": False},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    other_tenant_id, other_user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/settings/notifications", headers=_headers(TENANT_ADMIN, other_user_id))
    approved = next(i for i in response.json() if i["eventName"] == "Contract Approved")
    assert approved["emailToggle"] is True
