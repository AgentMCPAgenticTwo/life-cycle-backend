"""Wire-format request/response types this task owns: `SignerResponse`, `SignerListResponse`,
`AddSignerRequest`, `UpdateSignerRequest`, `SendForSignatureRequest`,
`SendForSignatureResponse`, `AuditCertificateSignerEntry`, `AuditCertificateResponse` -- see
CLAUDE.md's UC6-UC7-combined module section and T-CONTRACTS-API/context.json. Field names are
camelCase and match the contract exactly.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SignerType = Literal["Internal", "External"]
SignatureMethod = Literal["In-built E-signature", "DocuSign", "Adobe Sign", "Aadhaar eSign"]


class SignerResponse(BaseModel):
    id: uuid.UUID
    contractId: uuid.UUID
    signerName: str
    signerEmail: str
    signerType: str
    signingOrder: int
    signatureMethod: str
    reminderFrequencyDays: int | None = None
    signerStatus: str
    otpVerifiedAt: datetime | None = None
    signaturePadCompleted: bool
    ipAddress: str | None = None
    signedAt: datetime | None = None
    declineReason: str | None = None
    linkExpiresAt: datetime | None = None


class SignerListResponse(BaseModel):
    contractId: uuid.UUID
    signers: list[SignerResponse]
    sendForSignatureEnabled: bool
    signingOrderLocked: bool


class AddSignerRequest(BaseModel):
    signerName: str
    signerEmail: str
    signerType: SignerType
    signingOrder: int
    signatureMethod: SignatureMethod


class UpdateSignerRequest(BaseModel):
    signerName: str | None = None
    signerEmail: str | None = None
    signerType: SignerType | None = None
    signingOrder: int | None = None
    signatureMethod: SignatureMethod | None = None


class SendForSignatureRequest(BaseModel):
    signatureMethod: SignatureMethod | None = None


class SendForSignatureResponse(BaseModel):
    contractId: uuid.UUID
    contractStatus: str
    signers: list[SignerResponse]
    errorMessage: str | None = None


class AuditCertificateSignerEntry(BaseModel):
    signerName: str
    signerEmail: str
    signerType: str
    signingOrder: int
    signatureMethod: str
    reminderFrequencyDays: int | None = None
    signerStatus: str
    ipAddress: str | None = None
    signedAt: datetime | None = None
    otpVerifiedAt: datetime | None = None
    signaturePadCompleted: bool


class AuditCertificateResponse(BaseModel):
    contractId: uuid.UUID
    generatedAt: datetime
    downloadUrl: str
    signers: list[AuditCertificateSignerEntry]
