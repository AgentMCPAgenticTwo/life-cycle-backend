"""Data access for `contract_clauses`, `contract_metadata`, `clause_audit_log` and
`ask_ai_interactions`. Owns queries only -- the business rules (risk scoring, mandatory-flag
evaluation, status transitions, labelling) live in `app.services.lifecycle_clauses`.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.lifecycle_clause import (
    AskAiInteraction,
    ClauseAuditLog,
    ContractClause,
    ContractMetadata,
)


def list_clauses(db: Session, contract_id: uuid.UUID) -> list[ContractClause]:
    return (
        db.query(ContractClause)
        .filter(ContractClause.contract_id == contract_id, ContractClause.deleted_at.is_(None))
        .order_by(ContractClause.created_at.asc())
        .all()
    )


def get_clause(db: Session, contract_id: uuid.UUID, clause_id: uuid.UUID) -> ContractClause | None:
    return (
        db.query(ContractClause)
        .filter(
            ContractClause.id == clause_id,
            ContractClause.contract_id == contract_id,
            ContractClause.deleted_at.is_(None),
        )
        .first()
    )


def insert_clause(db: Session, clause: ContractClause) -> ContractClause:
    db.add(clause)
    db.flush()
    return clause


def get_metadata(db: Session, contract_id: uuid.UUID) -> ContractMetadata | None:
    return db.query(ContractMetadata).filter(ContractMetadata.contract_id == contract_id).first()


def insert_metadata(db: Session, metadata: ContractMetadata) -> ContractMetadata:
    db.add(metadata)
    db.flush()
    return metadata


def insert_audit_entry(db: Session, entry: ClauseAuditLog) -> ClauseAuditLog:
    db.add(entry)
    db.flush()
    return entry


def list_audit_log(
    db: Session, contract_id: uuid.UUID, *, offset: int, limit: int
) -> tuple[list[ClauseAuditLog], int]:
    query = db.query(ClauseAuditLog).filter(ClauseAuditLog.contract_id == contract_id)
    total = query.count()
    rows = query.order_by(ClauseAuditLog.occurred_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def get_latest_audit_entry(
    db: Session,
    contract_id: uuid.UUID,
    *,
    action_types: list[str],
    field_name: str | None = None,
) -> ClauseAuditLog | None:
    query = db.query(ClauseAuditLog).filter(
        ClauseAuditLog.contract_id == contract_id,
        ClauseAuditLog.action_type.in_(action_types),
    )
    if field_name is not None:
        query = query.filter(ClauseAuditLog.field_name == field_name)
    return query.order_by(ClauseAuditLog.occurred_at.desc(), ClauseAuditLog.created_at.desc()).first()


def insert_ask_ai_interaction(db: Session, interaction: AskAiInteraction) -> AskAiInteraction:
    db.add(interaction)
    db.flush()
    return interaction
