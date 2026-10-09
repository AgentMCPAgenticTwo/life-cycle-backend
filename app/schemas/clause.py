"""Wire-format request/response types for the `clauses` resource (see CLAUDE.md's uc123
module section). Field names are camelCase and match the contract's `ClauseResponse`,
`ClauseListResponse`, `CreateClauseRequest`, `UpdateClauseRequest`, `VersionHistoryItemResponse`
and `VersionHistoryResponse` DTOs exactly.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ClauseCategory = Literal["Confidentiality", "Liability", "Termination", "Payment Terms"]
RiskLevel = Literal["Low", "Medium", "High"]
ClauseStatus = Literal["Draft", "Active", "Inactive"]


class ClauseResponse(BaseModel):
    id: uuid.UUID
    clauseName: str
    clauseCategory: ClauseCategory
    standardText: str
    fallbackText1: str | None = None
    fallbackText2: str | None = None
    riskLevel: RiskLevel
    mandatory: bool
    status: ClauseStatus
    lastModifiedBy: str
    lastModifiedDate: datetime


class ClauseListResponse(BaseModel):
    items: list[ClauseResponse]


class CreateClauseRequest(BaseModel):
    clauseName: str = Field(max_length=150)
    clauseCategory: ClauseCategory
    standardText: str
    fallbackText1: str | None = None
    fallbackText2: str | None = None
    riskLevel: RiskLevel
    mandatory: bool


class UpdateClauseRequest(BaseModel):
    clauseName: str = Field(max_length=150)
    clauseCategory: ClauseCategory
    standardText: str
    fallbackText1: str | None = None
    fallbackText2: str | None = None
    riskLevel: RiskLevel
    mandatory: bool
    # Added field, not in context.json's UpdateClauseRequest -- see T-CLAUSES-API output
    # `blockers`. UC3-AF-006 requires detecting a conflicting concurrent save, but the
    # contract gives the client no way to say which version it started from. Optional so a
    # caller that omits it (e.g. generated frontend code unaware of this field) still works;
    # when present it is compared against the clause's current version before saving.
    expectedVersion: int | None = None


class VersionHistoryItemResponse(BaseModel):
    versionNumber: int
    changedBy: str
    dateChanged: datetime
    changeSummary: str | None = None


class VersionHistoryResponse(BaseModel):
    items: list[VersionHistoryItemResponse]
