"""Wire-format request/response types for the `lifecycle-uc4-uc5` module's AI Clause
Analysis endpoints (`/api/v1/lifecycle/contracts/{contractId}/...`). Field names are
camelCase and match the contract's `ClauseResponse`, `ContractMetadataResponse`,
`ClauseAnalysisResponse`, `EditClauseRequest`, `RejectClauseRequest`, `UpdateMetadataRequest`,
`AskAIRequest`, `AskAIResponse`, `AuditLogEntryResponse`, `PagedAuditLogResponse` and
`ProceedToNegotiationResponse` DTOs exactly.
"""
import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ClauseResponse(BaseModel):
    clauseId: uuid.UUID
    clauseText: str
    clauseCategory: str | None = None
    libraryMatchStatus: str
    riskScore: str
    aiExplanation: str | None = None
    suggestedText: str | None = None
    status: str
    isMandatory: bool
    mandatoryClauseFlag: bool
    mandatoryClauseFlagLabel: str | None = None
    version: int
    updatedAt: datetime
    updatedBy: uuid.UUID | None = None


class ContractMetadataResponse(BaseModel):
    parties: str | None = None
    partiesLabel: str
    contractValue: Decimal | None = None
    contractValueLabel: str
    startDate: date | None = None
    startDateLabel: str
    endDate: date | None = None
    endDateLabel: str
    renewalTerms: str | None = None
    renewalTermsLabel: str
    paymentTerms: str | None = None
    paymentTermsLabel: str
    keyObligations: str | None = None
    keyObligationsLabel: str


class ClauseAnalysisResponse(BaseModel):
    contractId: uuid.UUID
    fileFormatSupported: bool
    analysisStatus: str
    clauses: list[ClauseResponse]
    overallContractRiskScore: str
    metadata: ContractMetadataResponse | None = None
    proceedToNegotiationEnabled: bool
    askAiEnabled: bool


class EditClauseRequest(BaseModel):
    clauseText: str
    expectedVersion: int


class RejectClauseRequest(BaseModel):
    reason: str | None = None


class UpdateMetadataRequest(BaseModel):
    parties: str | None = None
    contractValue: Decimal | None = None
    startDate: date | None = None
    endDate: date | None = None
    renewalTerms: str | None = None
    paymentTerms: str | None = None
    keyObligations: str | None = None


class AskAIRequest(BaseModel):
    question: str


class AskAIResponse(BaseModel):
    answer: str
    disclaimer: str
    relatedClauseIds: list[uuid.UUID] | None = None


class AuditLogEntryResponse(BaseModel):
    id: uuid.UUID
    userId: uuid.UUID
    userName: str
    timestamp: datetime
    clauseId: uuid.UUID | None = None
    actionType: str
    fieldName: str | None = None
    beforeText: str | None = None
    afterText: str | None = None


class PagedAuditLogResponse(BaseModel):
    items: list[AuditLogEntryResponse]
    page: int
    pageSize: int
    totalCount: int


class ProceedToNegotiationResponse(BaseModel):
    contractId: uuid.UUID
    negotiationStatus: str
    routedAt: datetime | None = None
    clauses: list[ClauseResponse]
    overallContractRiskScore: str
    metadata: ContractMetadataResponse | None = None
    askAiAvailable: bool
