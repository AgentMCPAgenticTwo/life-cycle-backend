"""Wire-format request/response types for the dashboard and lookup endpoints (see CLAUDE.md's
uc123 module section). Field names are camelCase and match this task's DashboardSummaryResponse,
MyTasksResponse, HighRiskContractsResponse, DashboardFilterOptionsResponse and
UserOptionListResponse DTOs exactly.
"""
import uuid
from datetime import date
from typing import Literal

from pydantic import BaseModel

from app.schemas.contract import ContractStatus

UserRole = Literal[
    "TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER", "SIGNER", "EXTERNAL_PARTY"
]


class DashboardSummaryResponse(BaseModel):
    totalContractsCount: int
    inDraftCount: int
    inNegotiationCount: int
    pendingApprovalCount: int
    pendingSignatureCount: int
    executedCount: int
    expiring30DaysCount: int
    expiring60DaysCount: int
    expiring90DaysCount: int
    noContractsMessage: str | None = None
    noMatchMessage: str | None = None


class MyTaskItemResponse(BaseModel):
    contractId: uuid.UUID
    contractName: str
    counterparty: str
    status: ContractStatus
    dueDate: date


class MyTasksResponse(BaseModel):
    items: list[MyTaskItemResponse]
    emptyMessage: str | None = None


class HighRiskContractResponse(BaseModel):
    contractId: uuid.UUID
    contractName: str
    counterparty: str
    riskScore: int


class HighRiskContractsResponse(BaseModel):
    items: list[HighRiskContractResponse]
    emptyMessage: str | None = None


class CounterpartyOptionResponse(BaseModel):
    id: uuid.UUID
    name: str


class OwnerOptionResponse(BaseModel):
    id: uuid.UUID
    name: str


class DashboardFilterOptionsResponse(BaseModel):
    contractTypes: list[str]
    departments: list[str]
    counterparties: list[CounterpartyOptionResponse]
    owners: list[OwnerOptionResponse]


class UserOptionResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: UserRole


class UserOptionListResponse(BaseModel):
    items: list[UserOptionResponse]
