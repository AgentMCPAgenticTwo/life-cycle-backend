"""DTOs for `/api/v1/auth/*`. Field names are taken verbatim from the frontend contract
(`LoginResponse`, `AuthUserResponse`) -- a renamed field here is a 200 with blank values on
screen, not a visible error.
"""
import uuid

from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str | None = None
    password: str | None = None


class AuthUserResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    tenantId: uuid.UUID
    mustChangePassword: bool


class LoginResponse(BaseModel):
    accessToken: str
    user: AuthUserResponse


class RefreshResponse(BaseModel):
    accessToken: str


class ChangePasswordRequest(BaseModel):
    currentPassword: str | None = None
    newPassword: str | None = None
