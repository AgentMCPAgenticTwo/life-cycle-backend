"""Data access for `esignature_settings`. Owns queries only -- the business rules
(defaulting, validation) live in `app.services.esignature_settings`.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.esignature import EsignatureSettings


def get_by_tenant(db: Session, tenant_id: uuid.UUID) -> EsignatureSettings | None:
    return (
        db.query(EsignatureSettings)
        .filter(EsignatureSettings.tenant_id == tenant_id)
        .first()
    )


def insert(db: Session, settings: EsignatureSettings) -> EsignatureSettings:
    db.add(settings)
    db.flush()
    return settings
