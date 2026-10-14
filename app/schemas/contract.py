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
# "Rejected" and "Ready For Signature" were added here (additively, nothing removed or
# renamed) by T-APPROVALS-API: the approvals workflow (UC6) needs to persist these two
# terminal/near-terminal contract states to the same `contracts.status` column the uc123
# module already reads/writes, and that module's `ContractResponse.status` is validated
# against this Literal -- an unlisted value would 500 on every contract GET. See this
# task's `blockers` for the full contradiction this resolves.
# "Sent" was added here (additively) by T-CONTRACTS-API (UC7 e-signature): Send for Signature
# persists this status to the same shared `contracts.status` column. See this task's
# `blockers`.
# "In Approval", "In Signature", "Active", "Expired", "Terminated", "Renewed" and "Amended"
# were added here (additively) by the life-cycle-uc8-uc9 module's T-CONTRACTS-API run: UC8-BR-011
# and UC9-BR-004/016/017/018 persist these lifecycle states to this same shared
# `contracts.status` column (Repository status display, and the Renew/Amend/Terminate
# transitions). See this task's `blockers`.
# Contract status flow fix: the workflow now writes only Draft -> In Negotiation -> Pending
# Approval -> Pending Signature -> Executed, plus Rejected and "Signature Declined" (see
# app.services.contract_status). "Ready For Signature", "Sent" and "SignatureDeclined" are no
# longer written -- migration 0053 rewrites them -- and stay listed only so a row the
# migration has not reached cannot 500 a contract GET.
ContractStatus = Literal[
    "Draft",
    "In Negotiation",
    "Pending Approval",
    "Pending Signature",
    "Executed",
    "Rejected",
    "Signature Declined",
    "Ready For Signature",
    "Sent",
    "SignatureDeclined",
    "In Approval",
    "In Signature",
    "Active",
    "Expired",
    "Terminated",
    "Renewed",
    "Amended",
]


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
    # UC2 document generation: the frontend's ContractResponse carries only id/contractName/
    # status, so these two fields are additive and ignored by a client that does not read
    # them. `documentVersionNumber` is the version the save produced (always 1 on create);
    # `message` is UC2's confirmation text.
    documentVersionNumber: int | None = None
    message: str | None = None


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
