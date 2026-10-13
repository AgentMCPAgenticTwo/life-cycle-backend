"""Data access for the Turnaround tab. Owns queries only -- the business rules (role scoping,
BR-4/BR-7 Estimated Turnaround derivation, variance color coding, the empty-state tiers) live
in `app.services.tracker_turnaround`.

The entitlement, open-stage and tenant-contract lookups are identical to the Bottleneck tab's
(UC10-BR-005/009/010/011 apply the same way here), so this module reuses
`app.repositories.tracker_bottleneck` for those rather than duplicating the queries.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.tracker import ContractTurnaroundMetrics, TurnaroundOverrideLog
from app.repositories.tracker_bottleneck import (  # noqa: F401
    STATUS_TO_STAGE,
    list_open_stage_rows,
    list_owner_role_contract_ids,
    list_tenant_contracts,
)


def get_metrics_by_contract(
    db: Session, tenant_id: uuid.UUID, contract_ids: set[uuid.UUID]
) -> dict[uuid.UUID, ContractTurnaroundMetrics]:
    if not contract_ids:
        return {}
    rows = (
        db.query(ContractTurnaroundMetrics)
        .filter(
            ContractTurnaroundMetrics.tenant_id == tenant_id,
            ContractTurnaroundMetrics.contract_id.in_(contract_ids),
            ContractTurnaroundMetrics.deleted_at.is_(None),
        )
        .all()
    )
    return {row.contract_id: row for row in rows}


def get_metrics_for_contract(
    db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID
) -> ContractTurnaroundMetrics | None:
    return (
        db.query(ContractTurnaroundMetrics)
        .filter(
            ContractTurnaroundMetrics.tenant_id == tenant_id,
            ContractTurnaroundMetrics.contract_id == contract_id,
            ContractTurnaroundMetrics.deleted_at.is_(None),
        )
        .first()
    )


def add_override_log(db: Session, log: TurnaroundOverrideLog) -> None:
    db.add(log)
    db.commit()
