"""`/api/v1/lifecycle/contracts/{contractId}/...` -- thin HTTP binding over
`app.services.lifecycle_clauses`. See CLAUDE.md's lifecycle-uc4-uc5 module section for the
exact paths, roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.errors import ImmutableResourceError
from app.models.immutable import AUDIT_LOG_IMMUTABLE_MESSAGE
from app.schemas.lifecycle_clause import (
    AskAIRequest,
    AskAIResponse,
    ClauseAnalysisResponse,
    ClauseResponse,
    ContractMetadataResponse,
    EditClauseRequest,
    PagedAuditLogResponse,
    ProceedToNegotiationResponse,
    RejectClauseRequest,
    UpdateMetadataRequest,
)
from app.schemas.pagination import PageParams
from app.services import lifecycle_clauses as service

router = APIRouter(prefix="/lifecycle/contracts/{contractId}", tags=["lifecycle-clauses"])

# Dependency declaration order matters here, not just for readability: the role check must
# resolve (and be able to raise 401/403) before `current_tenant_id` ever touches the
# database -- see app/routers/clauses.py for the same convention.


@router.get("/clause-analysis", response_model=ClauseAnalysisResponse)
def get_clause_analysis(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER", "TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseAnalysisResponse:
    return service.get_clause_analysis(db, tenant_id, user, contractId)


@router.post("/retry-extraction", response_model=ClauseAnalysisResponse)
def retry_extraction(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseAnalysisResponse:
    return service.retry_extraction(db, tenant_id, user, contractId)


@router.post("/clauses/{clauseId}/accept-suggestion", response_model=ClauseResponse)
def accept_suggestion(
    contractId: uuid.UUID,
    clauseId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseResponse:
    return service.accept_suggestion(db, tenant_id, user, contractId, clauseId)


@router.put("/clauses/{clauseId}", response_model=ClauseResponse)
def edit_clause(
    contractId: uuid.UUID,
    clauseId: uuid.UUID,
    payload: EditClauseRequest,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseResponse:
    return service.edit_clause(db, tenant_id, user, contractId, clauseId, payload)


@router.post("/clauses/{clauseId}/reject", response_model=ClauseResponse)
def reject_clause(
    contractId: uuid.UUID,
    clauseId: uuid.UUID,
    payload: RejectClauseRequest,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseResponse:
    return service.reject_clause(db, tenant_id, user, contractId, clauseId, payload)


@router.put("/metadata", response_model=ContractMetadataResponse)
def update_metadata(
    contractId: uuid.UUID,
    payload: UpdateMetadataRequest,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ContractMetadataResponse:
    return service.update_metadata(db, tenant_id, user, contractId, payload)


@router.post("/ask-ai", response_model=AskAIResponse)
def ask_ai(
    contractId: uuid.UUID,
    payload: AskAIRequest,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> AskAIResponse:
    return service.ask_ai(db, tenant_id, user, contractId, payload)


@router.post("/proceed-to-negotiation", response_model=ProceedToNegotiationResponse)
def proceed_to_negotiation(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ProceedToNegotiationResponse:
    return service.proceed_to_negotiation(db, tenant_id, user, contractId)


@router.get("/audit-log", response_model=PagedAuditLogResponse)
def get_audit_log(
    contractId: uuid.UUID,
    page_params: PageParams = Depends(),
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER", "TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> PagedAuditLogResponse:
    return service.get_audit_log(db, tenant_id, contractId, page_params)


# UC11-BR-005: the clause audit trail is immutable. These routes exist only to answer an
# edit/delete attempt with the rule's own message instead of a bare 405; the persistence
# layer blocks the same thing again (`app.models.immutable.enforce_append_only`).
def _reject_audit_log_mutation() -> None:
    raise ImmutableResourceError(
        AUDIT_LOG_IMMUTABLE_MESSAGE, details=[AUDIT_LOG_IMMUTABLE_MESSAGE]
    )


@router.put("/audit-log/{entryId}")
@router.patch("/audit-log/{entryId}")
def update_audit_log_entry(
    contractId: uuid.UUID,
    entryId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER", "TENANT_ADMIN")),
) -> None:
    _reject_audit_log_mutation()


@router.delete("/audit-log/{entryId}")
def delete_audit_log_entry(
    contractId: uuid.UUID,
    entryId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("LEGAL_REVIEWER", "CONTRACT_OWNER", "TENANT_ADMIN")),
) -> None:
    _reject_audit_log_mutation()
