"""`/api/v1/tracker/bottleneck` -- thin HTTP binding over `app.services.tracker_bottleneck`.
See CLAUDE.md's lifecycle-uc10-uc11 module section and TASK.md (T-TRACKER-BOTTLENECK-API)
for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.tracker_bottleneck import BottleneckTabResponse, TrackerQueryParams
from app.services import tracker_bottleneck as bottleneck_service

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.get("/bottleneck", response_model=BottleneckTabResponse)
def get_bottleneck_tab(
    params: TrackerQueryParams = Depends(),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> BottleneckTabResponse:
    return bottleneck_service.get_bottleneck_tab(db, tenant_id, user, params)
