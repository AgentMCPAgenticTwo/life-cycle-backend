"""`/api/v1/settings/audit-log` -- thin HTTP binding over
`app.services.settings_audit_log`. See CLAUDE.md's lifecycle-uc10-uc11 module section
and TASK.md (T-SETTINGS-AUDIT-LOG-API) for the exact path, roles and DTOs.

Read-only by design (UC11-BR-005/BR-011): no PUT/PATCH/DELETE route exists for this
resource, so an edit/delete attempt against it is a 404/405 from FastAPI's routing itself
rather than a handled business rule.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
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
