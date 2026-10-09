"""`/api/v1/clauses` -- thin HTTP binding over `app.services.clauses`. See CLAUDE.md's uc123
module section for the exact paths, roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.clause import (
    ClauseListResponse,
    ClauseResponse,
    CreateClauseRequest,
    UpdateClauseRequest,
    VersionHistoryResponse,
)
from app.services import clauses as clauses_service

router = APIRouter(prefix="/clauses", tags=["clauses"])

# Dependency declaration order matters here, not just for readability: the role check must
# resolve (and be able to raise 401/403) before `current_tenant_id` ever touches the
# database, so an unauthorized caller never trips a DB-configuration error instead of the
# auth error the contract promises. `db: Depends(get_db)` is declared last on every route
# below for the same reason, even though `current_tenant_id` already resolved (and cached)
# the identical session.


@router.get("", response_model=ClauseListResponse)
def list_clauses(
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "LEGAL_REVIEWER", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseListResponse:
    return clauses_service.list_clauses(db, tenant_id, user.role)


@router.post("", response_model=ClauseResponse, status_code=201)
def create_clause(
    payload: CreateClauseRequest,
    response: Response,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseResponse:
    result = clauses_service.create_clause(db, tenant_id, user, payload)
    response.headers["Location"] = f"/api/v1/clauses/{result.id}"
    return result


@router.put("/{id}", response_model=ClauseResponse)
def update_clause(
    id: uuid.UUID,
    payload: UpdateClauseRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseResponse:
    return clauses_service.update_clause(db, tenant_id, id, user, payload)


@router.post("/{id}/deactivate", response_model=ClauseResponse)
def deactivate_clause(
    id: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseResponse:
    return clauses_service.deactivate_clause(db, tenant_id, id, user)


@router.post("/{id}/reactivate", response_model=ClauseResponse)
def reactivate_clause(
    id: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ClauseResponse:
    return clauses_service.reactivate_clause(db, tenant_id, id, user)


@router.get("/{id}/versions", response_model=VersionHistoryResponse)
def get_clause_versions(
    id: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> VersionHistoryResponse:
    return clauses_service.get_versions(db, tenant_id, id)
