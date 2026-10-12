"""`/api/v1/approval-matrix-config` -- thin HTTP binding over
`app.services.approval_matrix`. See CLAUDE.md's UC6-UC7-combined module section for the
exact path, roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.approval_matrix import (
    ApprovalMatrixConfigListResponse,
    UpdateApprovalMatrixConfigRequest,
)
from app.services import approval_matrix as approval_matrix_service

router = APIRouter(prefix="/approval-matrix-config", tags=["approval-matrix-config"])


@router.get("", response_model=ApprovalMatrixConfigListResponse)
def get_approval_matrix_config(
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalMatrixConfigListResponse:
    return approval_matrix_service.list_configs(db, tenant_id)


@router.put("", response_model=ApprovalMatrixConfigListResponse)
def update_approval_matrix_config(
    payload: UpdateApprovalMatrixConfigRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalMatrixConfigListResponse:
    return approval_matrix_service.update_configs(db, tenant_id, user, payload)
