"""Business rules for the `settings/notifications` resource: defaulting every status-change
event's Email/In-App toggles to On (UC11-BR-007), updating one toggle without disturbing the
other (UC11-FV-004), and auditing each change -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-SETTINGS-NOTIFICATIONS-API).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import NotFoundError
from app.models.tracker import TenantAuditLog, TenantNotificationSetting
from app.repositories import settings_audit_log as audit_log_repo
from app.repositories import settings_notifications as notifications_repo
from app.repositories.settings_notifications import EVENT_NAMES
from app.schemas.settings_notifications import (
    NotificationEventResponse,
    UpdateNotificationEventRequest,
)

UNKNOWN_EVENT_MESSAGE = "unknown notification event"


def _safe_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except (ValueError, TypeError):
        return uuid.UUID(int=0)


def _to_response(row: TenantNotificationSetting) -> NotificationEventResponse:
    return NotificationEventResponse(
        eventName=row.event_name,
        emailToggle=row.email_toggle,
        inAppToggle=row.in_app_toggle,
    )


def _require_known_name(event_name: str) -> None:
    if event_name not in EVENT_NAMES:
        raise NotFoundError(UNKNOWN_EVENT_MESSAGE)


def _log(db: Session, tenant_id: uuid.UUID, user: CurrentUser, details: str) -> None:
    now = datetime.now(timezone.utc)
    user_uuid = _safe_uuid(user.user_id)
    audit_log_repo.append(
        db,
        TenantAuditLog(
            tenant_id=tenant_id,
            log_date_time=now,
            log_user=user.role,
            log_action="Updated",
            log_entity="NotificationSetting",
            details=details,
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )


def list_notifications(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser
) -> list[NotificationEventResponse]:
    user_uuid = _safe_uuid(user.user_id)
    notifications_repo.ensure_seeded(db, tenant_id, user_uuid)
    # Commit unconditionally: ensure_seeded's inserts must survive past this request too, or
    # every GET would reseed against an empty table.
    db.commit()
    rows = notifications_repo.list_by_tenant(db, tenant_id)
    return [_to_response(row) for row in rows]


def update_notification(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    event_name: str,
    payload: UpdateNotificationEventRequest,
) -> NotificationEventResponse:
    _require_known_name(event_name)
    user_uuid = _safe_uuid(user.user_id)
    row = notifications_repo.get_by_name(db, tenant_id, event_name)
    if row is None:
        row = notifications_repo.insert(
            db,
            TenantNotificationSetting(
                tenant_id=tenant_id,
                event_name=event_name,
                email_toggle=True,
                in_app_toggle=True,
                created_by=user_uuid,
                updated_by=user_uuid,
            ),
        )

    if payload.emailToggle is not None:
        row.email_toggle = payload.emailToggle
    if payload.inAppToggle is not None:
        row.in_app_toggle = payload.inAppToggle

    row.updated_at = datetime.now(timezone.utc)
    row.updated_by = user_uuid
    _log(db, tenant_id, user, f"{event_name} notification settings updated")
    db.commit()
    return _to_response(row)
