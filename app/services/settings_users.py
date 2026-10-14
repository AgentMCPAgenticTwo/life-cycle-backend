"""Business rules for the `settings/users` resource: required-field and email-format/role
validation (UC11-FV-001), the duplicate-email guard (UC11-AF-002, UC11-BR-002), the
Invited/Active/Deactivated status transitions (UC11-BR-013, UC11-BR-014, UC11-BR-015) and
the last-active-Tenant-Admin guard (UC11-AF-005, UC11-BR-003) -- see CLAUDE.md's
lifecycle-uc10-uc11 module section and TASK.md (T-SETTINGS-USERS-API).
"""
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models.tracker import TenantAuditLog, TenantUser
from app.models.user import User
from app.repositories import auth as auth_repo
from app.repositories import settings_audit_log as audit_log_repo
from app.repositories import settings_users as users_repo
from app.schemas.pagination import PageParams
from app.schemas.settings_users import (
    CreateUserRequest,
    CreateUserResponse,
    ResetPasswordResponse,
    UserListItemResponse,
    UserListResponse,
    UpdateUserStatusRequest,
)
from app.security import PASSWORD_RULE_MESSAGE, generate_password, hash_password, password_violations
from app.services.auth import role_code_for

REQUIRED_FIELDS_MESSAGE = "Please complete all required fields"
EMAIL_FORMAT_MESSAGE = "User Email must be a valid email address."
ROLE_MESSAGE = "User Role must be one of: Approver, Contract Owner, External Party, Legal Reviewer, Signer, Tenant Admin."
DUPLICATE_EMAIL_MESSAGE = "A user with this email already exists"
STATUS_MESSAGE = "User Status must be one of: Active, Deactivated, Invited."
LAST_ADMIN_MESSAGE = "At least one Tenant Admin must remain active"

_ROLES = {"Tenant Admin", "Legal Reviewer", "Contract Owner", "Approver", "External Party", "Signer"}
_STATUSES = {"Invited", "Active", "Deactivated"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _safe_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except (ValueError, TypeError):
        return uuid.UUID(int=0)


def _validate_create(payload: CreateUserRequest) -> None:
    if _is_blank(payload.name) or _is_blank(payload.email) or _is_blank(payload.role):
        raise ValidationFailedError(REQUIRED_FIELDS_MESSAGE, details=[REQUIRED_FIELDS_MESSAGE])
    if not _EMAIL_RE.match(payload.email.strip()):
        raise ValidationFailedError(EMAIL_FORMAT_MESSAGE, details=[EMAIL_FORMAT_MESSAGE])
    if payload.role not in _ROLES:
        raise ValidationFailedError(ROLE_MESSAGE, details=[ROLE_MESSAGE])


def _to_response(user: TenantUser) -> UserListItemResponse:
    return UserListItemResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
        status=user.status,
        lastLogin=user.last_login,
    )


