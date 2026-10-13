"""DTOs for `/api/v1/tracker/turnaround` -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-TRACKER-TURNAROUND-API) for the exact fields.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Literal

from fastapi import Query
from pydantic import BaseModel

PERIODS = ("Daily", "Weekly", "Monthly")

EstimatedTurnaroundSource = Literal["UC2_TARGET_COMPLETION_DATE", "AI_SUGGESTED", "NOT_SET"]
VarianceColor = Literal["RED", "GREEN"]


class TrackerQueryParams:
    """Binds `TrackerQueryParams` as GET query parameters (camelCase on the wire)."""

    def __init__(
        self,
        period: str | None = Query(None),
        contractTypeFilter: str | None = Query(None),
        ownerFilter: str | None = Query(None),
        dateRangeFrom: str | None = Query(None),
        dateRangeTo: str | None = Query(None),
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=200),
    ) -> None:
        self.period = period
        self.contract_type_filter = contractTypeFilter
        self.owner_filter = ownerFilter
        self.date_range_from = dateRangeFrom
        self.date_range_to = dateRangeTo
        self.page = page
        self.page_size = pageSize

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class TurnaroundRowResponse(BaseModel):
    contractId: uuid.UUID
    contractName: str
    contractType: str
    estimatedTurnaround: Decimal | None = None
    estimatedTurnaroundNotSet: bool
    estimatedTurnaroundSource: EstimatedTurnaroundSource | None = None
    actualTurnaround: Decimal | None = None
    variance: Decimal | None = None
    varianceColor: VarianceColor | None = None
    excludedFromAverages: bool


class TurnaroundTabResponse(BaseModel):
    rows: list[TurnaroundRowResponse]
    isEmpty: bool
    emptyStateMessage: str | None = None
    totalCount: int
    page: int
    pageSize: int


class EstimatedTurnaroundOverrideRequest(BaseModel):
    newEstimatedTurnaround: Decimal
    overrideReason: str | None = None
    originalAiSuggestedValue: Decimal | None = None
    overriddenBy: uuid.UUID
    overrideTimestamp: datetime
