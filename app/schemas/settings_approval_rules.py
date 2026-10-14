"""DTOs for `/api/v1/settings/approval-rules` -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-SETTINGS-APPROVAL-RULES-API) for the exact fields and enums.
"""
import uuid
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel

ContractType = Literal["Product", "Service"]
ApproverRole = Literal["Approver", "Legal Reviewer", "Tenant Admin"]


class ApprovalRuleResponse(BaseModel):
    id: uuid.UUID
    contractType: ContractType
    valueThreshold: Decimal
    approverRole: ApproverRole


class ApprovalRuleListResponse(BaseModel):
    items: list[ApprovalRuleResponse]
    page: int
    pageSize: int
    totalCount: int


class CreateApprovalRuleRequest(BaseModel):
    """Fields are optional/untyped here on purpose: UC11-AF-003 requires the single message
    'Please complete all required fields' for a blank Contract Type or Approver Role, and
    UC11-FV-002 requires a dedicated numeric/negative message for Value Threshold -- both are
    business-rule checks raised by app.services.settings_approval_rules, not generic Pydantic
    "field required" / "not a valid enumeration member" errors from this layer.
    """

    contractType: str | None = None
    valueThreshold: Decimal | None = None
    approverRole: str | None = None


class UpdateApprovalRuleRequest(CreateApprovalRuleRequest):
    """Editing a rule carries the same three fields, and the same validation, as creating
    one (UC11-AF-003, UC11-FV-002, UC11-BR-004)."""
