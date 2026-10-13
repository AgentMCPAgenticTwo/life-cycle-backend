"""DTOs for `GET /api/v1/tracker/bottleneck-thresholds` -- see CLAUDE.md's
lifecycle-uc10-uc11 module section and TASK.md (T-TRACKER-BOTTLENECK-THRESHOLDS-API) for the
exact fields and enum.
"""
from typing import Literal

from pydantic import BaseModel

Stage = Literal["Drafting", "Negotiation", "Approval", "Signature"]


class BottleneckThresholdResponse(BaseModel):
    stage: Stage
    thresholdDays: int
