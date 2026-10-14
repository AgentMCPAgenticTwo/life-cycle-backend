"""Exercises every endpoint this task owns (`/api/v1/clauses*`) against a real in-memory
database: happy paths, the role matrix, and the acceptance criteria named in TASK.md --
blank-name rejection (UC3-AF-001), concurrent-save conflicts (UC3-AF-006), versioning on
save (UC3-BR-002/014), the Draft->Active transition (UC3-BR-011), deactivate/reactivate
(UC3-BR-012/013), and Contract Owner's Active-only read-only view (UC3-BR-009).
"""
import uuid

from app.models.tenant import Tenant
from app.models.user import User
from tests.conftest import auth_headers

TENANT_ADMIN = "TENANT_ADMIN"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
CONTRACT_OWNER = "CONTRACT_OWNER"
SIGNER = "SIGNER"


def _seed_tenant_and_user(db_session, role: str) -> tuple[uuid.UUID, uuid.UUID]:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
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
            email=f"{role.lower()}@acme.test",
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
    payload = {
        "clauseName": "Confidentiality Standard",
        "clauseCategory": "Confidentiality",
        "standardText": "Both parties shall keep confidential information secret.",
        "fallbackText1": "Fallback option A",
        "fallbackText2": None,
        "riskLevel": "Medium",
        "mandatory": True,
    }
    payload.update(overrides)
    return payload


def test_missing_role_header_is_401(db_client):
    resp = db_client.get("/api/v1/clauses")
    assert resp.status_code == 401
    assert "error" in resp.json() and "details" in resp.json()


def test_disallowed_role_is_403(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, SIGNER)
    resp = db_client.get("/api/v1/clauses", headers=_headers(SIGNER, user_id))
    assert resp.status_code == 403


def test_create_clause_happy_path_returns_201_active_version_1(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    resp = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    )
    assert resp.status_code == 201
    assert "Location" in resp.headers
    body = resp.json()
    assert body["clauseName"] == "Confidentiality Standard"
    assert body["clauseCategory"] == "Confidentiality"
    assert body["riskLevel"] == "Medium"
    assert body["mandatory"] is True
    assert body["status"] == "Active"
    assert body["lastModifiedBy"] == "Tenant_Admin User"
    assert uuid.UUID(body["id"])

    versions = db_client.get(
        f"/api/v1/clauses/{body['id']}/versions", headers=_headers(TENANT_ADMIN, user_id)
    ).json()
    assert len(versions["items"]) == 1
    assert versions["items"][0]["versionNumber"] == 1
    assert versions["items"][0]["changedBy"] == "Tenant_Admin User"


