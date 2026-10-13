"""`/api/v1/tracker/turnaround` -- thin HTTP binding over `app.services.tracker_turnaround`.
See CLAUDE.md's lifecycle-uc10-uc11 module section and TASK.md (T-TRACKER-TURNAROUND-API)
for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.tracker_turnaround import (
    EstimatedTurnaroundOverrideRequest,
    TrackerQueryParams,
    TurnaroundRowResponse,
    TurnaroundTabResponse,
)
from app.services import tracker_turnaround as turnaround_service

router = APIRouter(prefix="/tracker", tags=["tracker"])

ALLOWED_ROLES = ("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")


@router.get("/turnaround", response_model=TurnaroundTabResponse)
def get_turnaround_tab(
    params: TrackerQueryParams = Depends(),
    user: CurrentUser = Depends(require_roles(*ALLOWED_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> TurnaroundTabResponse:
    return turnaround_service.get_turnaround_tab(db, tenant_id, user, params)


@router.put("/turnaround/{contractId}/estimated-override", response_model=TurnaroundRowResponse)
def override_estimated_turnaround(
    contractId: uuid.UUID,
    payload: EstimatedTurnaroundOverrideRequest,
    user: CurrentUser = Depends(require_roles(*ALLOWED_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> TurnaroundRowResponse:
    return turnaround_service.override_estimated_turnaround(db, tenant_id, user, contractId, payload)
