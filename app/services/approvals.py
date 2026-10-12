"""Business rules for the `approvals` resource: visibility/listing, the full approval review
screen with action-eligibility flags, the Approve/Reject/Send Back transition, time-bound
delegation, and the immutable Approval History tab -- see CLAUDE.md's UC6-UC7-combined module
section and this task's stories (T-APPROVALS-API/TASK.md).

This task owns `approvals`, `approval_step_instances`, `approval_delegations` and
`approval_audit_log`. It has no endpoint to *create* an `Approval` (none is listed in this
task's `context.json`); that is the responsibility of whatever upstream workflow routes a
contract out of Negotiation (UC5) into the approval matrix. This service therefore assumes an
`Approval` row (and, ideally, its current-step `ApprovalStepInstance`) already exists, and
lazily resolves/creates the current step's instance from `approval_matrix_steps` the first
time it is needed if upstream has not already done so -- see `_get_or_create_step_instance`.
Recorded in this task's `blockers`.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from app.models.approval import (
    Approval,
    ApprovalAuditLog,
    ApprovalDelegation,
    ApprovalMatrixStep,
    ApprovalStepInstance,
)
from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.user import User
from app.repositories import approvals as approvals_repo
from app.schemas.approval import (
    ApprovalActionRequest,
    ApprovalActionResponse,
    ApprovalHistoryEntryResponse,
    ApprovalHistoryListResponse,
    ApprovalListItemResponse,
    ApprovalListResponse,
    ApprovalResponse,
    DelegateRequest,
    DelegateResponse,
)
from app.schemas.pagination import PageParams

_EMPTY_MESSAGE = "No contracts are currently awaiting your approval."

# This module's `ApprovalActionResponse.contractStatus` enum (`InNegotiation`,
# `PendingApproval`, `Approved`, `Rejected`, `ReadyForSignature`) does not match the uc123
# module's shared `contracts.status` values (`In Negotiation`, `Pending Approval`, ...,
# space-separated -- see `app/schemas/contract.py`'s `ContractStatus` Literal, which the
# `/api/v1/contracts/{id}` response validates against). Rather than writing a value into the
# shared column that would break that other module's response serialization, this module
# persists the existing space-separated convention (extended additively with "Rejected" and
# "Ready For Signature") and maps to this module's own wire format only in its own responses.
# Recorded in this task's `blockers`.
_CONTRACT_STATUS_TO_WIRE = {
    "Draft": "Draft",
    "In Negotiation": "InNegotiation",
    "Pending Approval": "PendingApproval",
    "Pending Signature": "PendingSignature",
    "Executed": "Executed",
    "Rejected": "Rejected",
    "Ready For Signature": "ReadyForSignature",
}


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _resolve_user(db: Session, user_id: uuid.UUID | None) -> User | None:
    if user_id is None:
        return None
    return db.query(User).filter(User.id == user_id).first()


def _resolve_user_name(db: Session, user_id: uuid.UUID | None) -> str:
    row = _resolve_user(db, user_id)
    return row.name if row is not None else "Unknown"


def _resolve_counterparty_name(db: Session, counterparty_id: uuid.UUID) -> str:
    row = db.query(Counterparty).filter(Counterparty.id == counterparty_id).first()
    return row.name if row is not None else "Unknown"


def _step_name(db: Session, config_id: uuid.UUID | None, step_number: int) -> str:
    if config_id is not None:
        step = (
            db.query(ApprovalMatrixStep)
            .filter(ApprovalMatrixStep.config_id == config_id, ApprovalMatrixStep.step_number == step_number)
            .first()
        )
        if step is not None:
            return step.step_name
    return f"Step {step_number}"


def _step_label(db: Session, approval: Approval, step_number: int) -> str:
    name = _step_name(db, approval.config_id, step_number)
    return f"Step {step_number} of {approval.total_steps} – {name}"


def _resolve_approver_for_step(
    db: Session, tenant_id: uuid.UUID, contract: Contract, config_id: uuid.UUID | None, step_number: int
) -> uuid.UUID:
    if config_id is not None:
        matrix_step = (
            db.query(ApprovalMatrixStep)
            .filter(ApprovalMatrixStep.config_id == config_id, ApprovalMatrixStep.step_number == step_number)
            .first()
        )
        if matrix_step is not None:
            if matrix_step.approver_user_id is not None:
                return matrix_step.approver_user_id
            if matrix_step.approver_role:
                # UC6-BR-011: the Contract Owner is never eligible, even if named in the matrix.
                candidate = (
                    db.query(User)
                    .filter(
                        User.tenant_id == tenant_id,
                        User.role == matrix_step.approver_role,
                        User.deleted_at.is_(None),
                        User.id != contract.contract_owner_id,
                    )
                    .order_by(User.id.asc())
                    .first()
                )
                if candidate is not None:
                    return candidate.id
    # No resolvable matrix step/role -- fall back to the contract owner rather than leaving
    # the non-nullable approver column unset. A misconfigured tenant matrix is a data
    # problem, not something this read endpoint can 400 on. Recorded in this task's
    # `blockers`: a contract whose matrix cannot resolve any eligible approver other than its
    # owner has no one who can legally act on it (UC6-BR-011 still excludes the owner), and
    # a true fix requires a Tenant Admin to correct the approval matrix configuration.
    return contract.contract_owner_id


def _get_or_create_step_instance(
    db: Session, tenant_id: uuid.UUID, approval: Approval, contract: Contract, step_number: int
) -> ApprovalStepInstance:
    instance = approvals_repo.get_current_step_instance(db, approval.id, step_number)
    if instance is not None:
        return instance
    approver_id = _resolve_approver_for_step(db, tenant_id, contract, approval.config_id, step_number)
    now = datetime.now(timezone.utc)
    instance = ApprovalStepInstance(
        approval_id=approval.id,
        step_number=step_number,
        approver_user_id=approver_id,
        status="Pending",
        created_by=approver_id,
        updated_by=approver_id,
        created_at=now,
        updated_at=now,
    )
    db.add(instance)
    db.flush()
    return instance


def _active_delegation_for(
    db: Session, approval_id: uuid.UUID, approver_user_id: uuid.UUID, candidate_user_id: uuid.UUID
) -> ApprovalDelegation | None:
    return approvals_repo.get_active_delegation(
        db, approval_id, approver_user_id, candidate_user_id, date.today()
    )


def _retention_expiry(now: datetime) -> datetime:
    try:
        return now.replace(year=now.year + 7)
    except ValueError:
        # Feb 29 on a non-leap target year.
        return now.replace(month=2, day=28, year=now.year + 7)


def _write_audit_log(
    db: Session,
    *,
    approval: Approval,
    contract: Contract,
    step_label: str,
    action: str,
    actor_id: uuid.UUID,
    actor_role: str,
    acting_as_delegate_for: uuid.UUID | None,
    delegate_to_user_id: uuid.UUID | None,
    delegate_to_name: str | None,
    prior_state: str,
    new_state: str,
    comments: str | None,
) -> None:
    now = datetime.now(timezone.utc)
    entry = ApprovalAuditLog(
        approval_id=approval.id,
        contract_title=contract.contract_name,
        contract_type=contract.contract_type,
        contract_value=contract.contract_value,
        counterparty_name=_resolve_counterparty_name(db, contract.counterparty_id),
        key_terms_summary=approval.key_terms_summary,
        deviations_from_standard=approval.deviations_from_standard,
        ai_risk_score=approval.ai_risk_score,
        approval_matrix_step_label=step_label,
        action=action,
        actor_id=actor_id,
        actor_role=actor_role,
        acting_as_delegate_for=acting_as_delegate_for,
        delegate_to_user_id=delegate_to_user_id,
        delegate_to_name=delegate_to_name,
        prior_state=prior_state,
        new_state=new_state,
        comments=comments,
        retention_expires_at=_retention_expiry(now),
        archived=False,
        timestamp=now,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    approvals_repo.insert_audit_log(db, entry)


def _to_list_item(db: Session, approval: Approval, contract: Contract) -> ApprovalListItemResponse:
    return ApprovalListItemResponse(
        id=approval.id,
        contractId=contract.id,
        contractTitle=contract.contract_name,
        contractType=contract.contract_type,
        contractValue=contract.contract_value,
        counterpartyName=_resolve_counterparty_name(db, contract.counterparty_id),
        keyTermsSummary=approval.key_terms_summary,
        deviationsFromStandard=approval.deviations_from_standard,
        aiRiskScore=approval.ai_risk_score if approval.ai_risk_score is not None else contract.risk_score,
        approvalMatrixStepLabel=_step_label(db, approval, approval.current_step_number),
        status=approval.status,
    )


def list_approvals(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, page_params: PageParams
) -> ApprovalListResponse:
    contract_owner_id: uuid.UUID | None = None
    current_approver_ids: list[uuid.UUID] | None = None

    if user.role == "CONTRACT_OWNER":
        contract_owner_id = uuid.UUID(user.user_id)
    elif user.role == "APPROVER":
        actor_id = uuid.UUID(user.user_id)
        delegated_for = [
            d.approver_user_id for d in approvals_repo.list_active_delegations_for_user(db, actor_id, date.today())
        ]
        current_approver_ids = [actor_id, *delegated_for]
    # TENANT_ADMIN / LEGAL_REVIEWER: tenant-wide visibility, no extra filter.

    rows, total = approvals_repo.list_for_tenant(
        db,
        tenant_id,
        contract_owner_id=contract_owner_id,
        current_approver_ids=current_approver_ids,
        offset=page_params.offset,
        limit=page_params.page_size,
    )
    items = [_to_list_item(db, approval, contract) for approval, contract in rows]
    is_empty = total == 0
    return ApprovalListResponse(
        items=items,
        page=page_params.page,
        pageSize=page_params.page_size,
        totalCount=total,
        isEmpty=is_empty,
        emptyMessage=_EMPTY_MESSAGE if is_empty else None,
    )


def _load_approval_or_404(
    db: Session, tenant_id: uuid.UUID, approval_id: uuid.UUID
) -> tuple[Approval, Contract]:
    row = approvals_repo.get_approval_with_contract(db, tenant_id, approval_id)
    if row is None:
        raise NotFoundError("approval not found")
    return row


def get_approval_detail(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, approval_id: uuid.UUID
) -> ApprovalResponse:
    approval, contract = _load_approval_or_404(db, tenant_id, approval_id)

    # UC6-BR-017: a Contract Owner may only view their own contracts' approval status.
    if user.role == "CONTRACT_OWNER" and str(contract.contract_owner_id) != user.user_id:
        raise ForbiddenError("You do not have access to this contract")

    step = _get_or_create_step_instance(db, tenant_id, approval, contract, approval.current_step_number)

    actor_id = uuid.UUID(user.user_id) if user.user_id else None
    is_current_approver = user.role == "APPROVER" and actor_id == step.approver_user_id
    is_active_delegate = False
    if user.role == "APPROVER" and actor_id is not None and not is_current_approver:
        is_active_delegate = _active_delegation_for(db, approval.id, step.approver_user_id, actor_id) is not None

    is_contract_owner_actor = actor_id == contract.contract_owner_id
    is_pending = approval.status == "PendingApproval"
    is_eligible_actor = (
        user.role == "APPROVER"
        and (is_current_approver or is_active_delegate)
        and not is_contract_owner_actor
    )
    is_step_actionable = is_pending and is_eligible_actor
    can_delegate = is_pending and is_current_approver and not is_contract_owner_actor

    delegation = None
    if is_active_delegate:
        delegation = _active_delegation_for(db, approval.id, step.approver_user_id, actor_id)
    else:
        delegation = (
            db.query(ApprovalDelegation)
            .filter(ApprovalDelegation.approval_id == approval.id, ApprovalDelegation.approver_user_id == step.approver_user_id)
            .order_by(ApprovalDelegation.created_at.desc())
            .first()
        )

    return ApprovalResponse(
        id=approval.id,
        contractId=contract.id,
        contractTitle=contract.contract_name,
        contractType=contract.contract_type,
        contractValue=contract.contract_value,
        counterpartyName=_resolve_counterparty_name(db, contract.counterparty_id),
        keyTermsSummary=approval.key_terms_summary,
        deviationsFromStandard=approval.deviations_from_standard,
        aiRiskScore=approval.ai_risk_score if approval.ai_risk_score is not None else contract.risk_score,
        approvalMatrixStepLabel=_step_label(db, approval, approval.current_step_number),
        approvalMatrixStepNumber=approval.current_step_number,
        approvalMatrixTotalSteps=approval.total_steps,
        status=approval.status,
        comments=step.comments,
        delegateToUserId=delegation.delegate_to_user_id if delegation else None,
        delegateToName=_resolve_user_name(db, delegation.delegate_to_user_id) if delegation else None,
        delegationStartDate=delegation.start_date if delegation else None,
        delegationEndDate=delegation.end_date if delegation else None,
        currentApproverId=step.approver_user_id,
        currentApproverName=_resolve_user_name(db, step.approver_user_id),
        isCurrentUserApprover=is_current_approver,
        isCurrentUserActiveDelegate=is_active_delegate,
        isStepActionable=is_step_actionable,
        canApprove=is_step_actionable,
        canReject=is_step_actionable,
        canSendBack=is_step_actionable,
        canDelegate=can_delegate,
        createdAt=approval.created_at,
        updatedAt=approval.updated_at,
    )


_ACTION_TYPES = {"Approve", "Reject", "SendBack"}


def submit_action(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    approval_id: uuid.UUID,
    payload: ApprovalActionRequest,
) -> ApprovalActionResponse:
    if payload.actionType not in _ACTION_TYPES:
        raise ValidationFailedError(
            "actionType must be one of Approve, Reject, SendBack.",
            details=["actionType must be one of Approve, Reject, SendBack."],
        )

    approval, contract = _load_approval_or_404(db, tenant_id, approval_id)
    actor_id = uuid.UUID(user.user_id)

    # UC6-AF-004 / UC6-BR-006 / UC6-BR-021: a non-PendingApproval approval is either already
    # resolved by a concurrent session or terminally closed -- either way, no further action.
    if approval.status != "PendingApproval":
        raise ConflictError(
            "This contract's approval status has changed. Please refresh to see the latest status."
        )

    step = _get_or_create_step_instance(db, tenant_id, approval, contract, approval.current_step_number)

    # UC6-BR-011: the Contract Owner can never act on their own contract's approval, even if
    # somehow named as its approver.
    if actor_id == contract.contract_owner_id:
        raise ForbiddenError("The Contract Owner cannot approve their own contract.")

    is_current_approver = actor_id == step.approver_user_id
    acting_as_delegate_for: uuid.UUID | None = None
    if not is_current_approver:
        delegation = _active_delegation_for(db, approval.id, step.approver_user_id, actor_id)
        if delegation is None:
            # UC6-AF-001 / UC6-BR-007: not the assigned approver and not an active delegate --
            # either genuinely unauthorized or a step that hasn't been reached yet.
            raise ForbiddenError(
                "This step is not yet available for approval. Waiting on an earlier approver."
            )
        acting_as_delegate_for = step.approver_user_id

    if payload.actionType in ("Reject", "SendBack") and _is_blank(payload.comments):
        raise ValidationFailedError(
            "Comments are required when rejecting or sending back a contract.",
            details=["Comments are required when rejecting or sending back a contract."],
        )

    prior_state = approval.status
    step_label_before = _step_label(db, approval, approval.current_step_number)
    now = datetime.now(timezone.utc)

    step.comments = payload.comments
    step.acted_by = actor_id
    step.acted_as_delegate_for = acting_as_delegate_for
    step.acted_at = now
    step.updated_by = actor_id
    step.updated_at = now

    if payload.actionType == "Reject":
        step.status = "Rejected"
        approval.status = "Rejected"
        contract.status = "Rejected"
    elif payload.actionType == "SendBack":
        step.status = "SentBack"
        # Flush the step's own Approve/Reject/SendBack attribution (comments, acted_by, ...)
        # before the bulk delete below, or SQLAlchemy's unit-of-work sees a later UPDATE
        # against a row the bulk DELETE already removed and raises StaleDataError.
        db.flush()
        # UC6-BR-005: sending back clears prior approval progress and resets the sequence.
        approval.current_step_number = 1
        approval.status = "PendingApproval"
        contract.status = "In Negotiation"
        db.query(ApprovalStepInstance).filter(ApprovalStepInstance.approval_id == approval.id).delete(
            synchronize_session=False
        )
        db.flush()
        _get_or_create_step_instance(db, tenant_id, approval, contract, 1)
    else:  # Approve
        step.status = "Approved"
        if approval.current_step_number < approval.total_steps:
            # UC6-BR-023: automatically advance to the next sequential step.
            approval.current_step_number += 1
            approval.status = "PendingApproval"
            _get_or_create_step_instance(db, tenant_id, approval, contract, approval.current_step_number)
        else:
            # UC6-BR-024: the final step was approved -- auto-transition to e-signature.
            approval.status = "ReadyForSignature"
            contract.status = "Ready For Signature"

    approval.updated_by = actor_id
    approval.updated_at = now
    contract.updated_by = actor_id
    contract.updated_at = now

    _write_audit_log(
        db,
        approval=approval,
        contract=contract,
        step_label=step_label_before,
        action=payload.actionType,
        actor_id=actor_id,
        actor_role=user.role,
        acting_as_delegate_for=acting_as_delegate_for,
        delegate_to_user_id=None,
        delegate_to_name=None,
        prior_state=prior_state,
        new_state=approval.status,
        comments=payload.comments,
    )

    db.commit()

    return ApprovalActionResponse(
        approvalId=approval.id,
        status=approval.status,
        approvalMatrixStepLabel=_step_label(db, approval, approval.current_step_number),
        approvalMatrixStepNumber=approval.current_step_number,
        contractStatus=_CONTRACT_STATUS_TO_WIRE.get(contract.status, contract.status),
    )


def submit_delegation(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    approval_id: uuid.UUID,
    payload: DelegateRequest,
) -> DelegateResponse:
    approval, contract = _load_approval_or_404(db, tenant_id, approval_id)
    actor_id = uuid.UUID(user.user_id)

    if approval.status != "PendingApproval":
        raise ConflictError(
            "This contract's approval status has changed. Please refresh to see the latest status."
        )

    step = _get_or_create_step_instance(db, tenant_id, approval, contract, approval.current_step_number)

    if actor_id == contract.contract_owner_id:
        raise ForbiddenError("The Contract Owner cannot approve their own contract.")

    # UC6-BR-015: only the assigned Approver may delegate -- a Delegate cannot delegate further.
    if actor_id != step.approver_user_id:
        raise ForbiddenError(
            "This step is not yet available for approval. Waiting on an earlier approver."
        )

    if payload.startDate > payload.endDate:
        raise ValidationFailedError(
            "Delegation start date must not be after the end date.",
            details=["Delegation start date must not be after the end date."],
        )

    # UC6-BR-005 / UC6-BR-011: the delegate must hold the Approver role in this tenant and
    # must not be the Contract Owner.
    if payload.delegateToUserId == contract.contract_owner_id:
        raise ValidationFailedError(
            "Selected user is not an eligible Approver and cannot be set as delegate.",
            details=["Selected user is not an eligible Approver and cannot be set as delegate."],
        )
    candidate = (
        db.query(User)
        .filter(
            User.id == payload.delegateToUserId,
            User.tenant_id == tenant_id,
            User.role == "APPROVER",
            User.deleted_at.is_(None),
        )
        .first()
    )
    if candidate is None:
        raise ValidationFailedError(
            "Selected user is not an eligible Approver and cannot be set as delegate.",
            details=["Selected user is not an eligible Approver and cannot be set as delegate."],
        )

    now = datetime.now(timezone.utc)
    delegation = ApprovalDelegation(
        approval_id=approval.id,
        approver_user_id=step.approver_user_id,
        delegate_to_user_id=payload.delegateToUserId,
        start_date=payload.startDate,
        end_date=payload.endDate,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    approvals_repo.insert_delegation(db, delegation)

    _write_audit_log(
        db,
        approval=approval,
        contract=contract,
        step_label=_step_label(db, approval, approval.current_step_number),
        action="Delegate",
        actor_id=actor_id,
        actor_role=user.role,
        acting_as_delegate_for=None,
        delegate_to_user_id=payload.delegateToUserId,
        delegate_to_name=candidate.name,
        prior_state=approval.status,
        new_state=approval.status,
        comments=None,
    )

    db.commit()

    return DelegateResponse(
        id=delegation.id,
        approvalId=approval.id,
        delegateToUserId=delegation.delegate_to_user_id,
        delegateToName=candidate.name,
        startDate=delegation.start_date,
        endDate=delegation.end_date,
        createdBy=delegation.created_by,
        createdAt=delegation.created_at,
    )


def get_history(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, approval_id: uuid.UUID, page_params: PageParams
) -> ApprovalHistoryListResponse:
    approval, contract = _load_approval_or_404(db, tenant_id, approval_id)
    if user.role == "CONTRACT_OWNER" and str(contract.contract_owner_id) != user.user_id:
        raise ForbiddenError("You do not have access to this contract")

    rows, total = approvals_repo.list_history(
        db, approval.id, offset=page_params.offset, limit=page_params.page_size
    )
    items = [
        ApprovalHistoryEntryResponse(
            id=row.id,
            approvalId=row.approval_id,
            contractTitle=row.contract_title,
            contractType=row.contract_type,
            contractValue=row.contract_value,
            counterpartyName=row.counterparty_name,
            keyTermsSummary=row.key_terms_summary,
            deviationsFromStandard=row.deviations_from_standard,
            aiRiskScore=row.ai_risk_score,
            approvalMatrixStepLabel=row.approval_matrix_step_label,
            action=row.action,
            actorId=row.actor_id,
            actorName=_resolve_user_name(db, row.actor_id),
            actorRole=row.actor_role,
            actingAsDelegateForUserId=row.acting_as_delegate_for,
            delegateToUserId=row.delegate_to_user_id,
            delegateToName=row.delegate_to_name,
            priorState=row.prior_state,
            newState=row.new_state,
            comments=row.comments,
            timestamp=row.timestamp,
        )
        for row in rows
    ]
    return ApprovalHistoryListResponse(
        items=items, page=page_params.page, pageSize=page_params.page_size, totalCount=total
    )
