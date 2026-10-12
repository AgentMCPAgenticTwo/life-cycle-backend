"""Business rules for the `approval-matrix-config` resource: field validation and the
full-replace save semantics behind `PUT /api/v1/approval-matrix-config` -- see CLAUDE.md's
UC6-UC7-combined module section and stories UC6-BR-002, UC6-BR-016.
"""
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ValidationFailedError
from app.models.approval import ApprovalMatrixConfig, ApprovalMatrixStep
from app.models.user import User
from app.repositories import approval_matrix as approval_matrix_repo
from app.schemas.approval_matrix import (
    ApprovalMatrixConfigItemRequest,
    ApprovalMatrixConfigListResponse,
    ApprovalMatrixConfigResponse,
    ApprovalMatrixStepConfig,
    UpdateApprovalMatrixConfigRequest,
)


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _validate_item(db: Session, tenant_id: uuid.UUID, item: ApprovalMatrixConfigItemRequest) -> None:
    if _is_blank(item.contractType):
        raise ValidationFailedError(
            "Contract Type is required.", details=["Contract Type is required."]
        )
    if item.valueMin is not None and item.valueMax is not None and item.valueMin > item.valueMax:
        message = "Contract Value minimum must not exceed the maximum."
        raise ValidationFailedError(message, details=[message])
    if (
        item.riskBandMin is not None
        and item.riskBandMax is not None
        and item.riskBandMin > item.riskBandMax
    ):
        message = "AI Risk Score band minimum must not exceed the maximum."
        raise ValidationFailedError(message, details=[message])
    if not item.steps:
        message = "At least one approval matrix step is required."
        raise ValidationFailedError(message, details=[message])

    seen_step_numbers: set[int] = set()
    for step in item.steps:
        if _is_blank(step.stepName):
            message = "Step Name is required for every approval matrix step."
            raise ValidationFailedError(message, details=[message])
        if step.stepNumber in seen_step_numbers:
            message = f"Step Number {step.stepNumber} is duplicated within {item.contractType}."
            raise ValidationFailedError(message, details=[message])
        seen_step_numbers.add(step.stepNumber)
        if not step.approverRole and step.approverUserId is None:
            message = "Each approval matrix step requires an approver role or a named approver user."
            raise ValidationFailedError(message, details=[message])
        if step.approverUserId is not None:
            approver = (
                db.query(User)
                .filter(
                    User.id == step.approverUserId,
                    User.tenant_id == tenant_id,
                    User.deleted_at.is_(None),
                )
                .first()
            )
            if approver is None:
                message = f"Approver user {step.approverUserId} does not belong to this tenant."
                raise ValidationFailedError(message, details=[message])


def _to_response(config: ApprovalMatrixConfig, steps: list[ApprovalMatrixStep]) -> ApprovalMatrixConfigResponse:
    return ApprovalMatrixConfigResponse(
        id=config.id,
        contractType=config.contract_type,
        valueMin=config.value_min,
        valueMax=config.value_max,
        riskBandMin=config.risk_band_min,
        riskBandMax=config.risk_band_max,
        steps=[
            ApprovalMatrixStepConfig(
                stepNumber=step.step_number,
                approverRole=step.approver_role,
                approverUserId=step.approver_user_id,
                stepName=step.step_name,
            )
            for step in sorted(steps, key=lambda s: s.step_number)
        ],
    )


def list_configs(db: Session, tenant_id: uuid.UUID) -> ApprovalMatrixConfigListResponse:
    configs = approval_matrix_repo.list_by_tenant(db, tenant_id)
    steps_by_config: dict[uuid.UUID, list[ApprovalMatrixStep]] = defaultdict(list)
    for step in approval_matrix_repo.list_steps(db, [c.id for c in configs]):
        steps_by_config[step.config_id].append(step)
    return ApprovalMatrixConfigListResponse(
        items=[_to_response(config, steps_by_config.get(config.id, [])) for config in configs]
    )


def update_configs(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    payload: UpdateApprovalMatrixConfigRequest,
) -> ApprovalMatrixConfigListResponse:
    for item in payload.items:
        _validate_item(db, tenant_id, item)

    now = datetime.now(timezone.utc)
    user_uuid = uuid.UUID(user.user_id)

    # UC6-BR-016: "I configure the approval matrix" is a full save of Settings -- the
    # existing tenant rule set is replaced by what is submitted, not merged field-by-field.
    # Recorded in this task's `blockers`: `context.json` does not spell out merge-vs-replace
    # semantics for this PUT.
    approval_matrix_repo.delete_all(db, tenant_id)

    responses: list[ApprovalMatrixConfigResponse] = []
    for item in payload.items:
        config = ApprovalMatrixConfig(
            tenant_id=tenant_id,
            contract_type=item.contractType,
            value_min=item.valueMin,
            value_max=item.valueMax,
            risk_band_min=item.riskBandMin,
            risk_band_max=item.riskBandMax,
            created_by=user_uuid,
            updated_by=user_uuid,
            created_at=now,
            updated_at=now,
        )
        approval_matrix_repo.insert_config(db, config)

        steps: list[ApprovalMatrixStep] = []
        for step in item.steps:
            model_step = ApprovalMatrixStep(
                config_id=config.id,
                step_number=step.stepNumber,
                step_name=step.stepName,
                approver_role=step.approverRole,
                approver_user_id=step.approverUserId,
                created_by=user_uuid,
                updated_by=user_uuid,
                created_at=now,
                updated_at=now,
            )
            approval_matrix_repo.insert_step(db, model_step)
            steps.append(model_step)

        responses.append(_to_response(config, steps))

    db.commit()
    return ApprovalMatrixConfigListResponse(items=responses)
