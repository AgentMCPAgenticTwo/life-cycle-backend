"""`/api/v1/tracker/bottleneck-thresholds` -- thin HTTP binding over
`app.services.tracker_bottleneck_thresholds`. See CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-TRACKER-BOTTLENECK-THRESHOLDS-API) for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.tracker_bottleneck_thresholds import BottleneckThresholdResponse
from app.services import tracker_bottleneck_thresholds as thresholds_service

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.get("/bottleneck-thresholds", response_model=list[BottleneckThresholdResponse])
def get_bottleneck_thresholds(
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> list[BottleneckThresholdResponse]:
    return thresholds_service.get_bottleneck_thresholds(db, tenant_id)
