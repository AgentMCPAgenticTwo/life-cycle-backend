"""Exercises every endpoint this task owns (`/api/v1/counterparties`) against a real
in-memory database: the role matrix, tenant isolation, search with GST/Tax ID duplicate
warning (UC2-AF-008), and Create validation -- mandatory fields (UC2-FV-002), email format
(UC2-FV-001/002), and blocking a duplicate GST/Tax ID on create (UC2-AF-008).
"""
import uuid

from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"


def _headers(role: str, user_id: uuid.UUID) -> dict:
    return auth_headers(role, user_id)


def _seed_tenant(db_session) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    seed_id = uuid.uuid4()
    db_session.add(
        Tenant(
            id=tenant_id,
            name="Acme Co",
            high_risk_threshold=70,
            created_by=seed_id,
            updated_by=seed_id,
        )
    )
    db_session.commit()
    return tenant_id


def _seed_user(db_session, tenant_id: uuid.UUID, role: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(
        User(
            id=user_id,
            tenant_id=tenant_id,
            name=f"{role.title()} User",
            email=f"{user_id}@acme.test",
            role=role,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()
    return user_id


def _seed_counterparty(
    db_session, tenant_id: uuid.UUID, admin_id: uuid.UUID, *, name="Globex Contact",
    company="Globex Corp", gst_tax_id: str | None = "GST-123",
) -> uuid.UUID:
    counterparty_id = uuid.uuid4()
    db_session.add(
        Counterparty(
            id=counterparty_id,
            tenant_id=tenant_id,
            name=name,
            email="contact@globex.test",
            company=company,
            gst_tax_id=gst_tax_id,
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()
    return counterparty_id


def _valid_payload(**overrides) -> dict:
    payload = {
        "name": "Initech Contact",
        "email": "contact@initech.test",
        "company": "Initech LLC",
    }
    payload.update(overrides)
    return payload


# ---- role / auth matrix -----------------------------------------------------------------


def test_missing_role_header_is_401(db_client):
    resp = db_client.get("/api/v1/counterparties")
    assert resp.status_code == 401
    assert "error" in resp.json() and "details" in resp.json()


def test_search_disallowed_role_is_403(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    resp = db_client.get("/api/v1/counterparties", headers=_headers(LEGAL_REVIEWER, reviewer_id))
    assert resp.status_code == 403


def test_create_disallowed_role_is_403(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    resp = db_client.post(
        "/api/v1/counterparties",
        json=_valid_payload(),
        headers=_headers(LEGAL_REVIEWER, reviewer_id),
    )
    assert resp.status_code == 403


# ---- search (UC2-MF-001, UC2-AF-008) -----------------------------------------------------


def test_search_scoped_to_tenant(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    _seed_counterparty(db_session, tenant_id, admin_id)

    other_tenant_id = _seed_tenant(db_session)
    other_admin_id = _seed_user(db_session, other_tenant_id, TENANT_ADMIN)
    _seed_counterparty(db_session, other_tenant_id, other_admin_id, name="Other Tenant Co")

    resp = db_client.get("/api/v1/counterparties", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Globex Contact"


def test_search_by_name_filters_results(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    _seed_counterparty(db_session, tenant_id, admin_id, name="Globex Contact", gst_tax_id="GST-1")
    _seed_counterparty(db_session, tenant_id, admin_id, name="Initech Contact", gst_tax_id="GST-2")

    resp = db_client.get(
        "/api/v1/counterparties",
        params={"search": "Initech"},
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["name"] == "Initech Contact"
    assert body["duplicateWarning"] is None


def test_search_by_gst_tax_id_returns_duplicate_warning(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    _seed_counterparty(db_session, tenant_id, admin_id, gst_tax_id="GST-123")

    resp = db_client.get(
        "/api/v1/counterparties",
        params={"search": "GST-123"},
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["items"]) == 1
    assert body["duplicateWarning"] == "A counterparty with this Tax ID already exists"


def test_search_with_no_match_returns_empty_items_no_warning(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)

    resp = db_client.get(
        "/api/v1/counterparties",
        params={"search": "Nonexistent"},
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["items"] == []
    assert body["duplicateWarning"] is None


# ---- create happy path (UC2-MF-001, UC2-FV-002) -------------------------------------------


def test_create_counterparty_happy_path_returns_201(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.post(
        "/api/v1/counterparties",
        json=_valid_payload(gstTaxId="GST-999"),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 201
    assert "Location" in resp.headers
    body = resp.json()
    assert body["name"] == "Initech Contact"
    assert body["email"] == "contact@initech.test"
    assert body["company"] == "Initech LLC"
    assert body["gstTaxId"] == "GST-999"
    assert uuid.UUID(body["id"])
    assert resp.headers["Location"] == f"/api/v1/counterparties/{body['id']}"


def test_create_counterparty_allowed_for_contract_owner(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    resp = db_client.post(
        "/api/v1/counterparties", json=_valid_payload(), headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 201


def test_create_counterparty_without_gst_tax_id_succeeds(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.post(
        "/api/v1/counterparties", json=_valid_payload(), headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 201
    assert resp.json()["gstTaxId"] is None


# ---- mandatory-field / email validation (UC2-FV-001/002) -----------------------------------


def test_create_counterparty_blank_name_is_400(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    payload = _valid_payload(name="   ")
    resp = db_client.post(
        "/api/v1/counterparties", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Please fill all mandatory fields"
    assert "Counterparty Name is required." in resp.json()["details"]


def test_create_counterparty_blank_company_is_400(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    payload = _valid_payload(company="   ")
    resp = db_client.post(
        "/api/v1/counterparties", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert "Counterparty Company is required." in resp.json()["details"]


def test_create_counterparty_invalid_email_is_400(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    payload = _valid_payload(email="not-an-email")
    resp = db_client.post(
        "/api/v1/counterparties", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Counterparty Email must be a valid email address."


# ---- GST/Tax ID duplicate blocking (UC2-AF-008) ---------------------------------------------


def test_create_counterparty_blocks_duplicate_gst_tax_id(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    _seed_counterparty(db_session, tenant_id, admin_id, gst_tax_id="GST-DUP")

    resp = db_client.post(
        "/api/v1/counterparties",
        json=_valid_payload(gstTaxId="GST-DUP"),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 409
    assert resp.json()["error"] == "A counterparty with this Tax ID already exists"


def test_create_counterparty_duplicate_gst_tax_id_case_insensitive(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    _seed_counterparty(db_session, tenant_id, admin_id, gst_tax_id="gst-dup")

    resp = db_client.post(
        "/api/v1/counterparties",
        json=_valid_payload(gstTaxId="GST-DUP"),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 409


def test_create_counterparty_duplicate_gst_tax_id_scoped_to_tenant(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)

    other_tenant_id = _seed_tenant(db_session)
    other_admin_id = _seed_user(db_session, other_tenant_id, TENANT_ADMIN)
    _seed_counterparty(db_session, other_tenant_id, other_admin_id, gst_tax_id="GST-SHARED")

    resp = db_client.post(
        "/api/v1/counterparties",
        json=_valid_payload(gstTaxId="GST-SHARED"),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 201


def test_create_counterparty_no_duplicate_creates_normally(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.post(
        "/api/v1/counterparties",
        json=_valid_payload(gstTaxId="GST-UNIQUE"),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 201
    assert resp.json()["gstTaxId"] == "GST-UNIQUE"
