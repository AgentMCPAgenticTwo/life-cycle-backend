"""Data access for `approval_matrix_rules`. Owns queries only -- the business rules (required
field / duplicate-combination validation) live in `app.services.settings_approval_rules`.
"""
import uuid
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.tracker import ApprovalMatrixRule


def list_by_tenant(
    db: Session, tenant_id: uuid.UUID, *, offset: int, limit: int
) -> tuple[list[ApprovalMatrixRule], int]:
    query = (
        db.query(ApprovalMatrixRule)
        .filter(ApprovalMatrixRule.tenant_id == tenant_id, ApprovalMatrixRule.deleted_at.is_(None))
        .order_by(ApprovalMatrixRule.contract_type.asc(), ApprovalMatrixRule.value_threshold.asc())
    )
    total = query.count()
    rows = query.offset(offset).limit(limit).all()
    return rows, total


def find_by_type_and_threshold(
    db: Session,
    tenant_id: uuid.UUID,
    contract_type: str,
    value_threshold: Decimal,
    *,
    exclude_id: uuid.UUID | None = None,
) -> ApprovalMatrixRule | None:
    query = db.query(ApprovalMatrixRule).filter(
        ApprovalMatrixRule.tenant_id == tenant_id,
        ApprovalMatrixRule.contract_type == contract_type,
        ApprovalMatrixRule.value_threshold == value_threshold,
        ApprovalMatrixRule.deleted_at.is_(None),
    )
    if exclude_id is not None:
        query = query.filter(ApprovalMatrixRule.id != exclude_id)
    return query.first()


def get_by_id(db: Session, tenant_id: uuid.UUID, rule_id: uuid.UUID) -> ApprovalMatrixRule | None:
    return (
        db.query(ApprovalMatrixRule)
        .filter(
            ApprovalMatrixRule.id == rule_id,
            ApprovalMatrixRule.tenant_id == tenant_id,
            ApprovalMatrixRule.deleted_at.is_(None),
        )
        .first()
    )


def insert(db: Session, rule: ApprovalMatrixRule) -> ApprovalMatrixRule:
    db.add(rule)
    db.flush()
    return rule
