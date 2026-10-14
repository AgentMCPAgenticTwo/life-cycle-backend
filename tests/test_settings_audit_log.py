"""Exercises `/api/v1/settings/audit-log` (T-SETTINGS-AUDIT-LOG-API): the role matrix,
newest-first ordering (UC11-GC-003), the Filter Date Range/user/action type filters
(UC11-FV-005), tenant scoping, and read-only-ness (UC11-BR-005/BR-011 -- no edit/delete
route exists for this resource at all).
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.errors import ImmutableResourceError
from app.models.tenant import Tenant
from app.models.tracker import TenantAuditLog
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


def _add_entry(
    db_session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    log_date_time: datetime,
    log_user: str = "System",
    log_action: str = "Created",
    log_entity: str = "User",
    details: str | None = None,
) -> TenantAuditLog:
    entry = TenantAuditLog(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        log_date_time=log_date_time,
        log_user=log_user,
        log_action=log_action,
        log_entity=log_entity,
        details=details,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(entry)
    db_session.commit()
    return entry


def test_get_requires_role_header(db_client):
    response = db_client.get("/api/v1/settings/audit-log")
    assert response.status_code == 401


def test_get_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.get("/api/v1/settings/audit-log", headers=_headers(APPROVER, user_id))
    assert response.status_code == 403


def test_get_empty_list(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/settings/audit-log", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert body["totalCount"] == 0


def test_get_returns_entries_sorted_newest_first(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    now = datetime.now(timezone.utc)
    older = _add_entry(db_session, tenant_id, user_id, log_date_time=now - timedelta(days=2))
    newer = _add_entry(db_session, tenant_id, user_id, log_date_time=now - timedelta(hours=1))

    response = db_client.get("/api/v1/settings/audit-log", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 2
    assert [item["id"] for item in body["items"]] == [str(newer.id), str(older.id)]

    first = body["items"][0]
    assert first["logUser"] == "System"
    assert first["logAction"] == "Created"
    assert first["logEntity"] == "User"


def test_get_filters_by_date_range(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    now = datetime.now(timezone.utc)
    in_range = _add_entry(db_session, tenant_id, user_id, log_date_time=now - timedelta(days=1))
    _add_entry(db_session, tenant_id, user_id, log_date_time=now - timedelta(days=30))

    from_date = (now - timedelta(days=5)).date().isoformat()
    to_date = now.date().isoformat()
    response = db_client.get(
        "/api/v1/settings/audit-log",
        params={"filterDateRangeFrom": from_date, "filterDateRangeTo": to_date},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 1
    assert body["items"][0]["id"] == str(in_range.id)


def test_get_filters_by_user_and_action_type(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    now = datetime.now(timezone.utc)
    _add_entry(db_session, tenant_id, user_id, log_date_time=now, log_user="Alice", log_action="Created")
    matching = _add_entry(
        db_session, tenant_id, user_id, log_date_time=now, log_user="Bob", log_action="Updated"
    )

    response = db_client.get(
        "/api/v1/settings/audit-log",
        params={"userFilter": "Bob", "actionTypeFilter": "Updated"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["totalCount"] == 1
    assert body["items"][0]["id"] == str(matching.id)


def test_get_scopes_entries_by_tenant(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    other_tenant_id, other_user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _add_entry(db_session, tenant_id, user_id, log_date_time=datetime.now(timezone.utc))

    response = db_client.get(
        "/api/v1/settings/audit-log", headers=_headers(TENANT_ADMIN, other_user_id)
    )
    assert response.status_code == 200
    assert response.json()["totalCount"] == 0


def test_no_write_routes_exist_for_audit_log(db_client, db_session):
    """UC11-BR-005/BR-011: the audit log is read-only. An edit or delete attempt is refused
    with the rule's own message, and the same rule is enforced again at the persistence
    layer so a caller holding the row cannot mutate it either."""
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    entry = _add_entry(db_session, tenant_id, user_id, log_date_time=datetime.now(timezone.utc))
    headers = _headers(TENANT_ADMIN, user_id)
    base = f"/api/v1/settings/audit-log/{entry.id}"

    for resp in (
        db_client.put(base, json={}, headers=headers),
        db_client.patch(base, json={}, headers=headers),
        db_client.delete(base, headers=headers),
    ):
        assert resp.status_code == 403
        assert resp.json()["error"] == "Audit log entries cannot be modified or deleted."

    entry.details = "tampered"
    try:
        db_session.flush()
        raise AssertionError("expected the flush to be blocked")
    except ImmutableResourceError as exc:
        assert exc.detail == "Audit log entries cannot be modified or deleted."
    db_session.rollback()

    db_session.delete(db_session.query(TenantAuditLog).first())
    try:
        db_session.flush()
        raise AssertionError("expected the delete to be blocked")
    except ImmutableResourceError:
        pass
    db_session.rollback()
