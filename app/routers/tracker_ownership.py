"""`/api/v1/tracker/ownership` -- thin HTTP binding over `app.services.tracker_ownership`.
See CLAUDE.md's lifecycle-uc10-uc11 module section and TASK.md (T-TRACKER-OWNERSHIP-API)
for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.tracker_ownership import OwnershipTabResponse, TrackerQueryParams
from app.services import tracker_ownership as ownership_service

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.get("/ownership", response_model=OwnershipTabResponse)
def get_ownership_tab(
    params: TrackerQueryParams = Depends(),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> OwnershipTabResponse:
    return ownership_service.get_ownership_tab(db, tenant_id, user, params)
