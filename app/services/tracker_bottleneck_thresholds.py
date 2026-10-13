"""Business rules for `GET /api/v1/tracker/bottleneck-thresholds` (UC10-BR-002): returns the
tenant-configured stuck-flag threshold for each of the four trackable stages, falling back to
the documented defaults (Drafting/Negotiation 5 days, Approval/Signature 3 days) for any stage
the tenant has not overridden. Reuses `app.repositories.tracker_bottleneck.get_thresholds`,
which already merges tenant overrides over the defaults for the Bottleneck tab itself -- this
endpoint is the read surface a Tenant Admin uses to see/confirm that same configuration.
"""
import uuid

from sqlalchemy.orm import Session

from app.repositories import tracker_bottleneck as repo
from app.schemas.tracker_bottleneck_thresholds import BottleneckThresholdResponse

# Fixed display order: Drafting/Negotiation share the 5-day default tier, Approval/Signature
# share the 3-day tier (UC10-BR-002 acceptance criteria).
STAGE_ORDER = ("Drafting", "Negotiation", "Approval", "Signature")


def get_bottleneck_thresholds(db: Session, tenant_id: uuid.UUID) -> list[BottleneckThresholdResponse]:
    thresholds = repo.get_thresholds(db, tenant_id)
    return [
        BottleneckThresholdResponse(stage=stage, thresholdDays=thresholds.get(stage, repo.DEFAULT_THRESHOLDS[stage]))
        for stage in STAGE_ORDER
    ]
