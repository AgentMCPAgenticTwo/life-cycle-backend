"""`/api/v1/settings/approval-rules` -- thin HTTP binding over
`app.services.settings_approval_rules`. See CLAUDE.md's lifecycle-uc10-uc11 module section
and TASK.md (T-SETTINGS-APPROVAL-RULES-API) for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.pagination import PageParams
from app.schemas.settings_approval_rules import (
    ApprovalRuleListResponse,
    ApprovalRuleResponse,
    CreateApprovalRuleRequest,
    UpdateApprovalRuleRequest,
)
from app.services import settings_approval_rules as approval_rules_service

router = APIRouter(prefix="/settings/approval-rules", tags=["settings-approval-rules"])


@router.get("", response_model=ApprovalRuleListResponse)
def list_approval_rules(
    page_params: PageParams = Depends(),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalRuleListResponse:
    return approval_rules_service.list_rules(db, tenant_id, page_params)


@router.post("", response_model=ApprovalRuleResponse, status_code=201)
def create_approval_rule(
    payload: CreateApprovalRuleRequest,
    response: Response,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalRuleResponse:
    result = approval_rules_service.create_rule(db, tenant_id, user, payload)
    response.headers["Location"] = f"/api/v1/settings/approval-rules/{result.id}"
    return result


@router.put("/{ruleId}", response_model=ApprovalRuleResponse)
def update_approval_rule(
    ruleId: uuid.UUID,
    payload: UpdateApprovalRuleRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ApprovalRuleResponse:
    return approval_rules_service.update_rule(db, tenant_id, user, ruleId, payload)


@router.delete("/{ruleId}", status_code=204)
def delete_approval_rule(
    ruleId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> Response:
    approval_rules_service.delete_rule(db, tenant_id, user, ruleId)
    return Response(status_code=204)
