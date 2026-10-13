"""Exercises every endpoint this task owns (`/api/v1/settings/users`): the role matrix,
the happy path for GET/POST/PATCH, and the validation rules named in TASK.md
(T-SETTINGS-USERS-API): UC11-FV-001 (required fields/email format/role enum), UC11-AF-002 /
UC11-BR-002 (duplicate email), and UC11-AF-005 / UC11-BR-003 (last active Tenant Admin guard).
"""
import uuid

from app.models.tenant import Tenant
from app.models.tracker import TenantUser
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


def _seed_tenant_user_row(
    db_session, tenant_id: uuid.UUID, actor_id: uuid.UUID, *, role: str = "Legal Reviewer", status: str = "Active"
) -> TenantUser:
    row = TenantUser(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Jane Doe",
        email=f"jane-{uuid.uuid4()}@acme.test",
        role=role,
        status=status,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(row)
    db_session.commit()
    return row


def _valid_payload(**overrides) -> dict:
    payload = {"name": "Jane Doe", "email": f"jane-{uuid.uuid4()}@acme.test", "role": "Legal Reviewer"}
    payload.update(overrides)
    return payload


def test_get_requires_role_header(db_client):
    response = db_client.get("/api/v1/settings/users")
    assert response.status_code == 401


def test_get_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.get("/api/v1/settings/users", headers=_headers(APPROVER, user_id))
    assert response.status_code == 403


def test_get_empty_list(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.get("/api/v1/settings/users", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["page"] == 1
    assert body["pageSize"] == 20
    assert body["totalCount"] == 0


def test_post_then_get_round_trips(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload()
    response = db_client.post("/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == payload["name"]
    assert body["email"] == payload["email"]
    assert body["role"] == payload["role"]
    assert body["status"] == "Invited"
    assert body["lastLogin"] is None
    new_id = body["id"]
    uuid.UUID(new_id)  # server-generated id, not client-supplied
    assert response.headers["location"] == f"/api/v1/settings/users/{new_id}"

    list_response = db_client.get("/api/v1/settings/users", headers=_headers(TENANT_ADMIN, user_id))
    assert list_response.status_code == 200
    list_body = list_response.json()
    assert list_body["totalCount"] == 1
    assert list_body["items"][0]["id"] == new_id


def test_post_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.post(
        "/api/v1/settings/users", json=_valid_payload(), headers=_headers(APPROVER, user_id)
    )
    assert response.status_code == 403


def test_post_rejects_missing_name(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(name=None)
    response = db_client.post("/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 400
    assert "Please complete all required fields" in response.json()["details"]


def test_post_rejects_missing_email(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(email=None)
    response = db_client.post("/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 400
    assert "Please complete all required fields" in response.json()["details"]


def test_post_rejects_missing_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(role=None)
    response = db_client.post("/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 400
    assert "Please complete all required fields" in response.json()["details"]


def test_post_rejects_invalid_email_format(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(email="not-an-email")
    response = db_client.post("/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 400


def test_post_rejects_invalid_role_enum(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(role="Other")
    response = db_client.post("/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 400


def test_post_rejects_duplicate_email(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload()
    db_client.post("/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id))

    response = db_client.post(
        "/api/v1/settings/users", json=_valid_payload(email=payload["email"]), headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 409
    assert "A user with this email already exists" in response.json()["details"]


def test_post_allows_same_email_in_different_tenant(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    other_tenant_id, other_user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload()
    db_client.post("/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id))

    response = db_client.post(
        "/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, other_user_id)
    )
    assert response.status_code == 201


def test_get_scopes_users_by_tenant(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    other_tenant_id, other_user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    db_client.post("/api/v1/settings/users", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id))

    response = db_client.get("/api/v1/settings/users", headers=_headers(TENANT_ADMIN, other_user_id))
    assert response.status_code == 200
    assert response.json()["totalCount"] == 0


def test_patch_status_requires_role_header(db_client):
    response = db_client.patch(f"/api/v1/settings/users/{uuid.uuid4()}/status", json={"status": "Active"})
    assert response.status_code == 401


def test_patch_status_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    row = _seed_tenant_user_row(db_session, tenant_id, user_id, status="Invited")
    response = db_client.patch(
        f"/api/v1/settings/users/{row.id}/status", json={"status": "Active"}, headers=_headers(APPROVER, user_id)
    )
    assert response.status_code == 403


def test_patch_status_404_for_unknown_user(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.patch(
        f"/api/v1/settings/users/{uuid.uuid4()}/status",
        json={"status": "Active"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 404


def test_patch_status_rejects_invalid_status_value(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    row = _seed_tenant_user_row(db_session, tenant_id, user_id, status="Invited")
    response = db_client.patch(
        f"/api/v1/settings/users/{row.id}/status",
        json={"status": "Bogus"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400


def test_patch_status_invited_to_active_auto_activate(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    row = _seed_tenant_user_row(db_session, tenant_id, user_id, status="Invited")
    response = db_client.patch(
        f"/api/v1/settings/users/{row.id}/status",
        json={"status": "Active"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Active"


def test_patch_status_active_to_deactivated(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    row = _seed_tenant_user_row(db_session, tenant_id, user_id, status="Active")
    response = db_client.patch(
        f"/api/v1/settings/users/{row.id}/status",
        json={"status": "Deactivated"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Deactivated"


def test_patch_status_deactivated_to_active_reactivate(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    row = _seed_tenant_user_row(db_session, tenant_id, user_id, status="Deactivated")
    response = db_client.patch(
        f"/api/v1/settings/users/{row.id}/status",
        json={"status": "Active"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Active"


def test_patch_status_blocks_deactivating_last_active_tenant_admin(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    # `user_id` (seeded via `_seed_tenant_and_user`) is a row in the shared `users` table, not
    # `tenant_users` -- this task's last-admin guard operates on `tenant_users` rows, so seed
    # the sole active Tenant Admin there directly.
    admin_row = _seed_tenant_user_row(db_session, tenant_id, user_id, role="Tenant Admin", status="Active")

    response = db_client.patch(
        f"/api/v1/settings/users/{admin_row.id}/status",
        json={"status": "Deactivated"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 409
    assert "At least one Tenant Admin must remain active" in response.json()["details"]

    # Still unchanged.
    list_response = db_client.get("/api/v1/settings/users", headers=_headers(TENANT_ADMIN, user_id))
    row = next(item for item in list_response.json()["items"] if item["id"] == str(admin_row.id))
    assert row["status"] == "Active"


def test_patch_status_allows_deactivating_one_of_several_active_tenant_admins(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    first_admin = _seed_tenant_user_row(db_session, tenant_id, user_id, role="Tenant Admin", status="Active")
    _seed_tenant_user_row(db_session, tenant_id, user_id, role="Tenant Admin", status="Active")

    response = db_client.patch(
        f"/api/v1/settings/users/{first_admin.id}/status",
        json={"status": "Deactivated"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    assert response.json()["status"] == "Deactivated"


# ---- initial password / reset password --------------------------------------------------


def test_create_user_without_initial_password_returns_a_generated_one(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload()

    response = db_client.post(
        "/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 201
    temporary = response.json()["temporaryPassword"]
    assert temporary and len(temporary) >= 8

    # The generated password actually signs that user in, and forces a change first.
    login = db_client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": temporary}
    )
    assert login.status_code == 200
    assert login.json()["user"]["mustChangePassword"] is True
    assert login.json()["user"]["role"] == "LEGAL_REVIEWER"


def test_create_user_with_an_explicit_initial_password(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(initialPassword="Ch0sen!pass")

    response = db_client.post(
        "/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 201
    assert response.json()["temporaryPassword"] == "Ch0sen!pass"
    login = db_client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": "Ch0sen!pass"}
    )
    assert login.status_code == 200


def test_create_user_rejects_a_weak_initial_password(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/settings/users",
        json=_valid_payload(initialPassword="weakpass"),
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400
    assert response.json()["details"]


def test_the_password_is_never_returned_again_after_creation(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    created = db_client.post(
        "/api/v1/settings/users", json=_valid_payload(), headers=_headers(TENANT_ADMIN, user_id)
    ).json()

    listed = db_client.get("/api/v1/settings/users", headers=_headers(TENANT_ADMIN, user_id))
    row = next(item for item in listed.json()["items"] if item["id"] == created["id"])
    assert "temporaryPassword" not in row


def test_reset_password_issues_a_new_temporary_password(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(initialPassword="Ch0sen!pass")
    created = db_client.post(
        "/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    ).json()

    response = db_client.post(
        f"/api/v1/settings/users/{created['id']}/reset-password",
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    new_password = response.json()["temporaryPassword"]
    assert new_password != "Ch0sen!pass"

    stale = db_client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": "Ch0sen!pass"}
    )
    assert stale.status_code == 401
    fresh = db_client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": new_password}
    )
    assert fresh.status_code == 200


def test_reset_password_for_unknown_user_is_404(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        f"/api/v1/settings/users/{uuid.uuid4()}/reset-password",
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 404


def test_reset_password_rejects_a_non_admin_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, APPROVER)
    response = db_client.post(
        f"/api/v1/settings/users/{uuid.uuid4()}/reset-password",
        headers=_headers(APPROVER, user_id),
    )
    assert response.status_code == 403


def test_deactivating_a_user_blocks_their_login(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    payload = _valid_payload(initialPassword="Ch0sen!pass")
    created = db_client.post(
        "/api/v1/settings/users", json=payload, headers=_headers(TENANT_ADMIN, user_id)
    ).json()

    db_client.patch(
        f"/api/v1/settings/users/{created['id']}/status",
        json={"status": "Deactivated"},
        headers=_headers(TENANT_ADMIN, user_id),
    )
    response = db_client.post(
        "/api/v1/auth/login", json={"email": payload["email"], "password": "Ch0sen!pass"}
    )
    assert response.status_code == 403
