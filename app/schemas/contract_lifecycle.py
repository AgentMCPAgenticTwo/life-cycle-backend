"""Wire-format request/response types for the life-cycle-uc8-uc9 module (`/api/v1/contracts`
document/versions/activity-log/folder-tags/obligations/renewal sub-resources, plus the
tenant-level `/api/v1/folder-tags` lookup). Field names are camelCase and match this task's
`context.json` DTOs exactly.

`ContractSearchRequest`, `ContractListItemResponse` and `ContractDetailResponse` are
deliberately NOT defined here -- see this task's `blockers` for why `GET /api/v1/contracts`
and `GET /api/v1/contracts/{contractId}` are not implemented by this module.
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ContractDocumentResponse(BaseModel):
    contractId: uuid.UUID
    documentUrl: str | None = None
    fileName: str
    fileType: str
    fileSizeBytes: int
    isOversized: bool
    isCorruptedOrMissing: bool
    downloadEnabled: bool
    unavailableComment: str | None = None


class DocumentDownloadResponse(BaseModel):
    success: bool
    fileUrl: str | None = None
    errorMessage: str | None = None


class ContractVersionResponse(BaseModel):
    versionId: uuid.UUID
    versionNumber: int
    createdAt: datetime
    createdBy: str
    changeSummary: str | None = None


class ContractVersionListResponse(BaseModel):
    items: list[ContractVersionResponse]
    page: int
    pageSize: int
    totalCount: int


class ActivityLogEntryResponse(BaseModel):
    entryId: uuid.UUID
    contractId: uuid.UUID
    actionType: str
    performedBy: str
    performedAt: datetime
    details: str | None = None


class ActivityLogListResponse(BaseModel):
    items: list[ActivityLogEntryResponse]
    page: int
    pageSize: int
    totalCount: int


class AssignFolderTagRequest(BaseModel):
    folderTagIds: list[uuid.UUID]


class CreateFolderTagRequest(BaseModel):
    name: str
    kind: str


class FolderTagOptionResponse(BaseModel):
    id: uuid.UUID
    name: str
    kind: str


class ContractFolderTagResponse(BaseModel):
    contractId: uuid.UUID
    folderTags: list[FolderTagOptionResponse]


class ObligationResponse(BaseModel):
    obligationId: uuid.UUID
    contractId: uuid.UUID
    obligationDescription: str
    obligationType: str
    owner: str | None = None
    dueDate: date | None = None
    status: str
    source: str
    confirmationLabel: str
    evidenceReference: str | None = None
    readOnly: bool


class ObligationListResponse(BaseModel):
    items: list[ObligationResponse]
    page: int
    pageSize: int
    totalCount: int


class CreateObligationRequest(BaseModel):
    obligationDescription: str
    obligationType: str
    owner: str
    dueDate: date
    status: str


class UpdateObligationRequest(BaseModel):
    obligationDescription: str | None = None
    obligationType: str | None = None
    owner: str | None = None
    dueDate: date | None = None
    status: str | None = None
    evidenceReference: str | None = None


class RenewalPanelResponse(BaseModel):
    contractId: uuid.UUID
    renewalAlertBanner: str | None = None
    contractEndDate: date | None = None
    noticePeriod: str | None = None
    alertThresholdDays: int | None = None
    renewEnabled: bool
    amendEnabled: bool
    terminateEnabled: bool
    actionInProgress: bool
    linkedContractId: uuid.UUID | None = None
    linkedContractRelation: str | None = None
    obligations: list[ObligationResponse] | None = None
    terminationReason: str | None = None
    effectiveTerminationDate: date | None = None


class TerminateContractRequest(BaseModel):
    terminationReason: str
    effectiveTerminationDate: date


class LinkedContractActionResponse(BaseModel):
    originalContractId: uuid.UUID
    originalContractStatus: str
    linkedContractId: uuid.UUID
    linkedContractReference: uuid.UUID
    terminationReason: str | None = None
    effectiveTerminationDate: date | None = None
    contractEndDate: date | None = None
    noticePeriod: str | None = None
    renewalAlertBanner: str | None = None
    obligations: list[ObligationResponse] | None = None
