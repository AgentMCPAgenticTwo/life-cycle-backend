"""`/api/v1/settings/audit-log` -- thin HTTP binding over
`app.services.settings_audit_log`. See CLAUDE.md's lifecycle-uc10-uc11 module section
and TASK.md (T-SETTINGS-AUDIT-LOG-API) for the exact path, roles and DTOs.

Read-only by design (UC11-BR-005/BR-011). The edit/delete routes below exist only to say
so explicitly: without them FastAPI answers a PUT/PATCH/DELETE with a bare 405 carrying no
message, and the UI has a specific one to show. The same rule is enforced again at the
persistence layer (`app.models.immutable.enforce_append_only` on `TenantAuditLog`).
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.errors import ImmutableResourceError
from app.models.immutable import AUDIT_LOG_IMMUTABLE_MESSAGE
from app.schemas.settings_audit_log import AuditLogListResponse, AuditLogQueryParams
from app.services import settings_audit_log as audit_log_service

router = APIRouter(prefix="/settings/audit-log", tags=["settings-audit-log"])


@router.get("", response_model=AuditLogListResponse)
def list_audit_log(
    query_params: AuditLogQueryParams = Depends(),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> AuditLogListResponse:
    return audit_log_service.list_entries(db, tenant_id, query_params)


def _reject_mutation() -> None:
    raise ImmutableResourceError(
        AUDIT_LOG_IMMUTABLE_MESSAGE, details=[AUDIT_LOG_IMMUTABLE_MESSAGE]
    )


@router.put("/{entryId}")
@router.patch("/{entryId}")
def update_audit_log_entry(
    entryId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
) -> None:
    _reject_mutation()


@router.delete("/{entryId}")
def delete_audit_log_entry(
    entryId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
) -> None:
    _reject_mutation()
