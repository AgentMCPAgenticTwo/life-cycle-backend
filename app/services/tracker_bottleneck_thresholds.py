"""Business rules for `GET`/`PUT /api/v1/tracker/bottleneck-thresholds` (UC10-BR-002): returns the
tenant-configured stuck-flag threshold for each of the four trackable stages, falling back to
the documented defaults (Drafting/Negotiation 5 days, Approval/Signature 3 days) for any stage
the tenant has not overridden. Reuses `app.repositories.tracker_bottleneck.get_thresholds`,
which already merges tenant overrides over the defaults for the Bottleneck tab itself -- this
endpoint is the read surface a Tenant Admin uses to see/confirm that same configuration.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ValidationFailedError
from app.models.tracker import TenantAuditLog, TenantBottleneckThreshold
from app.repositories import settings_audit_log as audit_log_repo
from app.repositories import tracker_bottleneck as repo
from app.schemas.tracker_bottleneck_thresholds import (
    BottleneckThresholdResponse,
    UpdateBottleneckThresholdRequest,
)

# Fixed display order: Drafting/Negotiation share the 5-day default tier, Approval/Signature
# share the 3-day tier (UC10-BR-002 acceptance criteria).
STAGE_ORDER = ("Drafting", "Negotiation", "Approval", "Signature")

STAGE_MESSAGE = f"Stage must be one of: {', '.join(STAGE_ORDER)}."
THRESHOLD_DAYS_MESSAGE = "Threshold days must be a positive whole number."


def get_bottleneck_thresholds(db: Session, tenant_id: uuid.UUID) -> list[BottleneckThresholdResponse]:
    thresholds = repo.get_thresholds(db, tenant_id)
    return [
        BottleneckThresholdResponse(stage=stage, thresholdDays=thresholds.get(stage, repo.DEFAULT_THRESHOLDS[stage]))
        for stage in STAGE_ORDER
    ]


def _coerce_days(value: int | float | str | None) -> int:
    """Positive whole numbers of days only -- 0, a negative, a fraction or a non-number is a
    400, not a silently-clamped threshold that would mis-flag every contract in the stage.
    """
    if isinstance(value, bool) or value is None:
        raise ValidationFailedError(THRESHOLD_DAYS_MESSAGE, details=[THRESHOLD_DAYS_MESSAGE])
    try:
        days = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValidationFailedError(THRESHOLD_DAYS_MESSAGE, details=[THRESHOLD_DAYS_MESSAGE])
    if days <= 0:
        raise ValidationFailedError(THRESHOLD_DAYS_MESSAGE, details=[THRESHOLD_DAYS_MESSAGE])
    return days


def update_bottleneck_thresholds(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    payload: list[UpdateBottleneckThresholdRequest],
) -> list[BottleneckThresholdResponse]:
    """Saves the per-stage stuck-flag thresholds a Tenant Admin edits. The whole array is
    validated before anything is written, so a single bad row leaves the configuration
    untouched; the Bottleneck tab reads the new values on its next request, since it derives
    the stuck flag from these rows rather than from a stored flag.
    """
    if not payload:
        raise ValidationFailedError(STAGE_MESSAGE, details=[STAGE_MESSAGE])

    validated: dict[str, int] = {}
    for entry in payload:
        stage = (entry.stage or "").strip()
        if stage not in STAGE_ORDER:
            raise ValidationFailedError(STAGE_MESSAGE, details=[STAGE_MESSAGE])
        validated[stage] = _coerce_days(entry.thresholdDays)

    now = datetime.now(timezone.utc)
    user_uuid = uuid.UUID(user.user_id)
    changes: list[str] = []
    for stage, days in validated.items():
        row = repo.find_threshold(db, tenant_id, stage)
        if row is None:
            repo.insert_threshold(
                db,
                TenantBottleneckThreshold(
                    tenant_id=tenant_id,
                    stage=stage,
                    threshold_days=days,
                    created_by=user_uuid,
                    updated_by=user_uuid,
                    created_at=now,
                    updated_at=now,
                ),
            )
            changes.append(f"{stage}: {repo.DEFAULT_THRESHOLDS[stage]} -> {days}")
        else:
            if row.threshold_days != days:
                changes.append(f"{stage}: {row.threshold_days} -> {days}")
            row.threshold_days = days
            row.updated_by = user_uuid
            row.updated_at = now

    if changes:
        audit_log_repo.append(
            db,
            TenantAuditLog(
                tenant_id=tenant_id,
                log_date_time=now,
                log_user=user.role,
                log_action="Updated",
                log_entity="Bottleneck Threshold",
                details="; ".join(changes),
                created_by=user_uuid,
                updated_by=user_uuid,
            ),
        )
    db.commit()
    return get_bottleneck_thresholds(db, tenant_id)
