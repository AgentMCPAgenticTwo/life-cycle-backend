"""`/api/v1/settings/users` -- thin HTTP binding over `app.services.settings_users`. See
CLAUDE.md's lifecycle-uc10-uc11 module section and TASK.md (T-SETTINGS-USERS-API) for the
exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.pagination import PageParams
from app.schemas.settings_users import CreateUserRequest, UserListItemResponse, UserListResponse, UpdateUserStatusRequest
from app.services import settings_users as users_service

router = APIRouter(prefix="/settings/users", tags=["settings-users"])


@router.get("", response_model=UserListResponse)
def list_users(
    page_params: PageParams = Depends(),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> UserListResponse:
    return users_service.list_users(db, tenant_id, page_params)


@router.post("", response_model=UserListItemResponse, status_code=201)
def create_user(
    payload: CreateUserRequest,
    response: Response,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> UserListItemResponse:
    result = users_service.create_user(db, tenant_id, user, payload)
    response.headers["Location"] = f"/api/v1/settings/users/{result.id}"
    return result


@router.patch("/{userId}/status", response_model=UserListItemResponse)
def update_user_status(
    userId: uuid.UUID,
    payload: UpdateUserStatusRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> UserListItemResponse:
    return users_service.update_user_status(db, tenant_id, user, userId, payload)
