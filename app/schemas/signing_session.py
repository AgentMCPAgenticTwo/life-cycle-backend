"""Wire-format request/response types this task owns: `SigningSessionResponse`,
`VerifyOtpRequest`, `VerifyOtpResponse`, `ApplySignatureRequest`, `ApplySignatureResponse`,
`DeclineSignatureRequest`, `DeclineSignatureResponse` -- see CLAUDE.md's UC6-UC7-combined
module section and T-SIGNING-SESSIONS-API/context.json. Field names are camelCase and match
the contract exactly.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel

SignatureType = Literal["Draw", "Type", "Upload"]


class SigningSessionResponse(BaseModel):
    sessionId: uuid.UUID
    contractId: uuid.UUID
    signerId: uuid.UUID
    signerName: str
    signerEmail: str
    signerStatus: str
    isCurrentTurn: bool
    otpVerified: bool
    documentUrl: str | None = None
    signaturePadAvailable: bool
    declineAvailable: bool
    reminderFrequencyDays: int | None = None
    linkExpired: bool
    blockedMessage: str | None = None


class VerifyOtpRequest(BaseModel):
    otpCode: str


class VerifyOtpResponse(BaseModel):
    signerStatus: str
    documentUrl: str | None = None
    signaturePadAvailable: bool
    attemptsRemaining: int | None = None
    lockedUntil: datetime | None = None
    errorMessage: str | None = None


class ApplySignatureRequest(BaseModel):
    signatureData: str
    signatureType: SignatureType


class ApplySignatureResponse(BaseModel):
    signerId: uuid.UUID
    signerStatus: str
    contractStatus: str
    nextSignerId: uuid.UUID | None = None


class DeclineSignatureRequest(BaseModel):
    reason: str


class DeclineSignatureResponse(BaseModel):
    signerId: uuid.UUID
    signerStatus: str
    contractStatus: str
    reason: str
