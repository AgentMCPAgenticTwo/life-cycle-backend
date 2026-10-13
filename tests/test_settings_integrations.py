"""Exercises every endpoint this task owns (`/api/v1/settings/integrations`): the role
matrix, the GET seeding/listing of the 7 fixed integration cards, the connect/disconnect
happy paths and UC11-BR-009's credential masking, UC11-AF-004's invalid-credentials failure
message, and UC11-AF-007's automatic token-expiry transition -- see TASK.md
(T-SETTINGS-INTEGRATIONS-API).
"""
import uuid
from datetime import datetime, timedelta, timezone

from app.models.tenant import Tenant
from app.models.tracker import TenantIntegration
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
    response = db_client.get("/api/v1/settings/integrations")
    assert response.status_code == 401


def test_get_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.get("/api/v1/settings/integrations", headers=_headers(APPROVER, user_id))
    assert response.status_code == 403


def test_get_seeds_all_seven_cards_disconnected(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/settings/integrations", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 7
    names = {item["integrationName"] for item in body}
    assert names == {
        "Salesforce",
        "HubSpot",
        "ERP",
        "Google Drive",
        "SharePoint",
        "DocuSign",
        "Adobe Sign",
    }
    for item in body:
        assert item["connectionStatus"] == "Disconnected"
        assert item["maskedCredential"] is None


def test_get_does_not_duplicate_cards_on_repeat_calls(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.get("/api/v1/settings/integrations", headers=_headers(TENANT_ADMIN, user_id))
    response = db_client.get("/api/v1/settings/integrations", headers=_headers(TENANT_ADMIN, user_id))
    assert len(response.json()) == 7


def test_connect_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.post(
        "/api/v1/settings/integrations/Salesforce/connect",
        json={"credentials": {"apiKey": "abc12345"}},
        headers=_headers(APPROVER, user_id),
    )
    assert response.status_code == 403


def test_connect_unknown_integration_name_returns_404(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/settings/integrations/NotARealIntegration/connect",
        json={"credentials": {"apiKey": "abc12345"}},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 404


def test_connect_with_invalid_credentials_stays_disconnected(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/settings/integrations/Salesforce/connect",
        json={"credentials": {}},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400
    assert "Connection failed. Please check your credentials and try again" in response.json()["details"]

    list_response = db_client.get("/api/v1/settings/integrations", headers=_headers(TENANT_ADMIN, user_id))
    salesforce = next(i for i in list_response.json() if i["integrationName"] == "Salesforce")
    assert salesforce["connectionStatus"] == "Disconnected"


def test_connect_with_blank_credential_value_is_rejected(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/settings/integrations/HubSpot/connect",
        json={"credentials": {"apiKey": "   "}},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400


def test_connect_with_valid_credentials_transitions_to_connected_and_masks(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/settings/integrations/DocuSign/connect",
        json={"credentials": {"apiKey": "sk-abcd1234"}},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["integrationName"] == "DocuSign"
    assert body["connectionStatus"] == "Connected"
    assert body["maskedCredential"] is not None
    assert "1234" in body["maskedCredential"]
    assert "sk-abcd1234" not in body["maskedCredential"]


def test_connect_then_get_never_exposes_plaintext_credential(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.post(
        "/api/v1/settings/integrations/ERP/connect",
        json={"credentials": {"token": "plaintext-secret-value"}},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    response = db_client.get("/api/v1/settings/integrations", headers=_headers(TENANT_ADMIN, user_id))
    erp = next(i for i in response.json() if i["integrationName"] == "ERP")
    assert "plaintext-secret-value" not in str(erp)
    assert erp["connectionStatus"] == "Connected"


def test_disconnect_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.post(
        "/api/v1/settings/integrations/Salesforce/disconnect", headers=_headers(APPROVER, user_id)
    )
    assert response.status_code == 403


def test_disconnect_unknown_integration_name_returns_404(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/settings/integrations/NotARealIntegration/disconnect",
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 404


def test_disconnect_connected_integration_transitions_back(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.post(
        "/api/v1/settings/integrations/SharePoint/connect",
        json={"credentials": {"apiKey": "abc12345"}},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    response = db_client.post(
        "/api/v1/settings/integrations/SharePoint/disconnect", headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["connectionStatus"] == "Disconnected"


def test_expired_token_surfaces_reconnect_required_on_get(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.post(
        "/api/v1/settings/integrations/Google Drive/connect",
        json={"credentials": {"apiKey": "abc12345"}},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    row = (
        db_session.query(TenantIntegration)
        .filter(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_name == "Google Drive",
        )
        .first()
    )
    row.token_expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db_session.commit()

    response = db_client.get("/api/v1/settings/integrations", headers=_headers(TENANT_ADMIN, user_id))
    drive = next(i for i in response.json() if i["integrationName"] == "Google Drive")
    assert drive["connectionStatus"] == "Disconnected - reconnect required"


def test_get_scopes_integrations_by_tenant(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.post(
        "/api/v1/settings/integrations/Salesforce/connect",
        json={"credentials": {"apiKey": "abc12345"}},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    other_tenant_id, other_user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/settings/integrations", headers=_headers(TENANT_ADMIN, other_user_id))
    salesforce = next(i for i in response.json() if i["integrationName"] == "Salesforce")
    assert salesforce["connectionStatus"] == "Disconnected"
