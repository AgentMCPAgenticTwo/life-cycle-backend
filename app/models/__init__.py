"""Import every ORM entity so `Base.metadata` is fully populated as soon as this package is
imported -- Alembic's `env.py` and any future resource task rely on this for autogeneration
and for `Base.metadata.create_all()` in tests.
"""
from app.models.approval import (
    Approval,
    ApprovalAuditLog,
    ApprovalDelegation,
    ApprovalMatrixConfig,
    ApprovalMatrixStep,
    ApprovalStepInstance,
)
from app.models.clause import Clause, ClauseVersion
from app.models.contract import Contract, ContractTask
from app.models.contract_lifecycle import (
    ActivityLogEntry,
    ContractAssignment,
    ContractDocument,
    ContractFolderTag,
    ContractLifecycleAction,
    ContractVersion,
    FolderTag,
    Obligation,
    ObligationAuditLog,
    RenewalAlert,
)
from app.models.counterparty import Counterparty
from app.models.esignature import (
    AuditCertificate,
    EsignatureSettings,
    SignatureAuditLog,
    Signer,
)
from app.models.lifecycle_clause import (
    AskAiInteraction,
    ClauseAuditLog,
    ContractClause,
    ContractMetadata,
)
from app.models.lifecycle_negotiation import (
    NegotiationComment,
    NegotiationExternalLink,
    NegotiationReminder,
    NegotiationReviewer,
    NegotiationRouting,
    NegotiationVersion,
)
from app.models.tenant import Tenant
from app.models.template import Template, TemplateVersion
from app.models.tracker import (
    ApprovalMatrixRule,
    ContractLifecycleStageHistory,
    ContractOwner,
    ContractTurnaroundMetrics,
    TenantAuditLog,
    TenantBottleneckThreshold,
    TenantIntegration,
    TenantNotificationSetting,
    TenantUser,
    TurnaroundOverrideLog,
)
from app.models.refresh_token import RefreshToken
from app.models.uploaded_file import UploadedFile
from app.models.user import User

__all__ = [
    "Tenant",
    "User",
    "RefreshToken",
    "Counterparty",
    "UploadedFile",
    "Template",
    "TemplateVersion",
    "Clause",
    "ClauseVersion",
    "Contract",
    "ContractTask",
    "ContractClause",
    "ContractMetadata",
    "ClauseAuditLog",
    "AskAiInteraction",
    "NegotiationRouting",
    "NegotiationReviewer",
    "NegotiationVersion",
    "NegotiationComment",
    "NegotiationExternalLink",
    "NegotiationReminder",
    "ApprovalMatrixConfig",
    "ApprovalMatrixStep",
    "Approval",
    "ApprovalStepInstance",
    "ApprovalDelegation",
    "ApprovalAuditLog",
    "Signer",
    "SignatureAuditLog",
    "AuditCertificate",
    "EsignatureSettings",
    "ContractAssignment",
    "ContractDocument",
    "ContractVersion",
    "FolderTag",
    "ContractFolderTag",
    "ActivityLogEntry",
    "Obligation",
    "RenewalAlert",
    "ContractLifecycleAction",
    "ObligationAuditLog",
    "ContractLifecycleStageHistory",
    "ContractOwner",
    "ContractTurnaroundMetrics",
    "TurnaroundOverrideLog",
    "TenantBottleneckThreshold",
    "TenantUser",
    "ApprovalMatrixRule",
    "TenantIntegration",
    "TenantNotificationSetting",
    "TenantAuditLog",
]
