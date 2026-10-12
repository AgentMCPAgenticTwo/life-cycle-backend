"""`/api/v1/lifecycle/contracts/{contractId}/negotiation/...` and
`/api/v1/lifecycle/negotiation/external/{linkToken}/...` -- thin HTTP binding over
`app.services.lifecycle_negotiation`. See CLAUDE.md's lifecycle-uc4-uc5 module section for the
exact paths, roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.lifecycle_negotiation import (
    CommentRequest,
    CommentResponse,
    CompareVersionsResponse,
    ExternalSubmitRequest,
    ExternalSubmitResponse,
    GenerateExternalLinkResponse,
    MarkAgreedResponse,
    NegotiationTrackerResponse,
    ReminderResponse,
    RoutingRequest,
    RoutingResponse,
    SubmitReviewRequest,
    SubmitReviewResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)
from app.services import lifecycle_negotiation as service

router = APIRouter(prefix="/lifecycle/contracts/{contractId}/negotiation", tags=["lifecycle-negotiation"])
external_router = APIRouter(prefix="/lifecycle/negotiation/external/{linkToken}", tags=["lifecycle-negotiation-external"])


@router.post("/routing", response_model=RoutingResponse)
def create_routing(
    contractId: uuid.UUID,
    payload: RoutingRequest,
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> RoutingResponse:
    return service.create_routing(db, tenant_id, user, contractId, payload)


@router.get("", response_model=NegotiationTrackerResponse)
def get_tracker(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER", "TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> NegotiationTrackerResponse:
    return service.get_tracker(db, tenant_id, contractId)


@router.post("/reviews", response_model=SubmitReviewResponse)
def submit_review(
    contractId: uuid.UUID,
    payload: SubmitReviewRequest,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> SubmitReviewResponse:
    return service.submit_review(db, tenant_id, user, contractId, payload)


@router.post("/external-link", response_model=GenerateExternalLinkResponse)
def generate_external_link(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER", "LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> GenerateExternalLinkResponse:
    return service.generate_external_link(db, tenant_id, user, contractId)


@router.get("/compare", response_model=CompareVersionsResponse)
def compare_versions(
    contractId: uuid.UUID,
    versionA: int = Query(...),
    versionB: int = Query(...),
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> CompareVersionsResponse:
    return service.compare_versions(db, tenant_id, contractId, versionA, versionB)


@router.post("/reminder", response_model=ReminderResponse)
def send_reminder(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ReminderResponse:
    return service.send_reminder(db, tenant_id, user, contractId)


@router.post("/mark-agreed", response_model=MarkAgreedResponse)
def mark_agreed(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> MarkAgreedResponse:
    return service.mark_agreed(db, tenant_id, user, contractId)


@router.post("/comments", response_model=CommentResponse)
def add_comment(
    contractId: uuid.UUID,
    payload: CommentRequest,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER", "APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> CommentResponse:
    return service.add_comment(db, tenant_id, user, contractId, payload)


@external_router.post("/verify-otp", response_model=VerifyOtpResponse)
def verify_otp(
    linkToken: str,
    payload: VerifyOtpRequest,
    db: Session = Depends(get_db),
) -> VerifyOtpResponse:
    """T-LIFECYCLE-NEGOTIATION-API's endpoint table marks this `auth_required: no` -- the
    External Party has no system account/header identity, only the secure link token plus
    OTP, so no X-User-Role/X-User-Id is required or checked here (see that task's blockers
    for the conflict with the generic "roles enforced via header" guidance)."""
    return service.verify_otp(db, linkToken, payload)


@external_router.post("/submit", response_model=ExternalSubmitResponse)
def external_submit(
    linkToken: str,
    payload: ExternalSubmitRequest,
    db: Session = Depends(get_db),
) -> ExternalSubmitResponse:
    return service.external_submit(db, linkToken, payload)
