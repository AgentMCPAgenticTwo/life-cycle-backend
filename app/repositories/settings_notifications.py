"""Data access for `tenant_notification_settings`. Owns queries only -- defaulting new
events to On (UC11-BR-007) and the update rules live in
`app.services.settings_notifications`.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.tracker import TenantNotificationSetting

EVENT_NAMES = (
    "Contract Sent for Approval",
    "Contract Approved",
    "Contract Rejected",
    "Contract Sent Back",
    "Contract Ready for Signature",
    "Contract Sent for Signature",
    "Contract Signature Declined",
    "Contract Signed",
    "New User Invited",
    "Contract Expiring Soon",
    "Contract Renewed",
)


def ensure_seeded(db: Session, tenant_id: uuid.UUID, user_id: uuid.UUID) -> None:
    """Idempotent seed: every tenant sees all status-change events with both toggles On by
    default (UC11-BR-007), even before any of them has ever been saved. Guarded by a lookup
    per name, not a bulk insert, so re-running this on every GET never duplicates a row.
    """
    existing_names = {
        row.event_name
        for row in db.query(TenantNotificationSetting.event_name)
        .filter(TenantNotificationSetting.tenant_id == tenant_id)
        .all()
    }
    for name in EVENT_NAMES:
        if name in existing_names:
            continue
        db.add(
            TenantNotificationSetting(
                tenant_id=tenant_id,
                event_name=name,
                email_toggle=True,
                in_app_toggle=True,
                created_by=user_id,
                updated_by=user_id,
            )
        )
    db.flush()


def list_by_tenant(db: Session, tenant_id: uuid.UUID) -> list[TenantNotificationSetting]:
    rows = (
        db.query(TenantNotificationSetting)
        .filter(TenantNotificationSetting.tenant_id == tenant_id)
        .all()
    )
    order = {name: index for index, name in enumerate(EVENT_NAMES)}
    return sorted(rows, key=lambda row: order.get(row.event_name, len(order)))


def get_by_name(
    db: Session, tenant_id: uuid.UUID, event_name: str
) -> TenantNotificationSetting | None:
    return (
        db.query(TenantNotificationSetting)
        .filter(
            TenantNotificationSetting.tenant_id == tenant_id,
            TenantNotificationSetting.event_name == event_name,
        )
        .first()
    )


def insert(db: Session, row: TenantNotificationSetting) -> TenantNotificationSetting:
    db.add(row)
    db.flush()
    return row
