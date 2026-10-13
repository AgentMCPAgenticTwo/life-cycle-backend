"""Real authentication: `Authorization: Bearer <JWT>`.

This replaced the former X-User-Role/X-User-Id header stub. Only `current_user()` changed --
`require_roles` and `current_tenant_id` keep their shape and signature, so no router needed
touching. The access token is issued by `/api/v1/auth/login` (see `app/routers/auth.py`);
the role is read from the database row rather than from the token's claims, so deactivating
or re-roling a user takes effect on their next request instead of on their next login.

The bearer scheme is declared to FastAPI's security layer so it appears in the OpenAPI
document -- without that the docs UI offers no "Authorize" input and every "try it out" call
comes back 401 while the API itself is fine.
"""
import uuid
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.user import User
from app.security import decode_access_token

bearer_scheme = HTTPBearer(scheme_name="BearerAuth", auto_error=False)


@dataclass
class CurrentUser:
    role: str
    user_id: str
    tenant_id: uuid.UUID | None = None
    name: str = ""
    email: str = ""
    must_change_password: bool = False


def current_user(
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(status_code=401, detail="missing Authorization header")
    claims = decode_access_token(credentials.credentials)
    if claims is None or not claims.get("sub"):
        raise HTTPException(status_code=401, detail="invalid or expired access token")
    try:
        user_uuid = uuid.UUID(str(claims["sub"]))
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="invalid or expired access token")
    row = db.query(User).filter(User.id == user_uuid, User.deleted_at.is_(None)).first()
    if row is None:
        raise HTTPException(status_code=401, detail="invalid or expired access token")
    if not row.is_active:
        raise HTTPException(status_code=403, detail="user account is deactivated")
    return CurrentUser(
        role=row.role,
        user_id=str(row.id),
        tenant_id=row.tenant_id,
        name=row.name,
        email=row.email,
        must_change_password=bool(row.must_change_password),
    )


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
    """Resolves the caller's tenant by looking the authenticated user up in `users`.

    Every tenant-scoped resource (clauses, templates, contracts, ...) needs the tenant that
    user belongs to, so this is the one place that join happens rather than every resource
    re-querying `users` itself. An unresolvable user id is treated the same as a missing auth
    header (401): without it there is no tenant to scope the request to.
    """
    try:
        user_uuid = uuid.UUID(user.user_id)
    except (ValueError, AttributeError):
        raise HTTPException(status_code=401, detail="invalid or expired access token")
    row = (
        db.query(User)
        .filter(User.id == user_uuid, User.deleted_at.is_(None))
        .first()
    )
    if row is None:
        raise HTTPException(status_code=401, detail="invalid or expired access token")
    return row.tenant_id
