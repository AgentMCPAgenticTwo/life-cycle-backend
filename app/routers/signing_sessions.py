"""`/api/v1/signing-sessions/{sessionId}` -- thin HTTP binding over
`app.services.signing_sessions`. See CLAUDE.md's UC6-UC7-combined module section for the exact
paths, roles and DTOs this router must match. There is no `signing_sessions` table --
`sessionId` is the owning Signer row's id (see the service module for why no tenant-scoped
auth dependency is used here).
"""
import uuid

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.auth import CurrentUser, require_roles
from app.db import get_db
from app.schemas.signing_session import (
    ApplySignatureRequest,
    ApplySignatureResponse,
    DeclineSignatureRequest,
    DeclineSignatureResponse,
    SigningSessionResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.services import signing_sessions as signing_sessions_service

router = APIRouter(prefix="/signing-sessions", tags=["signing-sessions"])


@router.get("/{sessionId}", response_model=SigningSessionResponse)
def get_session(
    sessionId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("SIGNER")),
    db: Session = Depends(get_db),
) -> SigningSessionResponse:
    return signing_sessions_service.get_session(db, user, sessionId)


@router.post("/{sessionId}/otp/verify", response_model=VerifyOtpResponse)
def verify_otp(
    sessionId: uuid.UUID,
    payload: VerifyOtpRequest,
    user: CurrentUser = Depends(require_roles("SIGNER")),
    db: Session = Depends(get_db),
) -> VerifyOtpResponse:
    return signing_sessions_service.verify_otp(db, user, sessionId, payload)


@router.post("/{sessionId}/otp/resend", response_model=SigningSessionResponse)
def resend_otp(
    sessionId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("SIGNER", "CONTRACT_OWNER")),
    db: Session = Depends(get_db),
) -> SigningSessionResponse:
    return signing_sessions_service.resend_otp(db, user, sessionId)


@router.post("/{sessionId}/sign", response_model=ApplySignatureResponse)
def apply_signature(
    sessionId: uuid.UUID,
    payload: ApplySignatureRequest,
    request: Request,
    user: CurrentUser = Depends(require_roles("SIGNER")),
    db: Session = Depends(get_db),
) -> ApplySignatureResponse:
    ip_address = request.client.host if request.client else None
    return signing_sessions_service.apply_signature(db, user, sessionId, payload, ip_address)


@router.post("/{sessionId}/decline", response_model=DeclineSignatureResponse)
def decline_signature(
    sessionId: uuid.UUID,
    payload: DeclineSignatureRequest,
    user: CurrentUser = Depends(require_roles("SIGNER")),
    db: Session = Depends(get_db),
) -> DeclineSignatureResponse:
    return signing_sessions_service.decline_signature(db, user, sessionId, payload)
