"""Wire-format request/response types for the `approvals` resource (see CLAUDE.md's
UC6-UC7-combined module section). Field names are camelCase and match the contract's
`ApprovalResponse`, `ApprovalListItemResponse`, `ApprovalListResponse`,
`ApprovalActionRequest`, `ApprovalActionResponse`, `DelegateRequest`, `DelegateResponse`,
`ApprovalHistoryEntryResponse` and `ApprovalHistoryListResponse` DTOs exactly.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ApprovalListItemResponse(BaseModel):
    id: uuid.UUID
    contractId: uuid.UUID
    contractTitle: str
    contractType: str
    contractValue: Decimal
    counterpartyName: str
    keyTermsSummary: str | None = None
    deviationsFromStandard: str | None = None
    aiRiskScore: int | None = None
    approvalMatrixStepLabel: str
    status: str


class ApprovalListResponse(BaseModel):
    items: list[ApprovalListItemResponse]
    page: int
    pageSize: int
    totalCount: int
    isEmpty: bool
    emptyMessage: str | None = None


class ApprovalResponse(BaseModel):
    id: uuid.UUID
    contractId: uuid.UUID
    contractTitle: str
    contractType: str
    contractValue: Decimal
    counterpartyName: str
    keyTermsSummary: str | None = None
    deviationsFromStandard: str | None = None
    aiRiskScore: int | None = None
    approvalMatrixStepLabel: str
    approvalMatrixStepNumber: int
    approvalMatrixTotalSteps: int
    status: str
    comments: str | None = None
    delegateToUserId: uuid.UUID | None = None
    delegateToName: str | None = None
    delegationStartDate: date | None = None
    delegationEndDate: date | None = None
    currentApproverId: uuid.UUID
    currentApproverName: str
    isCurrentUserApprover: bool
    isCurrentUserActiveDelegate: bool
    isStepActionable: bool
    canApprove: bool
    canReject: bool
    canSendBack: bool
    canDelegate: bool
    createdAt: datetime
    updatedAt: datetime


class ApprovalActionRequest(BaseModel):
    actionType: str
    comments: str | None = None


class ApprovalActionResponse(BaseModel):
    approvalId: uuid.UUID
    status: str
    approvalMatrixStepLabel: str
    approvalMatrixStepNumber: int
    contractStatus: str


class DelegateRequest(BaseModel):
    delegateToUserId: uuid.UUID
    startDate: date
    endDate: date


class DelegateResponse(BaseModel):
    id: uuid.UUID
    approvalId: uuid.UUID
    delegateToUserId: uuid.UUID
    delegateToName: str
    startDate: date
    endDate: date
    createdBy: uuid.UUID
    createdAt: datetime


class ApprovalHistoryEntryResponse(BaseModel):
    id: uuid.UUID
    approvalId: uuid.UUID
    contractTitle: str
    contractType: str
    contractValue: Decimal
    counterpartyName: str
    keyTermsSummary: str | None = None
    deviationsFromStandard: str | None = None
    aiRiskScore: int | None = None
    approvalMatrixStepLabel: str
    action: str
    actorId: uuid.UUID
    actorName: str
    actorRole: str
    actingAsDelegateForUserId: uuid.UUID | None = None
    delegateToUserId: uuid.UUID | None = None
    delegateToName: str | None = None
    priorState: str
    newState: str
    comments: str | None = None
    timestamp: datetime


class ApprovalHistoryListResponse(BaseModel):
    items: list[ApprovalHistoryEntryResponse]
    page: int
    pageSize: int
    totalCount: int
