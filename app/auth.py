"""Header-auth stub: no identity provider in this environment.

Callers assert a role with X-User-Role and an id with X-User-Id. Missing role header -> 401;
a role outside an endpoint's list -> 403.

FastAPI's APIKeyHeader is used so the two headers appear in the OpenAPI document -- without
that the Swagger UI offers no input for them and every "try it out" call returns 401 while
the API itself is fine.
"""
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User

role_header = APIKeyHeader(name="X-User-Role", scheme_name="UserRoleHeader", auto_error=False)
user_id_header = APIKeyHeader(name="X-User-Id", scheme_name="UserIdHeader", auto_error=False)


@dataclass
class CurrentUser:
    role: str
    user_id: str


def current_user(
    role: str | None = Security(role_header),
    user_id: str | None = Security(user_id_header),
) -> CurrentUser:
    if not role:
        raise HTTPException(status_code=401, detail="missing X-User-Role header")
    return CurrentUser(role=role, user_id=user_id or "")


def require_roles(*allowed: str):
    """Usage: @router.post("/", dependencies=[Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER"))])

    The permitted role names come from THIS module contract's endpoint `roles` lists --
    see CLAUDE.md's "Roles" section. Do not hard-code roles from another project.
    """

    def _check(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if allowed and user.role not in allowed:
            raise HTTPException(
                status_code=403,
                detail=f"role {user.role} is not permitted for this endpoint",
            )
        return user

    return _check


def current_tenant_id(
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> uuid.UUID:
    """Resolves the caller's tenant by looking X-User-Id up in `users`.

    The header-auth stub only asserts a role and a user id -- every tenant-scoped resource
    (clauses, templates, contracts, ...) needs the tenant that user belongs to, so this is
    the one place that join happens rather than every resource re-querying `users` itself.
    An unresolvable or malformed X-User-Id is treated the same as a missing auth header (401):
    without it there is no tenant to scope the request to.
    """
    try:
        user_uuid = uuid.UUID(user.user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="missing or invalid X-User-Id header")
    row = (
        db.query(User)
        .filter(User.id == user_uuid, User.deleted_at.is_(None))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=401, detail="unknown X-User-Id")
    return row.tenant_id
