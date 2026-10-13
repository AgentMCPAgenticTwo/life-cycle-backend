"""DTOs for `/api/v1/settings/notifications` -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-SETTINGS-NOTIFICATIONS-API) for the exact fields.
"""
from pydantic import BaseModel


class NotificationEventResponse(BaseModel):
    eventName: str
    emailToggle: bool
    inAppToggle: bool


class UpdateNotificationEventRequest(BaseModel):
    emailToggle: bool | None = None
    inAppToggle: bool | None = None
