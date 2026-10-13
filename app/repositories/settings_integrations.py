"""Data access for `tenant_integrations`. Owns queries only -- credential validation,
masking and the connected/disconnected transition rules live in
`app.services.settings_integrations`.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.tracker import TenantIntegration

INTEGRATION_NAMES = (
    "Salesforce",
    "HubSpot",
    "ERP",
    "Google Drive",
    "SharePoint",
    "DocuSign",
    "Adobe Sign",
)


def ensure_seeded(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Idempotent seed: every tenant sees all 7 integration cards (UC11-FV-003) even before
    any of them has ever been connected. Guarded by a lookup per name, not a bulk insert, so
    re-running this on every GET never duplicates a row.
    """
    existing_names = {
        row.integration_name
        for row in db.query(TenantIntegration.integration_name)
        .filter(TenantIntegration.tenant_id == tenant_id)
        .all()
    }
    for name in INTEGRATION_NAMES:
        if name in existing_names:
            continue
        db.add(
            TenantIntegration(
                tenant_id=tenant_id,
                integration_name=name,
                connection_status="Disconnected",
                created_by=user_id,
                updated_by=user_id,
            )
        )
    db.flush()


def list_by_tenant(db: Session, tenant_id: uuid.UUID) -> list[TenantIntegration]:
    rows = db.query(TenantIntegration).filter(TenantIntegration.tenant_id == tenant_id).all()
    order = {name: index for index, name in enumerate(INTEGRATION_NAMES)}
    return sorted(rows, key=lambda row: order.get(row.integration_name, len(order)))


def get_by_name(db: Session, tenant_id: uuid.UUID, integration_name: str) -> TenantIntegration | None:
    return (
        db.query(TenantIntegration)
        .filter(
            TenantIntegration.tenant_id == tenant_id,
            TenantIntegration.integration_name == integration_name,
        )
        .first()
    )


def insert(db: Session, row: TenantIntegration) -> TenantIntegration:
    db.add(row)
    db.flush()
    return row
