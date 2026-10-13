"""Business rules for the `settings/audit-log` resource: read-only, newest-first, scoped to
the caller's tenant, filterable by date range/user/action type (UC11-FV-005, UC11-GC-003,
UC11-BR-005, UC11-BR-011) -- see CLAUDE.md's lifecycle-uc10-uc11 module section and
TASK.md (T-SETTINGS-AUDIT-LOG-API). This module exposes no write path for the log itself --
other resources' services append entries as a side effect of their own writes.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.tracker import TenantAuditLog
from app.repositories import settings_audit_log as audit_log_repo
from app.schemas.settings_audit_log import AuditLogEntryResponse, AuditLogListResponse, AuditLogQueryParams


def _to_response(entry: TenantAuditLog) -> AuditLogEntryResponse:
    return AuditLogEntryResponse(
        id=entry.id,
        logDateTime=entry.log_date_time,
        logUser=entry.log_user,
        logAction=entry.log_action,
        logEntity=entry.log_entity,
        details=entry.details,
    )


def list_entries(
    db: Session, tenant_id: uuid.UUID, query_params: AuditLogQueryParams
) -> AuditLogListResponse:
    rows, total = audit_log_repo.list_by_tenant(
        db,
        tenant_id,
        date_from=query_params.filter_date_range_from,
        date_to=query_params.filter_date_range_to,
        user_filter=query_params.user_filter,
        action_type_filter=query_params.action_type_filter,
        offset=query_params.offset,
        limit=query_params.page_size,
    )
    return AuditLogListResponse(
        items=[_to_response(row) for row in rows],
        page=query_params.page,
        pageSize=query_params.page_size,
        totalCount=total,
    )
