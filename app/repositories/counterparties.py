"""Data access for `counterparties`. Owns queries only -- the business rules (mandatory
fields, email format, GST/Tax ID duplicate detection) live in `app.services.counterparties`.
"""
import uuid

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.counterparty import Counterparty


def search_by_tenant(db: Session, tenant_id: uuid.UUID, search: str | None) -> list[Counterparty]:
    query = db.query(Counterparty).filter(
        Counterparty.tenant_id == tenant_id, Counterparty.deleted_at.is_(None)
    )
    if search:
        pattern = f"%{search}%"
        query = query.filter(
            Counterparty.name.ilike(pattern)
            | Counterparty.company.ilike(pattern)
            | Counterparty.gst_tax_id.ilike(pattern)
        )
    return query.order_by(Counterparty.name.asc()).all()


def find_by_gst_tax_id(db: Session, tenant_id: uuid.UUID, gst_tax_id: str) -> Counterparty | None:
    return (
        db.query(Counterparty)
        .filter(
            Counterparty.tenant_id == tenant_id,
            Counterparty.deleted_at.is_(None),
            func.lower(Counterparty.gst_tax_id) == gst_tax_id.lower(),
        )
        .first()
    )


def insert_counterparty(db: Session, counterparty: Counterparty) -> Counterparty:
    db.add(counterparty)
    db.flush()
    return counterparty
