"""Wire-format request/response types for the `lifecycle-uc4-uc5` module's Negotiation &
Routing endpoints (`/api/v1/lifecycle/contracts/{contractId}/negotiation/...` and
`/api/v1/lifecycle/negotiation/external/{linkToken}/...`). Field names are camelCase and
match the contract's DTOs exactly: `ReviewerResponse`, `RoutingRequest`, `RoutingResponse`,
`VersionSummaryResponse`, `CommentResponse`, `CommentRequest`, `NegotiationTrackerResponse`,
`SubmitReviewRequest`, `SubmitReviewResponse`, `GenerateExternalLinkResponse`,
`VerifyOtpRequest`, `NegotiationExternalViewResponse`, `VerifyOtpResponse`,
`ExternalSubmitRequest`, `ExternalSubmitResponse`, `ClauseDiffResponse`,
`CompareVersionsResponse`, `ReminderResponse`, `MarkAgreedResponse`.
"""
import uuid
from datetime import date, datetime

from pydantic import BaseModel


class ReviewerResponse(BaseModel):
    reviewerId: uuid.UUID
    reviewerName: str
    role: str | None = None
    isMandatory: bool
    reviewStatus: str
    submittedAt: datetime | None = None
    sequenceOrder: int | None = None


class RoutingRequest(BaseModel):
    routingType: str
    internalReviewers: list[uuid.UUID]
    externalPartyName: str
    externalPartyEmail: str
    assignedDate: date
    dueDate: date


class RoutingResponse(BaseModel):
    contractId: uuid.UUID
    routingType: str
    internalReviewers: list[ReviewerResponse]
    externalPartyName: str
    externalPartyEmail: str
    assignedDate: date
    dueDate: date
    negotiationStatus: str
    versionNumber: int


class VersionSummaryResponse(BaseModel):
    versionNumber: int
    createdAt: datetime
    createdBy: str
    source: str


class CommentResponse(BaseModel):
    commentId: uuid.UUID
    clauseId: str | None = None
    commentText: str
    authorName: str
    createdAt: datetime
    versionNumber: int


class CommentRequest(BaseModel):
    clauseId: str | None = None
    commentText: str


class NegotiationTrackerResponse(BaseModel):
    contractId: uuid.UUID
    routingType: str
    internalReviewers: list[ReviewerResponse]
    externalPartyName: str
    externalPartyEmail: str
    assignedDate: date
    dueDate: date
    negotiationStatus: str
    versionNumber: int
    overdueFlag: bool
    versions: list[VersionSummaryResponse]
    comments: list[CommentResponse]


class SubmitReviewRequest(BaseModel):
    commentText: str | None = None
    redlineText: str | None = None
    # UC5: the version the reviewer had open when they started redlining. Optional because
    # the frontend contract does not list it -- when it is absent there is nothing to
    # compare against and the submission is treated as being on the latest version.
    expectedVersion: int | None = None


class SubmitReviewResponse(BaseModel):
    versionNumber: int
    negotiationStatus: str


class GenerateExternalLinkResponse(BaseModel):
    linkToken: str
    expiresAt: datetime
    status: str
    # Added field, not in context.json's GenerateExternalLinkResponse -- see this task's
    # `blockers`. There is no email-sending infrastructure anywhere in this codebase, so the
    # OTP that UC5-BR-016 requires to reach the External Party's inbox has no delivery
    # channel; it is returned here instead so the external verify/submit flow is reachable
    # at all without a real mail server.
    otp: str | None = None


class VerifyOtpRequest(BaseModel):
    otp: str


class NegotiationExternalViewResponse(BaseModel):
    contractId: uuid.UUID
    versionNumber: int
    documentText: str
    commentBoxEnabled: bool


class VerifyOtpResponse(BaseModel):
    verified: bool
    negotiationData: NegotiationExternalViewResponse | None = None


class ClauseRedlineRequest(BaseModel):
    clauseId: uuid.UUID
    clauseText: str


class ExternalSubmitRequest(BaseModel):
    commentText: str | None = None
    redlineText: str
    # Added field, not in the frontend's ExternalSubmitRequest -- optional, so a caller that
    # sends only `redlineText` still works. UC5's risk re-check must re-score only the
    # clauses the counterparty changed; a flat redline document cannot say which clause is
    # which, so when this list is present it carries the changed clauses explicitly and the
    # new version's snapshot (and therefore Compare Versions) shows the real diff.
    clauseRedlines: list[ClauseRedlineRequest] | None = None


class ExternalSubmitResponse(BaseModel):
    versionNumber: int
    negotiationStatus: str


class ClauseDiffResponse(BaseModel):
    clauseId: str | None = None
    clauseCategory: str | None = None
    textA: str | None = None
    textB: str | None = None
    changeType: str


class CompareVersionsResponse(BaseModel):
    versionA: VersionSummaryResponse
    versionB: VersionSummaryResponse
    differences: list[ClauseDiffResponse]
    comments: list[CommentResponse]
    negotiationStatus: str
    routingType: str
    internalReviewers: list[ReviewerResponse]
    externalPartyName: str
    externalPartyEmail: str
    assignedDate: date
    dueDate: date


class ReminderResponse(BaseModel):
    sentTo: str
    sentAt: datetime
    reminderType: str


class MarkAgreedResponse(BaseModel):
    negotiationStatus: str
    versionNumber: int
    routingType: str
    internalReviewers: list[ReviewerResponse]
    externalPartyName: str
    externalPartyEmail: str
    assignedDate: date
    dueDate: date
