"""DTOs for `/api/v1/settings/users` -- see CLAUDE.md's lifecycle-uc10-uc11 module section
and TASK.md (T-SETTINGS-USERS-API) for the exact fields and enums.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

UserRole = Literal[
    "Tenant Admin", "Legal Reviewer", "Contract Owner", "Approver", "External Party", "Signer"
]
UserStatus = Literal["Invited", "Active", "Deactivated"]


class UserListItemResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    status: UserStatus
    lastLogin: datetime | None = None


class UserListResponse(BaseModel):
    items: list[UserListItemResponse]
    page: int
    pageSize: int
    totalCount: int


class CreateUserRequest(BaseModel):
    """Fields are optional/untyped here on purpose (mirrors
    app/schemas/settings_approval_rules.py): UC11-FV-001 requires a single "missing
    mandatory field(s)" style message for a blank Name/Email/Role, a dedicated email-format
    message, and a dedicated role-enum message -- all business-rule checks raised by
    app.services.settings_users, not generic Pydantic "field required" errors from this layer.
    """

    name: str | None = None
    email: str | None = None
    role: str | None = None
    # Optional: leave it empty and the API generates a strong one. Either way the user is
    # created with must_change_password set, so it is always a temporary credential.
    initialPassword: str | None = None


class CreateUserResponse(UserListItemResponse):
    """The create response is the list row plus the one-time temporary password. It is
    returned exactly once, at creation, so the admin can hand it over -- no later read of
    the user ever includes it again.
    """

    temporaryPassword: str | None = None


class ResetPasswordResponse(BaseModel):
    temporaryPassword: str


class UpdateUserStatusRequest(BaseModel):
    status: str | None = None
