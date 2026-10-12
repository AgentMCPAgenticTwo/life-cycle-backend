"""Wire-format request/response types for the `approval-matrix-config` resource (see
CLAUDE.md's UC6-UC7-combined module section). Field names are camelCase and match the
contract's `ApprovalMatrixStepConfig`, `ApprovalMatrixConfigResponse`,
`ApprovalMatrixConfigListResponse` and `UpdateApprovalMatrixConfigRequest` DTOs exactly.
"""
import uuid
from decimal import Decimal

from pydantic import BaseModel


class ApprovalMatrixStepConfig(BaseModel):
    stepNumber: int
    approverRole: str | None = None
    approverUserId: uuid.UUID | None = None
    stepName: str


class ApprovalMatrixConfigResponse(BaseModel):
    id: uuid.UUID
    contractType: str
    valueMin: Decimal | None = None
    valueMax: Decimal | None = None
    riskBandMin: int | None = None
    riskBandMax: int | None = None
    steps: list[ApprovalMatrixStepConfig]


class ApprovalMatrixConfigListResponse(BaseModel):
    items: list[ApprovalMatrixConfigResponse]


class ApprovalMatrixConfigItemRequest(BaseModel):
    # `context.json`'s `UpdateApprovalMatrixConfigRequest.items` reuses
    # `ApprovalMatrixConfigResponse`, whose `id` is non-nullable -- but CLAUDE.md forbids
    # accepting a client-supplied id on create. `id` is made optional here: present it
    # matches an existing row to update, omitted it is a new rule and the server generates
    # the id. See this task's `blockers`.
    id: uuid.UUID | None = None
    contractType: str
    valueMin: Decimal | None = None
    valueMax: Decimal | None = None
    riskBandMin: int | None = None
    riskBandMax: int | None = None
    steps: list[ApprovalMatrixStepConfig]


class UpdateApprovalMatrixConfigRequest(BaseModel):
    items: list[ApprovalMatrixConfigItemRequest]
