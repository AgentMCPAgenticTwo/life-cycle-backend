"""DTOs for `POST /api/v1/tracker/export` -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-TRACKER-EXPORT-API) for the exact fields.
"""
from pydantic import BaseModel

TABS = ("Ownership", "CycleTime", "Bottleneck", "Turnaround")
FORMATS = ("Excel", "PDF")


class TrackerExportRequest(BaseModel):
    tab: str
    format: str
    period: str | None = None
    contractTypeFilter: str | None = None
    ownerFilter: str | None = None
    dateRangeFrom: str | None = None
    dateRangeTo: str | None = None


class TrackerExportResponse(BaseModel):
    success: bool
    fileUrl: str | None = None
    failureMessage: str | None = None
