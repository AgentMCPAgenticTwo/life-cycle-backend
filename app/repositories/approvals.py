"""Data access for `approvals`, `approval_step_instances`, `approval_delegations` and
`approval_audit_log`. Owns queries only -- business rules (sequence enforcement, mandatory
comments, ownership checks) live in `app.services.approvals`.
"""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.approval import (
    Approval,
    ApprovalAuditLog,
    ApprovalDelegation,
    ApprovalStepInstance,
)
from app.models.contract import Contract


def get_approval_with_contract(
    db: Session, tenant_id: uuid.UUID, approval_id: uuid.UUID
) -> tuple[Approval, Contract] | None:
    row = (
        db.query(Approval, Contract)
        .join(Contract, Contract.id == Approval.contract_id)
        .filter(
            Approval.id == approval_id,
            Contract.tenant_id == tenant_id,
            Contract.deleted_at.is_(None),
        )
        .first()
    )
    return row


def list_for_tenant(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    contract_owner_id: uuid.UUID | None,
    current_approver_ids: list[uuid.UUID] | None,
    offset: int,
    limit: int,
) -> tuple[list[tuple[Approval, Contract]], int]:
    query = (
        db.query(Approval, Contract)
        .join(Contract, Contract.id == Approval.contract_id)
        .filter(Contract.tenant_id == tenant_id, Contract.deleted_at.is_(None))
    )
    if contract_owner_id is not None:
        query = query.filter(Contract.contract_owner_id == contract_owner_id)
    if current_approver_ids is not None:
        if not current_approver_ids:
            return [], 0
        query = (
            query.join(
                ApprovalStepInstance,
                (ApprovalStepInstance.approval_id == Approval.id)
                & (ApprovalStepInstance.step_number == Approval.current_step_number),
            )
            .filter(ApprovalStepInstance.approver_user_id.in_(current_approver_ids))
        )
    total = query.count()
    rows = query.order_by(Approval.created_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def get_current_step_instance(
    db: Session, approval_id: uuid.UUID, step_number: int
) -> ApprovalStepInstance | None:
    return (
        db.query(ApprovalStepInstance)
        .filter(
            ApprovalStepInstance.approval_id == approval_id,
            ApprovalStepInstance.step_number == step_number,
        )
        .first()
    )


def get_active_delegation(
    db: Session, approval_id: uuid.UUID, approver_user_id: uuid.UUID, delegate_to_user_id: uuid.UUID, today: date
) -> ApprovalDelegation | None:
    return (
        db.query(ApprovalDelegation)
        .filter(
            ApprovalDelegation.approval_id == approval_id,
            ApprovalDelegation.approver_user_id == approver_user_id,
            ApprovalDelegation.delegate_to_user_id == delegate_to_user_id,
            ApprovalDelegation.start_date <= today,
            ApprovalDelegation.end_date >= today,
        )
        .first()
    )


def list_active_delegations_for_user(
    db: Session, delegate_to_user_id: uuid.UUID, today: date
) -> list[ApprovalDelegation]:
    return (
        db.query(ApprovalDelegation)
        .filter(
            ApprovalDelegation.delegate_to_user_id == delegate_to_user_id,
            ApprovalDelegation.start_date <= today,
            ApprovalDelegation.end_date >= today,
        )
        .all()
    )


def insert_delegation(db: Session, delegation: ApprovalDelegation) -> ApprovalDelegation:
    db.add(delegation)
    db.flush()
    return delegation


def insert_audit_log(db: Session, entry: ApprovalAuditLog) -> ApprovalAuditLog:
    db.add(entry)
    db.flush()
    return entry


def list_history(
    db: Session, approval_id: uuid.UUID, *, offset: int, limit: int
) -> tuple[list[ApprovalAuditLog], int]:
    query = db.query(ApprovalAuditLog).filter(ApprovalAuditLog.approval_id == approval_id)
    total = query.count()
    rows = query.order_by(ApprovalAuditLog.timestamp.desc()).offset(offset).limit(limit).all()
    return rows, total
