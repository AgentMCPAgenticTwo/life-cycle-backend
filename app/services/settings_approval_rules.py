"""Business rules for the `settings/approval-rules` resource: required-field validation
(UC11-AF-003), numeric/non-negative Value Threshold (UC11-FV-002), and the duplicate
Contract Type + Value Threshold guard (UC11-BR-004) -- see CLAUDE.md's lifecycle-uc10-uc11
module section and TASK.md (T-SETTINGS-APPROVAL-RULES-API).
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, ValidationFailedError
from app.models.tracker import ApprovalMatrixRule
from app.repositories import settings_approval_rules as approval_rules_repo
from app.schemas.pagination import PageParams
from app.schemas.settings_approval_rules import (
    ApprovalRuleListResponse,
    ApprovalRuleResponse,
    CreateApprovalRuleRequest,
)

REQUIRED_FIELDS_MESSAGE = "Please complete all required fields"
VALUE_THRESHOLD_MESSAGE = "Value Threshold must be a valid, non-negative number."
DUPLICATE_RULE_MESSAGE = "An approval rule for this Contract Type and Value Threshold already exists."

_CONTRACT_TYPES = {"Product", "Service"}
_APPROVER_ROLES = {"Approver", "Legal Reviewer", "Tenant Admin"}


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _validate(payload: CreateApprovalRuleRequest) -> Decimal:
    # UC11-AF-003: Contract Type, Value Threshold and Approver Role missing all surface the
    # same single message, re-displayed until every required field is provided.
    if _is_blank(payload.contractType) or _is_blank(payload.approverRole) or payload.valueThreshold is None:
        raise ValidationFailedError(REQUIRED_FIELDS_MESSAGE, details=[REQUIRED_FIELDS_MESSAGE])

    if payload.contractType not in _CONTRACT_TYPES:
        message = f"Contract Type must be one of: {', '.join(sorted(_CONTRACT_TYPES))}."
        raise ValidationFailedError(message, details=[message])
    if payload.approverRole not in _APPROVER_ROLES:
        message = f"Approver Role must be one of: {', '.join(sorted(_APPROVER_ROLES))}."
        raise ValidationFailedError(message, details=[message])

    try:
        value_threshold = Decimal(payload.valueThreshold)
    except (InvalidOperation, TypeError):
        raise ValidationFailedError(VALUE_THRESHOLD_MESSAGE, details=[VALUE_THRESHOLD_MESSAGE])
    if value_threshold < 0:
        raise ValidationFailedError(VALUE_THRESHOLD_MESSAGE, details=[VALUE_THRESHOLD_MESSAGE])

    return value_threshold


def _to_response(rule: ApprovalMatrixRule) -> ApprovalRuleResponse:
    return ApprovalRuleResponse(
        id=rule.id,
        contractType=rule.contract_type,
        valueThreshold=rule.value_threshold,
        approverRole=rule.approver_role,
    )


def list_rules(db: Session, tenant_id: uuid.UUID, page_params: PageParams) -> ApprovalRuleListResponse:
    rows, total = approval_rules_repo.list_by_tenant(
        db, tenant_id, offset=page_params.offset, limit=page_params.page_size
    )
    return ApprovalRuleListResponse(
        items=[_to_response(row) for row in rows],
        page=page_params.page,
        pageSize=page_params.page_size,
        totalCount=total,
    )


def create_rule(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: CreateApprovalRuleRequest
) -> ApprovalRuleResponse:
    value_threshold = _validate(payload)

    # UC11-BR-004: duplicate check is on Contract Type + Value Threshold only -- Approver
    # Role is not part of the uniqueness key.
    existing = approval_rules_repo.find_by_type_and_threshold(
        db, tenant_id, payload.contractType, value_threshold
    )
    if existing is not None:
        raise ConflictError(DUPLICATE_RULE_MESSAGE, details=[DUPLICATE_RULE_MESSAGE])

    now = datetime.now(timezone.utc)
    user_uuid = uuid.UUID(user.user_id)
    rule = ApprovalMatrixRule(
        tenant_id=tenant_id,
        contract_type=payload.contractType,
        value_threshold=value_threshold,
        approver_role=payload.approverRole,
        created_by=user_uuid,
        updated_by=user_uuid,
        created_at=now,
        updated_at=now,
    )
    approval_rules_repo.insert(db, rule)
    db.commit()
    return _to_response(rule)
