"""Data access for authentication: `users` credential lookups and the `refresh_tokens`
table. Owns queries only -- the rules (which failure is a 401 and which a 403, rotation,
revocation on password change) live in `app.services.auth`.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.refresh_token import RefreshToken
from app.models.tracker import TenantUser
from app.models.user import User


def find_user_by_email(db: Session, email: str) -> User | None:
    return (
        db.query(User)
        .filter(User.email == email, User.deleted_at.is_(None))
        .order_by(User.created_at.asc())
        .first()
    )


def find_user_by_id(db: Session, user_id: uuid.UUID) -> User | None:
    return db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()


def find_user_in_tenant_by_email(db: Session, tenant_id: uuid.UUID, email: str) -> User | None:
    return (
        db.query(User)
        .filter(
            User.tenant_id == tenant_id,
            User.email == email,
            User.deleted_at.is_(None),
        )
        .first()
    )


def find_tenant_user_by_email(db: Session, tenant_id: uuid.UUID, email: str) -> TenantUser | None:
    return (
        db.query(TenantUser)
        .filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.email == email,
            TenantUser.deleted_at.is_(None),
        )
        .first()
    )


def insert_user(db: Session, user: User) -> User:
    db.add(user)
    db.flush()
    return user


def insert_refresh_token(db: Session, token: RefreshToken) -> RefreshToken:
    db.add(token)
    db.flush()
    return token


def find_live_refresh_token(db: Session, token_hash: str) -> RefreshToken | None:
    return (
        db.query(RefreshToken)
        .filter(
            RefreshToken.token_hash == token_hash,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
        .first()
    )


def revoke_token(db: Session, token: RefreshToken) -> None:
    token.revoked_at = datetime.now(timezone.utc)
    db.flush()


def revoke_all_for_user(
    db: Session, user_id: uuid.UUID, *, except_id: uuid.UUID | None = None
) -> int:
    query = db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    )
    if except_id is not None:
        query = query.filter(RefreshToken.id != except_id)
    now = datetime.now(timezone.utc)
    rows = query.all()
    for row in rows:
        row.revoked_at = now
    db.flush()
    return len(rows)
