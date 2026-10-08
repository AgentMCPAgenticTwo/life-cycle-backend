"""Wire-format request/response types for the `templates` resource (see CLAUDE.md's uc123
module section). Field names are camelCase and match the contract's `TemplateResponse`,
`TemplateListResponse`, `CreateTemplateRequest`, `UpdateTemplateRequest`,
`VersionHistoryItemResponse` and `VersionHistoryResponse` DTOs exactly.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TemplateStatus = Literal["Draft", "Active", "Inactive"]


class TemplateResponse(BaseModel):
    id: uuid.UUID
    templateName: str
    templateCategory: str
    documentFormat: str
    templateBody: str
    status: TemplateStatus
    lastModifiedBy: str
    lastModifiedDate: datetime


class TemplateListResponse(BaseModel):
    items: list[TemplateResponse]


class CreateTemplateRequest(BaseModel):
    templateName: str = Field(max_length=150)
    templateCategory: str = Field(max_length=100)
    # Not a Literal: UC3-AF-005 requires the exact message 'Unsupported file format. Please
    # upload a PDF or DOCX file.' for a non-PDF/DOCX value, which a Pydantic Literal would
    # instead surface as a generic 400 from the shared RequestValidationError handler. Kept
    # as `str` so app.services.templates can raise that specific business-rule error.
    documentFormat: str
    templateBody: str


class UpdateTemplateRequest(BaseModel):
    templateName: str = Field(max_length=150)
    templateCategory: str = Field(max_length=100)
    documentFormat: str
    templateBody: str
    # Added field, not in context.json's UpdateTemplateRequest -- see T-TEMPLATES-API output
    # `blockers`. UC3-AF-006 requires detecting a conflicting concurrent save, but the
    # contract gives the client no way to say which version it started from. Optional so a
    # caller that omits it (e.g. generated frontend code unaware of this field) still works;
    # when present it is compared against the template's current version before saving.
    expectedVersion: int | None = None


class VersionHistoryItemResponse(BaseModel):
    versionNumber: int
    changedBy: str
    dateChanged: datetime
    changeSummary: str | None = None


class VersionHistoryResponse(BaseModel):
    items: list[VersionHistoryItemResponse]
