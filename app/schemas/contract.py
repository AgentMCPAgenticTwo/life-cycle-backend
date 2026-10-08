"""Wire-format request/response types for the `contracts` resource (see CLAUDE.md's uc123
module section). Field names are camelCase and match the contract's `ContractListItemResponse`,
`ContractListResponse`, `ContractResponse` and `CreateContractRequest` DTOs exactly.
"""
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel

ContractType = Literal[
    "NDA",
    "MSA",
    "SOW",
    "Sales Agreement",
    "Purchase Agreement",
    "Service Agreement",
    "Vendor Agreement",
    "Licensing",
    "Amendment",
    "Renewal",
]
Industry = Literal["Product", "Service"]
Currency = Literal["USD", "EUR", "GBP", "INR"]
RenewalType = Literal["Auto", "Manual", "None"]
ContractStatus = Literal["Draft", "In Negotiation", "Pending Approval", "Pending Signature", "Executed"]


class ContractListItemResponse(BaseModel):
    id: uuid.UUID
    contractName: str
    contractType: ContractType
    department: str | None = None
    counterpartyName: str
    contractOwnerName: str
    status: ContractStatus
    startDate: date
    endDate: date
    contractValue: float
    currency: Currency
    riskScore: int | None = None


class ContractListResponse(BaseModel):
    items: list[ContractListItemResponse]
    page: int
    pageSize: int
    totalCount: int
    noMatchMessage: str | None = None


class ContractResponse(BaseModel):
    id: uuid.UUID
    contractName: str
    contractType: ContractType
    industry: Industry
    department: str | None = None
    templateId: uuid.UUID | None = None
    thirdPartyPaperFileId: uuid.UUID | None = None
    counterpartyId: uuid.UUID
    counterpartyName: str
    counterpartyEmail: str
    counterpartyCompany: str
    counterpartyAddress: str | None = None
    counterpartyGstTaxId: str | None = None
    contractOwnerId: uuid.UUID
    contractOwnerName: str
    contractValue: float
    currency: Currency
    startDate: date
    endDate: date
    renewalType: RenewalType
    noticePeriod: int | None = None
    assignedDate: date
    dueDate: date
    status: ContractStatus
    riskScore: int | None = None
    createdAt: datetime
    updatedAt: datetime


class CreateContractRequest(BaseModel):
    contractType: ContractType
    industry: Industry
    templateId: uuid.UUID | None = None
    thirdPartyPaperFileId: uuid.UUID | None = None
    counterpartySearch: str | None = None
    counterpartyId: uuid.UUID | None = None
    counterpartyName: str | None = None
    counterpartyEmail: str | None = None
    counterpartyCompany: str | None = None
    counterpartyAddress: str | None = None
    counterpartyGstTaxId: str | None = None
    contractOwnerId: uuid.UUID
    contractValue: float
    currency: Currency
    startDate: date
    endDate: date
    renewalType: RenewalType
    noticePeriod: int | None = None
    dueDate: date
