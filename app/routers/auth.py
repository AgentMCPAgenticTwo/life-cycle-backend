"""`/api/v1/auth/*` -- thin HTTP binding over `app.services.auth`.

The access token goes back in the response body (the SPA keeps it in memory); the refresh
token only ever lives in an httpOnly cookie, so script running on the page cannot read it.
"""
import uuid

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_user
from app.config import settings
from app.db import get_db
from app.repositories import auth as auth_repo
from app.schemas.auth import (
    AuthUserResponse,
    ChangePasswordRequest,
    LoginRequest,
    LoginResponse,
    RefreshResponse,
)
from app.services import auth as auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _set_refresh_cookie(response: Response, raw_token: str) -> None:
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_token,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite="lax",
        max_age=settings.refresh_token_ttl_days * 24 * 60 * 60,
        path="/",
    )


@router.post("/login", response_model=LoginResponse)
def login(
    payload: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
) -> LoginResponse:
    result, refresh_raw = auth_service.login(db, payload.email, payload.password)
    _set_refresh_cookie(response, refresh_raw)
    return result


@router.post("/refresh", response_model=RefreshResponse)
def refresh(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> RefreshResponse:
    raw = request.cookies.get(settings.refresh_cookie_name)
    access, new_refresh = auth_service.refresh(db, raw)
    _set_refresh_cookie(response, new_refresh)
    return RefreshResponse(accessToken=access)


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> None:
    auth_service.logout(db, request.cookies.get(settings.refresh_cookie_name))
    response.delete_cookie(settings.refresh_cookie_name, path="/")


@router.get("/me", response_model=AuthUserResponse)
def me(
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> AuthUserResponse:
    row = auth_repo.find_user_by_id(db, uuid.UUID(user.user_id))
    return auth_service.to_auth_user(row)


@router.post("/change-password", status_code=204)
def change_password(
    payload: ChangePasswordRequest,
    response: Response,
    user: CurrentUser = Depends(current_user),
    db: Session = Depends(get_db),
) -> None:
    replacement = auth_service.change_password(
        db, uuid.UUID(user.user_id), payload.currentPassword, payload.newPassword
    )
    _set_refresh_cookie(response, replacement)
