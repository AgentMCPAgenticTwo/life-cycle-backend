"""Data access for `approval_matrix_configs` / `approval_matrix_steps`. Owns queries only --
the business rules (validation, full-replace semantics) live in `app.services.approval_matrix`.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.approval import ApprovalMatrixConfig, ApprovalMatrixStep


def list_by_tenant(db: Session, tenant_id: uuid.UUID) -> list[ApprovalMatrixConfig]:
    return (
        db.query(ApprovalMatrixConfig)
        .filter(ApprovalMatrixConfig.tenant_id == tenant_id)
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
    config_ids = [
        row.id for row in db.query(ApprovalMatrixConfig.id).filter(ApprovalMatrixConfig.tenant_id == tenant_id)
    ]
    if config_ids:
        db.query(ApprovalMatrixStep).filter(ApprovalMatrixStep.config_id.in_(config_ids)).delete(
            synchronize_session=False
        )
        db.query(ApprovalMatrixConfig).filter(ApprovalMatrixConfig.id.in_(config_ids)).delete(
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
