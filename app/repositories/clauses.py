"""Data access for `clauses` / `clause_versions`. Owns queries only -- the business rules
(completeness, versioning, lifecycle transitions) live in `app.services.clauses`.
"""
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.clause import Clause, ClauseVersion


def get_by_id(db: Session, tenant_id: uuid.UUID, clause_id: uuid.UUID) -> Clause | None:
    return (
        db.query(Clause)
        .filter(Clause.id == clause_id, Clause.tenant_id == tenant_id, Clause.deleted_at.is_(None))
        .first()
    )


def list_by_tenant(db: Session, tenant_id: uuid.UUID, statuses: list[str] | None = None) -> list[Clause]:
    query = db.query(Clause).filter(Clause.tenant_id == tenant_id, Clause.deleted_at.is_(None))
    if statuses:
        query = query.filter(Clause.status.in_(statuses))
    return query.order_by(Clause.clause_name.asc()).all()


def list_versions(db: Session, clause_id: uuid.UUID) -> list[ClauseVersion]:
    return (
        db.query(ClauseVersion)
        .filter(ClauseVersion.clause_id == clause_id)
        .order_by(ClauseVersion.version_number.asc())
        .all()
    )


def insert_clause(db: Session, clause: Clause) -> Clause:
    db.add(clause)
    db.flush()
    return clause


def insert_version(db: Session, version: ClauseVersion) -> ClauseVersion:
    db.add(version)
    db.flush()
    return version


def snapshot_version(
    db: Session, clause: Clause, *, changed_by: uuid.UUID, now: datetime, change_summary: str | None
) -> ClauseVersion:
    """Copies the clause's current field values into an immutable `clause_versions` row."""
    version = ClauseVersion(
        clause_id=clause.id,
        version_number=clause.current_version,
        changed_by=changed_by,
        date_changed=now,
        change_summary=change_summary,
        clause_name=clause.clause_name,
        clause_category=clause.clause_category,
        standard_text=clause.standard_text,
        fallback_text_1=clause.fallback_text_1,
        fallback_text_2=clause.fallback_text_2,
        risk_level=clause.risk_level,
        mandatory=clause.mandatory,
        status=clause.status,
        created_by=changed_by,
        updated_by=changed_by,
    )
    return insert_version(db, version)
