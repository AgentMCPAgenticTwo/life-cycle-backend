"""`/api/v1/tracker/cycle-time` -- thin HTTP binding over `app.services.tracker_cycle_time`.
See CLAUDE.md's lifecycle-uc10-uc11 module section and TASK.md (T-TRACKER-CYCLE-TIME-API)
for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.tracker_cycle_time import CycleTimeTabResponse, TrackerQueryParams
from app.services import tracker_cycle_time as cycle_time_service

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.get("/cycle-time", response_model=CycleTimeTabResponse)
def get_cycle_time_tab(
    params: TrackerQueryParams = Depends(),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> CycleTimeTabResponse:
    return cycle_time_service.get_cycle_time_tab(db, tenant_id, user, params)