def test_create_clause_blocks_blank_clause_name(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, LEGAL_REVIEWER)
    resp = db_client.post(
        "/api/v1/clauses",
        json=_valid_payload(clauseName="   "),
        headers=_headers(LEGAL_REVIEWER, user_id),
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Clause Name is required."


def test_create_clause_rejects_invalid_risk_level(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    resp = db_client.post(
        "/api/v1/clauses",
        json=_valid_payload(riskLevel="Severe"),
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert resp.status_code == 400


def test_create_clause_disallowed_for_contract_owner(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER)
    resp = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(CONTRACT_OWNER, user_id)
    )
    assert resp.status_code == 403


def test_get_clauses_list_scoped_to_tenant(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    other_tenant_id, other_user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)

    db_client.post("/api/v1/clauses", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id))
    db_client.post(
        "/api/v1/clauses",
        json=_valid_payload(clauseName="Other Tenant Clause"),
        headers=_headers(TENANT_ADMIN, other_user_id),
    )

    resp = db_client.get("/api/v1/clauses", headers=_headers(TENANT_ADMIN, user_id))
    assert resp.status_code == 200
    names = [item["clauseName"] for item in resp.json()["items"]]
    assert names == ["Confidentiality Standard"]


def test_contract_owner_sees_only_active_clauses(db_client, db_session):
    tenant_id, admin_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _co_tenant, co_id = tenant_id, uuid.uuid4()
    db_session.add(
        User(
            id=co_id,
            tenant_id=tenant_id,
            name="Contract Owner User",
            email="co@acme.test",
            role=CONTRACT_OWNER,
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()

    created = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(TENANT_ADMIN, admin_id)
    ).json()
    db_client.post(
        f"/api/v1/clauses/{created['id']}/deactivate", headers=_headers(TENANT_ADMIN, admin_id)
    )

    resp = db_client.get("/api/v1/clauses", headers=_headers(CONTRACT_OWNER, co_id))
    assert resp.status_code == 200
    assert resp.json()["items"] == []


def test_update_clause_creates_new_version_and_records_editor(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, LEGAL_REVIEWER)
    created = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(LEGAL_REVIEWER, user_id)
    ).json()

    resp = db_client.put(
        f"/api/v1/clauses/{created['id']}",
        json=_valid_payload(riskLevel="High"),
        headers=_headers(LEGAL_REVIEWER, user_id),
    )
    assert resp.status_code == 200
    assert resp.json()["riskLevel"] == "High"

    versions = db_client.get(
        f"/api/v1/clauses/{created['id']}/versions", headers=_headers(LEGAL_REVIEWER, user_id)
    ).json()
    assert [v["versionNumber"] for v in versions["items"]] == [1, 2]
    assert versions["items"][1]["changeSummary"] == "Updated: Risk Level"


def test_update_clause_without_changes_does_not_create_new_version(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    created = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    ).json()

    db_client.put(
        f"/api/v1/clauses/{created['id']}",
        json=_valid_payload(),
        headers=_headers(TENANT_ADMIN, user_id),
    )

    versions = db_client.get(
        f"/api/v1/clauses/{created['id']}/versions", headers=_headers(TENANT_ADMIN, user_id)
    ).json()
    assert len(versions["items"]) == 1


def test_update_clause_blocks_concurrent_conflicting_save(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    created = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    ).json()

    # First user's save succeeds and bumps the version.
    first = db_client.put(
        f"/api/v1/clauses/{created['id']}",
        json={**_valid_payload(riskLevel="High"), "expectedVersion": 1},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert first.status_code == 200

    # Second user's save, still believing it started from version 1, is blocked.
    second = db_client.put(
        f"/api/v1/clauses/{created['id']}",
        json={**_valid_payload(clauseName="Second User Edit"), "expectedVersion": 1},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert second.status_code == 409
    assert second.json()["error"] == (
        "This clause was updated by another user. Please refresh and re-apply your changes."
    )

    # The blocked edit must not have been persisted.
    current = db_client.get("/api/v1/clauses", headers=_headers(TENANT_ADMIN, user_id)).json()
    assert current["items"][0]["clauseName"] == "Confidentiality Standard"


def test_update_clause_not_found_is_404(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    resp = db_client.put(
        f"/api/v1/clauses/{uuid.uuid4()}",
        json=_valid_payload(),
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert resp.status_code == 404


def test_deactivate_then_reactivate_round_trip(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    created = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    ).json()

    deactivated = db_client.post(
        f"/api/v1/clauses/{created['id']}/deactivate", headers=_headers(TENANT_ADMIN, user_id)
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "Inactive"
    # Only the status changed -- every other field is untouched (UC3-BR-012).
    assert deactivated.json()["clauseName"] == "Confidentiality Standard"

    reactivated = db_client.post(
        f"/api/v1/clauses/{created['id']}/reactivate", headers=_headers(TENANT_ADMIN, user_id)
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "Active"


def test_deactivate_requires_tenant_admin_role(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, LEGAL_REVIEWER)
    created = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(LEGAL_REVIEWER, user_id)
    ).json()
    resp = db_client.post(
        f"/api/v1/clauses/{created['id']}/deactivate", headers=_headers(LEGAL_REVIEWER, user_id)
    )
    assert resp.status_code == 403


def test_deactivate_already_inactive_clause_is_409(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    created = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    ).json()
    db_client.post(
        f"/api/v1/clauses/{created['id']}/deactivate", headers=_headers(TENANT_ADMIN, user_id)
    )
    resp = db_client.post(
        f"/api/v1/clauses/{created['id']}/deactivate", headers=_headers(TENANT_ADMIN, user_id)
    )
    assert resp.status_code == 409


def test_malformed_clause_id_is_400(db_client, db_session):
    _tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    resp = db_client.get(
        "/api/v1/clauses/not-a-uuid/versions", headers=_headers(TENANT_ADMIN, user_id)
    )
    assert resp.status_code == 400


def test_versions_requires_tenant_admin_or_legal_reviewer(db_client, db_session):
    tenant_id, admin_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    co_id = uuid.uuid4()
    db_session.add(
        User(
            id=co_id,
            tenant_id=tenant_id,
            name="Contract Owner User",
            email="co2@acme.test",
            role=CONTRACT_OWNER,
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()
    created = db_client.post(
        "/api/v1/clauses", json=_valid_payload(), headers=_headers(TENANT_ADMIN, admin_id)
    ).json()
    resp = db_client.get(
        f"/api/v1/clauses/{created['id']}/versions", headers=_headers(CONTRACT_OWNER, co_id)
    )
    assert resp.status_code == 403
