"""Business rules for the `approvals` resource: visibility/listing, the full approval review
screen with action-eligibility flags, the Approve/Reject/Send Back transition, time-bound
delegation, and the immutable Approval History tab -- see CLAUDE.md's UC6-UC7-combined module
section and this task's stories (T-APPROVALS-API/TASK.md).

This task owns `approvals`, `approval_step_instances`, `approval_delegations` and
`approval_audit_log`. There is no endpoint to create an `Approval`: Mark as Agreed (UC5) calls
`start_approval`, which matches the tenant's approval rules to the contract's type and value
and opens Step 1. A Send Back closes that approval (status `SentBack`, kept for history) and
the next Mark as Agreed opens a new one.
"""
import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from app.models.approval import (
    Approval,
    ApprovalAuditLog,
    ApprovalDelegation,
    ApprovalMatrixConfig,
    ApprovalMatrixStep,
    ApprovalStepInstance,
)
from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.tracker import ApprovalMatrixRule
from app.models.user import User
from app.repositories import approvals as approvals_repo
from app.repositories import lifecycle_negotiation as negotiation_repo
from app.services import contract_status
from app.services import notifications
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
# `/api/v1/contracts/{id}` response validates against). This module persists the shared
# space-separated values (see `app.services.contract_status`) and maps to its own wire format
# only in its own responses.
_CONTRACT_STATUS_TO_WIRE = {
    "Draft": "Draft",
    "In Negotiation": "InNegotiation",
    "Pending Approval": "PendingApproval",
    "Pending Signature": "PendingSignature",
    "Executed": "Executed",
    "Rejected": "Rejected",
}

# Approval (not contract) statuses.
APPROVAL_PENDING = "PendingApproval"
APPROVAL_APPROVED = "Approved"
APPROVAL_REJECTED = "Rejected"
APPROVAL_SENT_BACK = "SentBack"

NO_MATCHING_RULE_MESSAGE = (
    "No approval rule found for this contract type and value. Please contact your Tenant Admin."
)

