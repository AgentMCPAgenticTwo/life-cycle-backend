"""Data access for `contracts`. Owns queries only -- validation and status rules live in
`app.services.contracts`. Cross-entity lookups (users, counterparties, templates, uploaded
files) that a contract merely references also live here: they are still plain data access,
not business rules.
"""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.approval import Approval, ApprovalDelegation, ApprovalStepInstance
from app.models.contract import Contract, ContractTask
from app.models.counterparty import Counterparty
from app.models.lifecycle_negotiation import NegotiationReviewer, NegotiationRouting
from app.models.template import Template
from app.models.uploaded_file import UploadedFile
from app.models.user import User

_SORTABLE_COLUMNS = {
    "contractName": Contract.contract_name,
    "startDate": Contract.start_date,
    "endDate": Contract.end_date,
    "contractValue": Contract.contract_value,
    "status": Contract.status,
}


def get_by_id(db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID) -> Contract | None:
    return (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.tenant_id == tenant_id, Contract.deleted_at.is_(None))
        .first()
    )


def list_by_tenant(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    search: str | None,
    sort_by: str | None,
    sort_order: str | None,
    status: str | None,
    contract_type: str | None,
    department: str | None,
    counterparty_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    start_date: date | None,
    end_date: date | None,
    offset: int,
    limit: int,
) -> tuple[list[Contract], int]:
    query = db.query(Contract).filter(Contract.tenant_id == tenant_id, Contract.deleted_at.is_(None))
    if status:
        query = query.filter(Contract.status == status)
    if contract_type:
        query = query.filter(Contract.contract_type == contract_type)
    if department:
        query = query.filter(Contract.department == department)
    if counterparty_id:
        query = query.filter(Contract.counterparty_id == counterparty_id)
    if owner_id:
        query = query.filter(Contract.contract_owner_id == owner_id)
    if start_date:
        query = query.filter(Contract.start_date >= start_date)
    if end_date:
        query = query.filter(Contract.end_date <= end_date)
    if search:
        query = query.filter(Contract.contract_name.ilike(f"%{search}%"))

    total = query.count()

    sort_column = _SORTABLE_COLUMNS.get(sort_by or "", Contract.created_at)
    order_clause = sort_column.asc() if sort_order == "asc" else sort_column.desc()
    rows = query.order_by(order_clause).offset(offset).limit(limit).all()
    return rows, total


def insert_contract(db: Session, contract: Contract) -> Contract:
    db.add(contract)
    db.flush()
    return contract


def get_user(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> User | None:
    return (
        db.query(User)
        .filter(User.id == user_id, User.tenant_id == tenant_id, User.deleted_at.is_(None))
        .first()
    )


def get_counterparty(db: Session, tenant_id: uuid.UUID, counterparty_id: uuid.UUID) -> Counterparty | None:
    return (
        db.query(Counterparty)
        .filter(
            Counterparty.id == counterparty_id,
            Counterparty.tenant_id == tenant_id,
            Counterparty.deleted_at.is_(None),
        )
        .first()
    )


def insert_counterparty(db: Session, counterparty: Counterparty) -> Counterparty:
    db.add(counterparty)
    db.flush()
    return counterparty


def get_template(db: Session, tenant_id: uuid.UUID, template_id: uuid.UUID) -> Template | None:
    return (
        db.query(Template)
        .filter(Template.id == template_id, Template.tenant_id == tenant_id, Template.deleted_at.is_(None))
        .first()
    )


def get_uploaded_file(db: Session, tenant_id: uuid.UUID, file_id: uuid.UUID) -> UploadedFile | None:
    return (
        db.query(UploadedFile)
        .filter(
            UploadedFile.id == file_id,
            UploadedFile.tenant_id == tenant_id,
            UploadedFile.deleted_at.is_(None),
        )
        .first()
    )


def is_workflow_participant(db: Session, contract_id: uuid.UUID, user_id: uuid.UUID) -> bool:
    """True when the user is linked to this contract's workflow: an internal reviewer on its
    negotiation routing, or the approver / a delegate on any of its approval steps."""
    reviewer = (
        db.query(NegotiationReviewer.id)
        .join(NegotiationRouting, NegotiationRouting.id == NegotiationReviewer.negotiation_routing_id)
        .filter(NegotiationRouting.contract_id == contract_id, NegotiationReviewer.reviewer_id == user_id)
        .first()
    )
    if reviewer is not None:
        return True
    approver = (
        db.query(ApprovalStepInstance.id)
        .join(Approval, Approval.id == ApprovalStepInstance.approval_id)
        .filter(Approval.contract_id == contract_id, ApprovalStepInstance.approver_user_id == user_id)
        .first()
    )
    if approver is not None:
        return True
    delegate = (
        db.query(ApprovalDelegation.id)
        .join(Approval, Approval.id == ApprovalDelegation.approval_id)
        .filter(Approval.contract_id == contract_id, ApprovalDelegation.delegate_to_user_id == user_id)
        .first()
    )
    return delegate is not None


def get_current_task_for_assignee(
    db: Session, contract_id: uuid.UUID, user_id: uuid.UUID
) -> ContractTask | None:
    """UC1-AF-006: a Legal Reviewer/Approver/Signer has "permitted actions" on a contract
    only while a `contract_tasks` row currently assigns them its pending step."""
    return (
        db.query(ContractTask)
        .filter(
            ContractTask.contract_id == contract_id,
            ContractTask.assignee_user_id == user_id,
            ContractTask.is_current.is_(True),
            ContractTask.deleted_at.is_(None),
        )
        .first()
    )
