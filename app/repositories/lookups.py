"""Data access for the dashboard/lookup endpoints: status counts, My Tasks assignments, High
Risk contracts, filter-option values and the Contract Owner dropdown. Owns queries only --
role scoping, thresholds and messages live in `app.services.lookups`.
"""
import uuid
from datetime import date

from sqlalchemy.orm import Session

from app.models.contract import Contract, ContractTask
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.user import User


def _apply_contract_filters(
    query,
    *,
    contract_type: str | None,
    department: str | None,
    counterparty_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    start_date: date | None,
    end_date: date | None,
):
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
    return query


def count_tenant_contracts(db: Session, tenant_id: uuid.UUID) -> int:
    return (
        db.query(Contract)
        .filter(Contract.tenant_id == tenant_id, Contract.deleted_at.is_(None))
        .count()
    )


def list_filtered_contracts(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    contract_type: str | None,
    department: str | None,
    counterparty_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> list[Contract]:
    query = db.query(Contract).filter(Contract.tenant_id == tenant_id, Contract.deleted_at.is_(None))
    query = _apply_contract_filters(
        query,
        contract_type=contract_type,
        department=department,
        counterparty_id=counterparty_id,
        owner_id=owner_id,
        start_date=start_date,
        end_date=end_date,
    )
    return query.all()


def list_current_tasks_for_assignee(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    *,
    contract_type: str | None,
    department: str | None,
    counterparty_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> list[tuple[ContractTask, Contract]]:
    """UC1-BR-003: contracts whose *current* pending step is assigned to this user, joined so
    the task's own due date (the pending step's due date, not the contract's overall due date)
    comes back alongside the contract."""
    query = (
        db.query(ContractTask, Contract)
        .join(Contract, Contract.id == ContractTask.contract_id)
        .filter(
            ContractTask.assignee_user_id == user_id,
            ContractTask.is_current.is_(True),
            ContractTask.deleted_at.is_(None),
            Contract.tenant_id == tenant_id,
            Contract.deleted_at.is_(None),
        )
    )
    query = _apply_contract_filters(
        query,
        contract_type=contract_type,
        department=department,
        counterparty_id=counterparty_id,
        owner_id=owner_id,
        start_date=start_date,
        end_date=end_date,
    )
    return query.all()


def list_owned_open_contracts(
    db: Session,
    tenant_id: uuid.UUID,
    owner_id: uuid.UUID,
    *,
    contract_type: str | None,
    department: str | None,
    counterparty_id: uuid.UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> list[Contract]:
    """UC1-BR-011: a Contract Owner's My Tasks shows contracts they own awaiting any action
    (i.e. not yet Executed), regardless of which step is currently pending."""
    query = db.query(Contract).filter(
        Contract.tenant_id == tenant_id,
        Contract.contract_owner_id == owner_id,
        Contract.status != "Executed",
        Contract.deleted_at.is_(None),
    )
    query = _apply_contract_filters(
        query,
        contract_type=contract_type,
        department=department,
        counterparty_id=counterparty_id,
        owner_id=None,
        start_date=start_date,
        end_date=end_date,
    )
    return query.all()


def get_tenant(db: Session, tenant_id: uuid.UUID) -> Tenant | None:
    return db.query(Tenant).filter(Tenant.id == tenant_id).first()


def get_counterparty(db: Session, counterparty_id: uuid.UUID) -> Counterparty | None:
    return db.query(Counterparty).filter(Counterparty.id == counterparty_id).first()


def list_counterparties(db: Session, tenant_id: uuid.UUID) -> list[Counterparty]:
    return (
        db.query(Counterparty)
        .filter(Counterparty.tenant_id == tenant_id, Counterparty.deleted_at.is_(None))
        .order_by(Counterparty.name.asc())
        .all()
    )


def list_distinct_departments(db: Session, tenant_id: uuid.UUID) -> list[str]:
    rows = (
        db.query(Contract.department)
        .filter(
            Contract.tenant_id == tenant_id,
            Contract.deleted_at.is_(None),
            Contract.department.is_not(None),
        )
        .distinct()
        .all()
    )
    return sorted({r[0] for r in rows if r[0]})


def list_users_by_role(db: Session, tenant_id: uuid.UUID, role: str | None) -> list[User]:
    query = db.query(User).filter(User.tenant_id == tenant_id, User.deleted_at.is_(None))
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.name.asc()).all()
