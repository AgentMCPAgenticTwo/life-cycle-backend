"""Exercises real authentication end-to-end through the error-handling layer in app/main.py.

Covers the Bearer dependency itself (missing header -> 401, tampered token -> 401, a role
outside the endpoint's allow-list -> 403, deactivated user -> 403) and the whole
`/api/v1/auth/*` resource: login, refresh rotation, logout, /me and change-password.
"""
import uuid

from fastapi import Depends

from app.auth import CurrentUser, require_roles
from app.main import app
from app.models.refresh_token import RefreshToken
from app.models.tenant import Tenant
from app.models.tracker import TenantUser
from app.models.user import User
from app.security import create_access_token, hash_password
from tests.conftest import auth_headers

TENANT_ADMIN = "TENANT_ADMIN"
APPROVER = "APPROVER"
PASSWORD = "Str0ng!pass"


@app.get("/_test/protected")
def _protected(user: CurrentUser = Depends(require_roles(TENANT_ADMIN))) -> dict:
    return {"role": user.role}


def _seed_user(
    db_session,
    *,
    role: str = TENANT_ADMIN,
    password: str | None = PASSWORD,
    is_active: bool = True,
    must_change_password: bool = False,
    tenant_status: str | None = None,
) -> User:
    tenant_id = uuid.uuid4()
    user_id = uuid.uuid4()
    email = f"user-{user_id}@acme.test"
    db_session.add(
        Tenant(
            id=tenant_id,
            name="Acme Co",
            high_risk_threshold=70,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    user = User(
        id=user_id,
        tenant_id=tenant_id,
        name="Ada Lovelace",
        email=email,
        role=role,
        password_hash=hash_password(password) if password else None,
        is_active=is_active,
        must_change_password=must_change_password,
        created_by=user_id,
        updated_by=user_id,
    )
    db_session.add(user)
    if tenant_status is not None:
        db_session.add(
            TenantUser(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                name="Ada Lovelace",
                email=email,
                role="Tenant Admin",
                status=tenant_status,
                created_by=user_id,
                updated_by=user_id,
            )
        )
    db_session.commit()
    return user


# --- the Bearer dependency -------------------------------------------------------------


def test_missing_authorization_header_is_401(db_client):
    response = db_client.get("/_test/protected")
    assert response.status_code == 401
    body = response.json()
    assert "error" in body and "details" in body


def test_garbage_token_is_401(db_client):
    response = db_client.get("/_test/protected", headers={"Authorization": "Bearer not-a-jwt"})
    assert response.status_code == 401


def test_token_for_unknown_user_is_401(db_client):
    token = create_access_token(uuid.uuid4(), TENANT_ADMIN, uuid.uuid4())
    response = db_client.get("/_test/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_disallowed_role_is_403(db_client, db_session):
    user = _seed_user(db_session, role=APPROVER)
    response = db_client.get("/_test/protected", headers=auth_headers(APPROVER, user.id))
    assert response.status_code == 403


def test_permitted_role_is_200(db_client, db_session):
    user = _seed_user(db_session)
    response = db_client.get("/_test/protected", headers=auth_headers(TENANT_ADMIN, user.id))
    assert response.status_code == 200
    assert response.json() == {"role": TENANT_ADMIN}


def test_deactivated_user_cannot_use_a_valid_token(db_client, db_session):
    user = _seed_user(db_session, is_active=False)
    response = db_client.get("/_test/protected", headers=auth_headers(TENANT_ADMIN, user.id))
    assert response.status_code == 403


def test_role_is_read_from_the_database_not_the_token(db_client, db_session):
    """A token minted with TENANT_ADMIN for an APPROVER row must not escalate."""
    user = _seed_user(db_session, role=APPROVER)
    response = db_client.get("/_test/protected", headers=auth_headers(TENANT_ADMIN, user.id))
    assert response.status_code == 403


def test_openapi_declares_the_bearer_security_scheme(db_client):
    """Regression guard: without a declared scheme the docs UI shows no "Authorize" input
    and every "try it out" call comes back 401 while the API itself is fine.
    """
    schemes = db_client.get("/openapi.json").json()["components"]["securitySchemes"]
    assert any(s.get("type") == "http" and s.get("scheme") == "bearer" for s in schemes.values())


# --- /auth/login -----------------------------------------------------------------------


def test_login_returns_access_token_user_and_refresh_cookie(db_client, db_session):
    user = _seed_user(db_session, must_change_password=True)
    response = db_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["accessToken"]
    assert body["user"] == {
        "id": str(user.id),
        "name": "Ada Lovelace",
        "email": user.email,
        "role": TENANT_ADMIN,
        "tenantId": str(user.tenant_id),
        "mustChangePassword": True,
    }
    assert "refreshToken" in response.cookies


def test_login_with_wrong_password_is_401(db_client, db_session):
    user = _seed_user(db_session)
    response = db_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": "Wr0ng!pass"}
    )
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid email or password"


def test_login_with_unknown_email_is_the_same_401(db_client, db_session):
    _seed_user(db_session)
    response = db_client.post(
        "/api/v1/auth/login", json={"email": "nobody@acme.test", "password": PASSWORD}
    )
    assert response.status_code == 401
    assert response.json()["error"] == "Invalid email or password"


def test_login_for_deactivated_user_is_403(db_client, db_session):
    user = _seed_user(db_session, is_active=False)
    response = db_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 403


def test_login_for_user_deactivated_in_settings_is_403(db_client, db_session):
    user = _seed_user(db_session, tenant_status="Deactivated")
    response = db_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    )
    assert response.status_code == 403


def test_login_activates_an_invited_user_and_stamps_last_login(db_client, db_session):
    user = _seed_user(db_session, tenant_status="Invited")
    assert (
        db_client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 200
    )
    db_session.expire_all()
    assert db_session.get(User, user.id).last_login_at is not None
    row = db_session.query(TenantUser).filter(TenantUser.email == user.email).first()
    assert row.status == "Active"


def test_login_token_authenticates_a_protected_endpoint(db_client, db_session):
    user = _seed_user(db_session)
    token = db_client.post(
        "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
    ).json()["accessToken"]
    response = db_client.get("/_test/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200


# --- /auth/refresh, /auth/logout, /auth/me ----------------------------------------------


def test_refresh_rotates_the_token_and_the_old_one_stops_working(db_client, db_session):
    user = _seed_user(db_session)
    db_client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    first_cookie = db_client.cookies.get("refreshToken")

    refreshed = db_client.post("/api/v1/auth/refresh")
    assert refreshed.status_code == 200
    assert refreshed.json()["accessToken"]
    assert db_client.cookies.get("refreshToken") != first_cookie

    db_client.cookies.set("refreshToken", first_cookie)
    assert db_client.post("/api/v1/auth/refresh").status_code == 401


def test_refresh_without_a_cookie_is_401(db_client):
    assert db_client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_the_refresh_token(db_client, db_session):
    user = _seed_user(db_session)
    db_client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    cookie = db_client.cookies.get("refreshToken")

    assert db_client.post("/api/v1/auth/logout").status_code == 204

    db_client.cookies.set("refreshToken", cookie)
    assert db_client.post("/api/v1/auth/refresh").status_code == 401


def test_me_returns_the_signed_in_user(db_client, db_session):
    user = _seed_user(db_session, must_change_password=True)
    response = db_client.get("/api/v1/auth/me", headers=auth_headers(TENANT_ADMIN, user.id))
    assert response.status_code == 200
    assert response.json()["email"] == user.email
    assert response.json()["mustChangePassword"] is True


def test_me_without_a_token_is_401(db_client):
    assert db_client.get("/api/v1/auth/me").status_code == 401


# --- /auth/change-password ---------------------------------------------------------------


def test_change_password_clears_the_flag_and_revokes_other_sessions(db_client, db_session):
    user = _seed_user(db_session, must_change_password=True)
    db_client.post("/api/v1/auth/login", json={"email": user.email, "password": PASSWORD})
    live = db_session.query(RefreshToken).filter(
        RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
    )
    assert live.count() == 1

    response = db_client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": PASSWORD, "newPassword": "N3w!password"},
        headers=auth_headers(TENANT_ADMIN, user.id),
    )
    assert response.status_code == 204

    db_session.expire_all()
    assert db_session.get(User, user.id).must_change_password is False
    # The session opened under the old password is gone; the caller keeps the replacement.
    assert live.count() == 1

    assert (
        db_client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": "N3w!password"}
        ).status_code
        == 200
    )
    assert (
        db_client.post(
            "/api/v1/auth/login", json={"email": user.email, "password": PASSWORD}
        ).status_code
        == 401
    )


def test_change_password_with_wrong_current_password_is_400(db_client, db_session):
    user = _seed_user(db_session)
    response = db_client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": "Wr0ng!pass", "newPassword": "N3w!password"},
        headers=auth_headers(TENANT_ADMIN, user.id),
    )
    assert response.status_code == 400


def test_change_password_rejects_a_weak_new_password(db_client, db_session):
    user = _seed_user(db_session)
    response = db_client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": PASSWORD, "newPassword": "weak"},
        headers=auth_headers(TENANT_ADMIN, user.id),
    )
    assert response.status_code == 400
    assert response.json()["details"]


def test_change_password_without_a_token_is_401(db_client):
    response = db_client.post(
        "/api/v1/auth/change-password",
        json={"currentPassword": PASSWORD, "newPassword": "N3w!password"},
    )
    assert response.status_code == 401
