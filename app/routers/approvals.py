"""`/api/v1/approvals` -- thin HTTP binding over `app.services.approvals`. See CLAUDE.md's
UC6-UC7-combined module section for the exact paths, roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalActionResponse,
    ApprovalHistoryListResponse,
    ApprovalListResponse,
    ApprovalResponse,
    DelegateRequest,
    DelegateResponse,
)
from app.schemas.pagination import PageParams
from app.services import approvals as approvals_service

router = APIRouter(prefix="/approvals", tags=["approvals"])

_VIEW_ROLES = ("APPROVER", "TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER")


@router.get("", response_model=ApprovalListResponse)
def list_approvals(
    page_params: PageParams = Depends(),
    user: CurrentUser = Depends(require_roles(*_VIEW_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalListResponse:
    return approvals_service.list_approvals(db, tenant_id, user, page_params)


@router.get("/{approvalId}", response_model=ApprovalResponse)
def get_approval(
    approvalId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_VIEW_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalResponse:
    return approvals_service.get_approval_detail(db, tenant_id, user, approvalId)


@router.post("/{approvalId}/actions", response_model=ApprovalActionResponse)
def submit_action(
    approvalId: uuid.UUID,
    payload: ApprovalActionRequest,
    user: CurrentUser = Depends(require_roles("APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalActionResponse:
    return approvals_service.submit_action(db, tenant_id, user, approvalId, payload)


@router.post("/{approvalId}/delegate", response_model=DelegateResponse)
def submit_delegation(
    approvalId: uuid.UUID,
    payload: DelegateRequest,
    user: CurrentUser = Depends(require_roles("APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> DelegateResponse:
    return approvals_service.submit_delegation(db, tenant_id, user, approvalId, payload)


@router.get("/{approvalId}/history", response_model=ApprovalHistoryListResponse)
def get_history(
    approvalId: uuid.UUID,
    page_params: PageParams = Depends(),
    user: CurrentUser = Depends(require_roles(*_VIEW_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalHistoryListResponse:
    return approvals_service.get_history(db, tenant_id, user, approvalId, page_params)
