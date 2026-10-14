"""Business rules for login/logout/refresh/change-password.

Rules that live here and nowhere else:
- wrong email OR wrong password is one indistinguishable 401 ("Invalid email or password"),
  so the endpoint cannot be used to enumerate accounts;
- a user deactivated either on `users.is_active` or via Settings > Users
  (`tenant_users.status == "Deactivated"`) gets 403, not 401 -- the credential was correct;
- refreshing rotates: the presented token is revoked and a new one issued, so a stolen
  refresh token stops working as soon as the real client refreshes;
- changing a password clears `must_change_password` and revokes every other session.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.errors import ForbiddenError, ValidationFailedError
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories import auth as auth_repo
from app.schemas.auth import AuthUserResponse, LoginResponse
from app.security import (
    PASSWORD_RULE_MESSAGE,
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    password_violations,
    refresh_token_expiry,
    verify_password,
)
from fastapi import HTTPException

INVALID_CREDENTIALS_MESSAGE = "Invalid email or password"
DEACTIVATED_MESSAGE = "This account has been deactivated. Contact your Tenant Admin."
CURRENT_PASSWORD_MESSAGE = "Current password is incorrect"
SAME_PASSWORD_MESSAGE = "New password must be different from the current password"

# Settings > Users stores a human role label; `users.role` (and X-User-Role before it, and
# every `require_roles` list) uses the role code. One mapping, used by both this module and
# `app.services.settings_users`, keeps the two tables in step.
ROLE_CODE_BY_LABEL = {
    "Tenant Admin": "TENANT_ADMIN",
    "Legal Reviewer": "LEGAL_REVIEWER",
    "Contract Owner": "CONTRACT_OWNER",
    "Approver": "APPROVER",
    "External Party": "EXTERNAL_PARTY",
    "Signer": "SIGNER",
}


def role_code_for(label: str) -> str:
    return ROLE_CODE_BY_LABEL.get(label, label.strip().upper().replace(" ", "_"))


def _unauthorized(detail: str) -> HTTPException:
    exc = HTTPException(status_code=401, detail=detail)
    exc.details = [detail]
    return exc


def to_auth_user(user: User) -> AuthUserResponse:
    return AuthUserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        tenantId=user.tenant_id,
        mustChangePassword=bool(user.must_change_password),
    )


def _assert_not_deactivated(db: Session, user: User) -> None:
    if not user.is_active:
        raise ForbiddenError(DEACTIVATED_MESSAGE, details=[DEACTIVATED_MESSAGE])
    tenant_user = auth_repo.find_tenant_user_by_email(db, user.tenant_id, user.email)
    if tenant_user is not None and tenant_user.status == "Deactivated":
        raise ForbiddenError(DEACTIVATED_MESSAGE, details=[DEACTIVATED_MESSAGE])


def issue_refresh_token(db: Session, user_id: uuid.UUID) -> str:
    raw = generate_refresh_token()
    auth_repo.insert_refresh_token(
        db,
        RefreshToken(
            user_id=user_id,
            token_hash=hash_refresh_token(raw),
            expires_at=refresh_token_expiry(),
        ),
    )
    return raw


def login(db: Session, email: str | None, password: str | None) -> tuple[LoginResponse, str]:
    if not (email or "").strip() or not (password or ""):
        raise _unauthorized(INVALID_CREDENTIALS_MESSAGE)

    user = auth_repo.find_user_by_email(db, email.strip())
    if user is None or not verify_password(password, user.password_hash):
        raise _unauthorized(INVALID_CREDENTIALS_MESSAGE)

    _assert_not_deactivated(db, user)

    user.last_login_at = datetime.now(timezone.utc)
    tenant_user = auth_repo.find_tenant_user_by_email(db, user.tenant_id, user.email)
    if tenant_user is not None:
        tenant_user.last_login = user.last_login_at
        # UC11-BR-013: an Invited user becomes Active the first time they actually sign in.
        if tenant_user.status == "Invited":
            tenant_user.status = "Active"

    refresh_raw = issue_refresh_token(db, user.id)
    access = create_access_token(user.id, user.role, user.tenant_id)
    db.commit()
    return LoginResponse(accessToken=access, user=to_auth_user(user)), refresh_raw


def refresh(db: Session, raw_token: str | None) -> tuple[str, str]:
    """Rotates: revokes the presented token and returns (accessToken, new refresh token)."""
    if not raw_token:
        raise _unauthorized("missing refresh token")
    row = auth_repo.find_live_refresh_token(db, hash_refresh_token(raw_token))
    if row is None:
        raise _unauthorized("invalid or expired refresh token")
    user = auth_repo.find_user_by_id(db, row.user_id)
    if user is None:
        auth_repo.revoke_token(db, row)
        db.commit()
        raise _unauthorized("invalid or expired refresh token")
    _assert_not_deactivated(db, user)

    auth_repo.revoke_token(db, row)
    new_raw = issue_refresh_token(db, user.id)
    access = create_access_token(user.id, user.role, user.tenant_id)
    db.commit()
    return access, new_raw


def logout(db: Session, raw_token: str | None) -> None:
    """Idempotent: logging out with no cookie, or with one already revoked, still succeeds."""
    if raw_token:
        row = auth_repo.find_live_refresh_token(db, hash_refresh_token(raw_token))
        if row is not None:
            auth_repo.revoke_token(db, row)
            db.commit()


def change_password(
    db: Session, user_id: uuid.UUID, current_password: str | None, new_password: str | None
) -> str:
    """Returns a fresh refresh token: every session established under the old password is
    revoked, and the caller who just changed it gets a replacement so they stay signed in.
    """
    user = auth_repo.find_user_by_id(db, user_id)
    if user is None:
        raise _unauthorized("invalid or expired access token")
    if not verify_password(current_password or "", user.password_hash):
        raise ValidationFailedError(CURRENT_PASSWORD_MESSAGE, details=[CURRENT_PASSWORD_MESSAGE])
    violations = password_violations(new_password)
    if violations:
        raise ValidationFailedError(PASSWORD_RULE_MESSAGE, details=violations)
    if verify_password(new_password, user.password_hash):
        raise ValidationFailedError(SAME_PASSWORD_MESSAGE, details=[SAME_PASSWORD_MESSAGE])

    user.password_hash = hash_password(new_password)
    user.must_change_password = False
    user.updated_at = datetime.now(timezone.utc)
    user.updated_by = user.id
    # Every other session was established under the old password -- drop them.
    auth_repo.revoke_all_for_user(db, user.id)
    replacement = issue_refresh_token(db, user.id)
    db.commit()
    return replacement
