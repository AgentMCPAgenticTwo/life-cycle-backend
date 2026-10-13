"""Exercises every endpoint this task owns (`/api/v1/esignature-settings`) against a real
in-memory database: the role matrix, the default-when-unconfigured path (UC7-FV-004), the
optional-field save, the whole-number validation rule, the signature-provider enum
validation, and that updates persist and round-trip through GET.
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


def test_get_requires_role_header(db_client):
    response = db_client.get("/api/v1/esignature-settings")
    assert response.status_code == 401


def test_get_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.get("/api/v1/esignature-settings", headers=_headers(APPROVER, user_id))
    assert response.status_code == 403


def test_get_defaults_when_unconfigured(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/esignature-settings", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    assert response.json() == {
        "reminderFrequencyDays": 3,
        "defaultSignatureProvider": "In-built E-signature",
    }


def test_put_then_get_round_trips(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = {"reminderFrequencyDays": 5, "defaultSignatureProvider": "DocuSign"}
    put_response = db_client.put(
        "/api/v1/esignature-settings", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert put_response.status_code == 200
    assert put_response.json() == payload

    get_response = db_client.get("/api/v1/esignature-settings", headers=_headers(TENANT_ADMIN, user_id))
    assert get_response.status_code == 200
    assert get_response.json() == payload


def test_put_blank_body_succeeds_with_defaults(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.put(
        "/api/v1/esignature-settings", json={}, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 200
    assert response.json() == {
        "reminderFrequencyDays": 3,
        "defaultSignatureProvider": "In-built E-signature",
    }


def test_put_updates_only_the_field_supplied(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.put(
        "/api/v1/esignature-settings",
        json={"reminderFrequencyDays": 7, "defaultSignatureProvider": "Adobe Sign"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    response = db_client.put(
        "/api/v1/esignature-settings",
        json={"reminderFrequencyDays": 10},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    assert response.json() == {"reminderFrequencyDays": 10, "defaultSignatureProvider": "Adobe Sign"}


def test_put_rejects_non_positive_reminder_frequency(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.put(
        "/api/v1/esignature-settings",
        json={"reminderFrequencyDays": 0},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400


def test_put_rejects_non_whole_number_reminder_frequency(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.put(
        "/api/v1/esignature-settings",
        json={"reminderFrequencyDays": 2.5},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400


def test_put_rejects_unknown_signature_provider(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.put(
        "/api/v1/esignature-settings",
        json={"defaultSignatureProvider": "Fax"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400


def test_put_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.put(
        "/api/v1/esignature-settings", json={}, headers=_headers(APPROVER, user_id)
    )
    assert response.status_code == 403
