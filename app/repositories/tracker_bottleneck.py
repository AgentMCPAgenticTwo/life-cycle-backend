"""Data access for the Bottleneck tab. Owns queries only -- the business rules (role
scoping, stage derivation, stuck-flag thresholds, empty-state tiers) live in
`app.services.tracker_bottleneck`.

`contract_lifecycle_stage_history` is this module's source of truth for "current stage" and
"days in current stage" (see its context.json description), but nothing in this codebase's
other modules writes to it yet (see that task's `blockers`). Contracts with no open stage-
history row fall back to a status-derived stage so the endpoint still returns useful data
against the contracts other modules do write.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.tracker import ContractLifecycleStageHistory, ContractOwner, TenantBottleneckThreshold
from app.models.user import User

# Fallback mapping from `contracts.status` (written by other modules) to this module's
# four-stage enum, used only when no `contract_lifecycle_stage_history` row exists yet for a
# contract. Statuses with no obvious open stage (Executed, Terminated, Rejected, ...) are
# excluded from the Bottleneck tab entirely -- they are no longer "in" a trackable stage.
STATUS_TO_STAGE = {
    "Draft": "Drafting",
    "In Negotiation": "Negotiation",
    "PendingApproval": "Approval",
    "Pending Approval": "Approval",
    "Ready For Signature": "Signature",
    "Sent": "Signature",
}

DEFAULT_THRESHOLDS = {"Drafting": 5, "Negotiation": 5, "Approval": 3, "Signature": 3}


def list_open_stage_rows(db: Session, tenant_id: uuid.UUID) -> dict[uuid.UUID, ContractLifecycleStageHistory]:
    """Latest open (`stage_end_date IS NULL`) stage-history row per contract, keyed by contract_id."""
    rows = (
        db.query(ContractLifecycleStageHistory)
        .filter(
            ContractLifecycleStageHistory.tenant_id == tenant_id,
            ContractLifecycleStageHistory.deleted_at.is_(None),
            ContractLifecycleStageHistory.stage_end_date.is_(None),
        )
        .order_by(ContractLifecycleStageHistory.stage_start_date.desc())
        .all()
    )
    result: dict[uuid.UUID, ContractLifecycleStageHistory] = {}
    for row in rows:
        result.setdefault(row.contract_id, row)
    return result


def list_owner_role_contract_ids(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID, role: str) -> set[uuid.UUID]:
    rows = (
        db.query(ContractOwner.contract_id)
        .filter(
            ContractOwner.tenant_id == tenant_id,
            ContractOwner.user_id == user_id,
            ContractOwner.role == role,
            ContractOwner.deleted_at.is_(None),
        )
        .all()
    )
    return {r[0] for r in rows}


def list_tenant_contracts(db: Session, tenant_id: uuid.UUID) -> list[Contract]:
    return db.query(Contract).filter(Contract.tenant_id == tenant_id, Contract.deleted_at.is_(None)).all()


def get_thresholds(db: Session, tenant_id: uuid.UUID) -> dict[str, int]:
    rows = db.query(TenantBottleneckThreshold).filter(TenantBottleneckThreshold.tenant_id == tenant_id).all()
    thresholds = dict(DEFAULT_THRESHOLDS)
    for row in rows:
        thresholds[row.stage] = row.threshold_days
    return thresholds


def get_user_names(db: Session, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    if not user_ids:
        return {}
    rows = db.query(User.id, User.name).filter(User.id.in_(user_ids)).all()
    return {r[0]: r[1] for r in rows}


def list_completed_stage_rows(db: Session, tenant_id: uuid.UUID) -> list[ContractLifecycleStageHistory]:
    """Stage-history rows with a `stage_end_date` -- the completed-stage durations the Cycle
    Time tab (UC10-BR-001) averages. See `app.repositories.tracker_cycle_time` for the
    read path that consumes this.
    """
    return (
        db.query(ContractLifecycleStageHistory)
        .filter(
            ContractLifecycleStageHistory.tenant_id == tenant_id,
            ContractLifecycleStageHistory.deleted_at.is_(None),
            ContractLifecycleStageHistory.stage_end_date.isnot(None),
        )
        .all()
    )
