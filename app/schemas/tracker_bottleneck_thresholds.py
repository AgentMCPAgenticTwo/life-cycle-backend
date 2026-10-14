"""DTOs for `GET`/`PUT /api/v1/tracker/bottleneck-thresholds` -- see CLAUDE.md's
lifecycle-uc10-uc11 module section and TASK.md (T-TRACKER-BOTTLENECK-THRESHOLDS-API) for the
exact fields and enum.
"""
from typing import Literal

from pydantic import BaseModel

Stage = Literal["Drafting", "Negotiation", "Approval", "Signature"]


class BottleneckThresholdResponse(BaseModel):
    stage: Stage
    thresholdDays: int


class UpdateBottleneckThresholdRequest(BaseModel):
    """One entry of the bare array the PUT accepts. Both fields are optional/untyped here on
    purpose: UC10 requires a named stage message and a "positive whole number of days"
    message, raised by app.services.tracker_bottleneck_thresholds, rather than a generic
    Pydantic error from this layer.
    """

    stage: str | None = None
    thresholdDays: int | float | str | None = None
