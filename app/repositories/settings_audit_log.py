"""Data access for `tenant_audit_log`. Owns queries only -- the log is append-only and this
module never exposes an HTTP update/delete path for it (UC11-BR-005/BR-011: this resource's
GET is the only route, read-only end to end). `append` exists so other resources' services
(e.g. settings_integrations) can record entries as a side effect of their own writes without
constructing `TenantAuditLog` rows themselves.
"""
import uuid
from datetime import date, datetime, time, timezone

from sqlalchemy.orm import Session

from app.models.tracker import TenantAuditLog


def append(db: Session, entry: TenantAuditLog) -> TenantAuditLog:
    db.add(entry)
    db.flush()
    return entry


def list_by_tenant(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    date_from: date | None,
    date_to: date | None,
    user_filter: str | None,
    action_type_filter: str | None,
    offset: int,
    limit: int,
) -> tuple[list[TenantAuditLog], int]:
    query = db.query(TenantAuditLog).filter(TenantAuditLog.tenant_id == tenant_id)

    if date_from is not None:
        query = query.filter(
            TenantAuditLog.log_date_time >= datetime.combine(date_from, time.min, tzinfo=timezone.utc)
        )
    if date_to is not None:
        query = query.filter(
            TenantAuditLog.log_date_time <= datetime.combine(date_to, time.max, tzinfo=timezone.utc)
        )
    if user_filter:
        query = query.filter(TenantAuditLog.log_user == user_filter)
    if action_type_filter:
        query = query.filter(TenantAuditLog.log_action == action_type_filter)

    total = query.count()
    rows = (
        query.order_by(TenantAuditLog.log_date_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return rows, total
