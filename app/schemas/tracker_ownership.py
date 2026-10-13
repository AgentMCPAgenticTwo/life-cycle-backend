"""DTOs for `GET /api/v1/tracker/ownership` -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-TRACKER-OWNERSHIP-API) for the exact fields.
"""
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


class OwnershipRowResponse(BaseModel):
    ownerName: str
    contractsOwned: int
    inDraftCount: int
    inNegotiationCount: int
    inApprovalCount: int
    inSignatureCount: int
    completedCount: int
    averageCycleTime: float | None = None


class OwnershipTabResponse(BaseModel):
    rows: list[OwnershipRowResponse]
    isEmpty: bool
    emptyStateMessage: str | None = None
    totalCount: int
    page: int
    pageSize: int