def _log(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    *,
    action: str,
    entity_label: str,
    details: str,
) -> None:
    now = datetime.now(timezone.utc)
    user_uuid = _safe_uuid(user.user_id)
    audit_log_repo.append(
        db,
        TenantAuditLog(
            tenant_id=tenant_id,
            log_date_time=now,
            log_user=user.role,
            log_action=action,
            log_entity=entity_label,
            details=details,
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )


def list_users(db: Session, tenant_id: uuid.UUID, page_params: PageParams) -> UserListResponse:
    rows, total = users_repo.list_by_tenant(db, tenant_id, offset=page_params.offset, limit=page_params.page_size)
    return UserListResponse(
        items=[_to_response(row) for row in rows],
        page=page_params.page,
        pageSize=page_params.page_size,
        totalCount=total,
    )


def _credential_for(password: str | None) -> str:
    """An admin-supplied password must satisfy the strength rule; an empty one is generated.

    The plain value is returned to the caller for the one-time hand-over only -- it is never
    stored, logged, or written to the audit trail.
    """
    if password is None or not password.strip():
        return generate_password()
    violations = password_violations(password)
    if violations:
        raise ValidationFailedError(PASSWORD_RULE_MESSAGE, details=violations)
    return password


def _upsert_login_user(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    name: str,
    email: str,
    role_label: str,
    password: str,
    actor_uuid: uuid.UUID,
) -> User:
    """Creates (or links, when a `users` row for that tenant+email already exists) the row
    real login authenticates against. Settings > Users and `users` are two tables keyed by
    the same tenant+email pair; `users.role` holds the role *code* that `require_roles` and
    the access token use.
    """
    now = datetime.now(timezone.utc)
    login_user = auth_repo.find_user_in_tenant_by_email(db, tenant_id, email)
    if login_user is None:
        login_user = User(
            tenant_id=tenant_id,
            name=name,
            email=email,
            role=role_code_for(role_label),
            created_by=actor_uuid,
            updated_by=actor_uuid,
            created_at=now,
            updated_at=now,
        )
        auth_repo.insert_user(db, login_user)
    else:
        login_user.name = name
        login_user.role = role_code_for(role_label)
        login_user.updated_by = actor_uuid
        login_user.updated_at = now
    login_user.password_hash = hash_password(password)
    login_user.must_change_password = True
    login_user.is_active = True
    db.flush()
    return login_user


def create_user(db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: CreateUserRequest) -> CreateUserResponse:
    _validate_create(payload)
    password = _credential_for(payload.initialPassword)

    email = payload.email.strip()
    existing = users_repo.find_by_email(db, tenant_id, email)
    if existing is not None:
        raise ConflictError(DUPLICATE_EMAIL_MESSAGE, details=[DUPLICATE_EMAIL_MESSAGE])

    now = datetime.now(timezone.utc)
    actor_uuid = _safe_uuid(user.user_id)
    row = TenantUser(
        tenant_id=tenant_id,
        name=payload.name.strip(),
        email=email,
        role=payload.role,
        status="Invited",
        created_by=actor_uuid,
        updated_by=actor_uuid,
        created_at=now,
        updated_at=now,
    )
    users_repo.insert(db, row)
    _upsert_login_user(
        db,
        tenant_id,
        name=row.name,
        email=row.email,
        role_label=row.role,
        password=password,
        actor_uuid=actor_uuid,
    )
    _log(db, tenant_id, user, action="Created", entity_label="User", details=f"Created user {row.email}")
    db.commit()
    return CreateUserResponse(**_to_response(row).model_dump(), temporaryPassword=password)


def reset_password(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, user_id: uuid.UUID
) -> ResetPasswordResponse:
    """Issues a new temporary password: the user must change it at next login, and every
    session they currently hold is revoked so the old password cannot keep one alive.
    """
    row = users_repo.get_by_id(db, tenant_id, user_id)
    if row is None:
        raise NotFoundError("user not found")

    password = generate_password()
    login_user = _upsert_login_user(
        db,
        tenant_id,
        name=row.name,
        email=row.email,
        role_label=row.role,
        password=password,
        actor_uuid=_safe_uuid(user.user_id),
    )
    auth_repo.revoke_all_for_user(db, login_user.id)
    _log(
        db,
        tenant_id,
        user,
        action="Updated",
        entity_label="User",
        details=f"Password reset for {row.email}",
    )
    db.commit()
    return ResetPasswordResponse(temporaryPassword=password)


def update_user_status(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, user_id: uuid.UUID, payload: UpdateUserStatusRequest
) -> UserListItemResponse:
    if _is_blank(payload.status) or payload.status not in _STATUSES:
        raise ValidationFailedError(STATUS_MESSAGE, details=[STATUS_MESSAGE])

    row = users_repo.get_by_id(db, tenant_id, user_id)
    if row is None:
        raise NotFoundError("user not found")

    new_status = payload.status
    # UC11-AF-005 / UC11-BR-003: moving the last active Tenant Admin out of Active (deactivate
    # or any other transition away from Active) must be blocked, and the blocked attempt is
    # still audited.
    if row.role == "Tenant Admin" and row.status == "Active" and new_status != "Active":
        remaining = users_repo.count_active_tenant_admins(db, tenant_id, exclude_id=row.id)
        if remaining == 0:
            _log(
                db,
                tenant_id,
                user,
                action="Updated",
                entity_label="User",
                details=f"Blocked status change for {row.email}: last active Tenant Admin",
            )
            db.commit()
            raise ConflictError(LAST_ADMIN_MESSAGE, details=[LAST_ADMIN_MESSAGE])

    previous_status = row.status
    row.status = new_status
    row.updated_at = datetime.now(timezone.utc)
    row.updated_by = _safe_uuid(user.user_id)
    # Keep the login row in step: a deactivated user must be refused at authentication
    # (403), and every session they hold revoked, not merely greyed out in the table.
    login_user = auth_repo.find_user_in_tenant_by_email(db, tenant_id, row.email)
    if login_user is not None:
        login_user.is_active = new_status != "Deactivated"
        if new_status == "Deactivated":
            auth_repo.revoke_all_for_user(db, login_user.id)
    _log(
        db,
        tenant_id,
        user,
        action="Updated",
        entity_label="User",
        details=f"User {row.email} status changed from {previous_status} to {new_status}",
    )
    db.commit()
    return _to_response(row)