# Settings > Routing & Approval stores the approver role by its display name.
_RULE_ROLE_TO_USER_ROLE = {
    "Approver": "APPROVER",
    "Legal Reviewer": "LEGAL_REVIEWER",
    "Tenant Admin": "TENANT_ADMIN",
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


def _matching_matrix_config(db: Session, tenant_id: uuid.UUID, contract: Contract) -> ApprovalMatrixConfig | None:
    """The Approval Matrix config (UC6) for this contract's type whose value -- and, when the
    contract has a risk score, risk band -- range contains it. The narrowest value band wins."""
    value = Decimal(contract.contract_value)
    risk = contract.risk_score
    candidates = (
        db.query(ApprovalMatrixConfig)
        .filter(ApprovalMatrixConfig.tenant_id == tenant_id, ApprovalMatrixConfig.contract_type == contract.contract_type)
        .all()
    )

    def fits(config: ApprovalMatrixConfig) -> bool:
        if config.value_min is not None and value < config.value_min:
            return False
        if config.value_max is not None and value > config.value_max:
            return False
        if risk is not None:
            if config.risk_band_min is not None and risk < config.risk_band_min:
                return False
            if config.risk_band_max is not None and risk > config.risk_band_max:
                return False
        has_steps = db.query(ApprovalMatrixStep).filter(ApprovalMatrixStep.config_id == config.id).first() is not None
        return has_steps

    matches = [c for c in candidates if fits(c)]
    matches.sort(key=lambda c: c.value_min if c.value_min is not None else Decimal(0), reverse=True)
    return matches[0] if matches else None


def _matching_settings_rules(db: Session, tenant_id: uuid.UUID, contract: Contract) -> list[ApprovalMatrixRule]:
    """Settings > Routing & Approval rules (UC11) whose threshold the contract's value meets, one
    approval step each, lowest threshold first. Their Contract Type is Product/Service, so a
    rule matches on the contract's industry as well as its contract type."""
    return (
        db.query(ApprovalMatrixRule)
        .filter(
            ApprovalMatrixRule.tenant_id == tenant_id,
            ApprovalMatrixRule.deleted_at.is_(None),
            ApprovalMatrixRule.contract_type.in_([contract.contract_type, contract.industry]),
            ApprovalMatrixRule.value_threshold <= contract.contract_value,
        )
        .order_by(ApprovalMatrixRule.value_threshold.asc())
        .all()
    )


def _approver_for_role(db: Session, tenant_id: uuid.UUID, contract: Contract, role_label: str) -> uuid.UUID:
    role = _RULE_ROLE_TO_USER_ROLE.get(role_label, role_label)
    # UC6-BR-011: the Contract Owner is never eligible.
    candidate = (
        db.query(User)
        .filter(
            User.tenant_id == tenant_id,
            User.role == role,
            User.deleted_at.is_(None),
            User.id != contract.contract_owner_id,
        )
        .order_by(User.id.asc())
        .first()
    )
    if candidate is None:
        message = f"No user holds the {role_label} role required by the approval rule. Please contact your Tenant Admin."
        raise ConflictError(message, details=[message])
    return candidate.id


def start_approval(db: Session, tenant_id: uuid.UUID, contract: Contract, actor_id: uuid.UUID) -> Approval:
    """REQ-2: open a new approval request for a contract whose negotiation was just Agreed.

    Matches the tenant's approval rules to the contract's type and value and starts at Step 1.
    Raises ConflictError (writing nothing) when no rule matches. Does not commit; the caller
    commits it together with the contract's move to Pending Approval, then calls
    `notify_step_approver`.
    """
    config = _matching_matrix_config(db, tenant_id, contract)
    rule_approvers: list[uuid.UUID] = []
    if config is not None:
        total_steps = db.query(ApprovalMatrixStep).filter(ApprovalMatrixStep.config_id == config.id).count()
    else:
        rules = _matching_settings_rules(db, tenant_id, contract)
        if not rules:
            raise ConflictError(NO_MATCHING_RULE_MESSAGE, details=[NO_MATCHING_RULE_MESSAGE])
        rule_approvers = [_approver_for_role(db, tenant_id, contract, r.approver_role) for r in rules]
        total_steps = len(rules)

    now = datetime.now(timezone.utc)
    # An approval still open from before a Send Back is superseded, never reused -- it stays
    # in history and the new request starts again at Step 1.
    for previous in (
        db.query(Approval)
        .filter(Approval.contract_id == contract.id, Approval.status == APPROVAL_PENDING)
        .all()
    ):
        previous.status = APPROVAL_SENT_BACK
        previous.updated_by = actor_id
        previous.updated_at = now

    approval = Approval(
        contract_id=contract.id,
        contract_owner_id=contract.contract_owner_id,
        config_id=config.id if config is not None else None,
        current_step_number=1,
        total_steps=total_steps,
        status=APPROVAL_PENDING,
        ai_risk_score=contract.risk_score,
        created_by=actor_id,
        updated_by=actor_id,
        created_at=now,
        updated_at=now,
    )
    db.add(approval)
    db.flush()

    if config is not None:
        _get_or_create_step_instance(db, tenant_id, approval, contract, 1)
    else:
        # Rule-based steps have no matrix row to resolve lazily, so each step's approver is
        # fixed now.
        for step_number, approver_id in enumerate(rule_approvers, start=1):
            db.add(
                ApprovalStepInstance(
                    approval_id=approval.id,
                    step_number=step_number,
                    approver_user_id=approver_id,
                    status="Pending",
                    created_by=actor_id,
                    updated_by=actor_id,
                    created_at=now,
                    updated_at=now,
                )
            )
        db.flush()
    return approval


def notify_step_approver(
    db: Session, tenant_id: uuid.UUID, approval: Approval, contract: Contract, actor_id: uuid.UUID
) -> None:
    """Tell the approver of the approval's current step that the contract is waiting on them."""
    step = approvals_repo.get_current_step_instance(db, approval.id, approval.current_step_number)
    approver = _resolve_user(db, step.approver_user_id) if step is not None else None
    notifications.dispatch(
        db,
        tenant_id,
        notifications.EVENT_SENT_FOR_APPROVAL,
        recipients=[approver.email if approver is not None else None],
        subject=f"Approval needed: {contract.contract_name}",
        body=(
            f"Contract {contract.contract_name} is waiting for your approval "
            f"({_step_label(db, approval, approval.current_step_number)})."
        ),
        entity="Contract",
        actor_id=actor_id,
    )


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

_ACTION_EVENTS = {
    "Approve": notifications.EVENT_APPROVED,
    "Reject": notifications.EVENT_REJECTED,
    "SendBack": notifications.EVENT_SENT_BACK,
}


def _notify_action(
    db: Session,
    tenant_id: uuid.UUID,
    contract: Contract,
    actor_id: uuid.UUID,
    action_type: str,
    approval_status: str,
) -> None:
    """The Contract Owner hears about every decision on their contract, and about the
    chain completing (UC6). Delivery goes through the one notification service, which
    honours Settings > Notifications and never lets a failed send undo the action.
    """
    owner = _resolve_user(db, contract.contract_owner_id)
    recipients = [owner.email if owner is not None else None]
    event = _ACTION_EVENTS[action_type]
    verb = {"Approve": "approved", "Reject": "rejected", "SendBack": "sent back"}[action_type]
    notifications.dispatch(
        db,
        tenant_id,
        event,
        recipients=recipients,
        subject=f"Contract {contract.contract_name} was {verb}",
        body=f"Contract {contract.contract_name} was {verb}.",
        entity="Contract",
        actor_id=actor_id,
    )
    if approval_status == APPROVAL_APPROVED:
        notifications.dispatch(
            db,
            tenant_id,
            notifications.EVENT_READY_FOR_SIGNATURE,
            recipients=recipients,
            subject=f"Contract {contract.contract_name} is ready for signature",
            body=(
                f"All approvals are complete. Contract {contract.contract_name} is ready "
                "for signature."
            ),
            entity="Contract",
            actor_id=actor_id,
        )


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
        approval.status = APPROVAL_REJECTED
        contract_status.transition(db, contract, contract_status.REJECTED, actor_id, "rejected by approver")
    elif payload.actionType == "SendBack":
        step.status = "SentBack"
        # UC6-BR-005: sending back ends this approval request -- it stays in history with its
        # step record, and the next Mark as Agreed opens a new request from Step 1.
        approval.status = APPROVAL_SENT_BACK
        contract_status.transition(
            db, contract, contract_status.IN_NEGOTIATION, actor_id, "sent back by approver"
        )
        routing = negotiation_repo.get_routing_by_contract(db, contract.id)
        if routing is not None:
            routing.negotiation_status = contract_status.NEGOTIATION_SENT_BACK
            routing.updated_by = actor_id
            routing.updated_at = now
    else:  # Approve
        step.status = "Approved"
        if approval.current_step_number < approval.total_steps:
            # UC6-BR-023: automatically advance to the next sequential step; the contract
            # stays Pending Approval.
            approval.current_step_number += 1
            approval.status = APPROVAL_PENDING
            _get_or_create_step_instance(db, tenant_id, approval, contract, approval.current_step_number)
        else:
            # UC6-BR-024 / REQ-3: the last step was approved -- the contract moves to
            # Pending Signature.
            approval.status = APPROVAL_APPROVED
            contract_status.transition(
                db, contract, contract_status.PENDING_SIGNATURE, actor_id, "all approval steps approved"
            )

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

    _notify_action(db, tenant_id, contract, actor_id, payload.actionType, approval.status)
    if payload.actionType == "Approve" and approval.status == APPROVAL_PENDING:
        notify_step_approver(db, tenant_id, approval, contract, actor_id)

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
