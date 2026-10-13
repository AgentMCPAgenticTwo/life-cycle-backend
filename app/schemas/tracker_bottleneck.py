"""DTOs for `GET /api/v1/tracker/bottleneck` -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-TRACKER-BOTTLENECK-API) for the exact fields.
"""
import uuid

from fastapi import Query
from pydantic import BaseModel

PERIODS = ("Daily", "Weekly", "Monthly")


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


class BottleneckRowResponse(BaseModel):
    contractId: uuid.UUID
    contractName: str
    ownerName: str | None = None
    currentStage: str
    daysInCurrentStage: int
    stuckFlag: str


class BottleneckTabResponse(BaseModel):
    rows: list[BottleneckRowResponse]
    isEmpty: bool
    emptyStateMessage: str | None = None
    totalCount: int
    page: int
    pageSize: int
