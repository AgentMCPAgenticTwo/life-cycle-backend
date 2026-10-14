"""Data access for `approval_matrix_configs` / `approval_matrix_steps`. Owns queries only --
the business rules (validation, full-replace semantics) live in `app.services.approval_matrix`.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.approval import Approval, ApprovalMatrixConfig, ApprovalMatrixStep


def list_by_tenant(db: Session, tenant_id: uuid.UUID) -> list[ApprovalMatrixConfig]:
    return (
        db.query(ApprovalMatrixConfig)
        .filter(ApprovalMatrixConfig.tenant_id == tenant_id, ApprovalMatrixConfig.archived_at.is_(None))
        .order_by(ApprovalMatrixConfig.contract_type.asc())
        .all()
    )


def list_steps(db: Session, config_ids: list[uuid.UUID]) -> list[ApprovalMatrixStep]:
    if not config_ids:
        return []
    return (
        db.query(ApprovalMatrixStep)
        .filter(ApprovalMatrixStep.config_id.in_(config_ids))
        .order_by(ApprovalMatrixStep.config_id.asc(), ApprovalMatrixStep.step_number.asc())
        .all()
    )


def delete_all(db: Session, tenant_id: uuid.UUID) -> None:
    """Remove the tenant's current configs. One an approval still points at (via
    `approvals.config_id`) is archived instead of deleted -- deleting it would violate that
    foreign key and strip the approval of its step names and approvers."""
    config_ids = [
        row.id
        for row in db.query(ApprovalMatrixConfig.id).filter(
            ApprovalMatrixConfig.tenant_id == tenant_id, ApprovalMatrixConfig.archived_at.is_(None)
        )
    ]
    if not config_ids:
        return
    referenced = {
        row.config_id
        for row in db.query(Approval.config_id).filter(Approval.config_id.in_(config_ids)).distinct()
    }
    if referenced:
        db.query(ApprovalMatrixConfig).filter(ApprovalMatrixConfig.id.in_(referenced)).update(
            {ApprovalMatrixConfig.archived_at: datetime.now(timezone.utc)}, synchronize_session=False
        )
    unreferenced = [config_id for config_id in config_ids if config_id not in referenced]
    if unreferenced:
        db.query(ApprovalMatrixStep).filter(ApprovalMatrixStep.config_id.in_(unreferenced)).delete(
            synchronize_session=False
        )
        db.query(ApprovalMatrixConfig).filter(ApprovalMatrixConfig.id.in_(unreferenced)).delete(
            synchronize_session=False
        )


def insert_config(db: Session, config: ApprovalMatrixConfig) -> ApprovalMatrixConfig:
    db.add(config)
    db.flush()
    return config


def insert_step(db: Session, step: ApprovalMatrixStep) -> ApprovalMatrixStep:
    db.add(step)
    db.flush()
    return step
