"""DTOs for `/api/v1/settings/audit-log` -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-SETTINGS-AUDIT-LOG-API) for the exact fields.

`AuditLogListResponse` is not named in context.json (only the single-entry
`AuditLogEntryResponse` is) but the endpoint is marked `is_paged: true`, so a paged wrapper
is required per CLAUDE.md's "Paged endpoints ... return the contract's paged response
shape" -- this mirrors the items/page/pageSize/totalCount shape already used by the other
paged list responses in this module (e.g. ApprovalRuleListResponse). Recorded in blockers.
"""
import uuid
from datetime import date, datetime
from typing import Literal

from fastapi import Query
from pydantic import BaseModel

LogAction = Literal["Created", "Updated", "Deleted"]


class AuditLogEntryResponse(BaseModel):
    id: uuid.UUID
    logDateTime: datetime
    logUser: str
    logAction: LogAction
    logEntity: str
    details: str | None = None


class AuditLogListResponse(BaseModel):
    items: list[AuditLogEntryResponse]
    page: int
    pageSize: int
    totalCount: int


class AuditLogQueryParams:
    def __init__(
        self,
        filterDateRangeFrom: date | None = Query(None),
        filterDateRangeTo: date | None = Query(None),
        userFilter: str | None = Query(None),
        actionTypeFilter: str | None = Query(None),
        page: int = Query(1, ge=1),
        pageSize: int = Query(20, ge=1, le=200),
    ) -> None:
        self.filter_date_range_from = filterDateRangeFrom
        self.filter_date_range_to = filterDateRangeTo
        self.user_filter = userFilter
        self.action_type_filter = actionTypeFilter
        self.page = max(page, 1)
        self.page_size = max(min(pageSize, 200), 1)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
