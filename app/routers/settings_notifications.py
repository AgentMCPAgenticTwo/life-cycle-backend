"""`/api/v1/settings/notifications` -- thin HTTP binding over
`app.services.settings_notifications`. See CLAUDE.md's lifecycle-uc10-uc11 module section
and TASK.md (T-SETTINGS-NOTIFICATIONS-API) for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.settings_notifications import (
    NotificationEventResponse,
    UpdateNotificationEventRequest,
)
from app.services import settings_notifications as notifications_service

router = APIRouter(prefix="/settings/notifications", tags=["settings-notifications"])


@router.get("", response_model=list[NotificationEventResponse])
def list_notifications(
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> list[NotificationEventResponse]:
    return notifications_service.list_notifications(db, tenant_id, user)


@router.put("/{eventName}", response_model=NotificationEventResponse)
def update_notification(
    eventName: str,
    payload: UpdateNotificationEventRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> NotificationEventResponse:
    return notifications_service.update_notification(db, tenant_id, user, eventName, payload)
