"""Data access for `tenant_users`. Owns queries only -- the business rules (required-field
validation, duplicate-email guard, last-active-Tenant-Admin guard) live in
`app.services.settings_users`.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.tracker import TenantUser


def list_by_tenant(
    db: Session, tenant_id: uuid.UUID, *, offset: int, limit: int
) -> tuple[list[TenantUser], int]:
    query = (
        db.query(TenantUser)
        .filter(TenantUser.tenant_id == tenant_id, TenantUser.deleted_at.is_(None))
        .order_by(TenantUser.name.asc())
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return rows, total


def find_by_email(db: Session, tenant_id: uuid.UUID, email: str) -> TenantUser | None:
    return (
        db.query(TenantUser)
        .filter(
            TenantUser.tenant_id == tenant_id,
            TenantUser.email == email,
            TenantUser.deleted_at.is_(None),
        )
        .first()
    )


def get_by_id(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> TenantUser | None:
    return (
        db.query(TenantUser)
        .filter(
            TenantUser.id == user_id,
            TenantUser.tenant_id == tenant_id,
            TenantUser.deleted_at.is_(None),
        )
        .first()
    )


def count_active_tenant_admins(db: Session, tenant_id: uuid.UUID, *, exclude_id: uuid.UUID | None = None) -> int:
    query = db.query(TenantUser).filter(
        TenantUser.tenant_id == tenant_id,
        TenantUser.deleted_at.is_(None),
        TenantUser.role == "Tenant Admin",
        TenantUser.status == "Active",
    )
    if exclude_id is not None:
        query = query.filter(TenantUser.id != exclude_id)
    return query.count()


def insert(db: Session, user: TenantUser) -> TenantUser:
    db.add(user)
    db.flush()
    return user
