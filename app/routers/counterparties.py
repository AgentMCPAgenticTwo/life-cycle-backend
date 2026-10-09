"""`/api/v1/counterparties` -- thin HTTP binding over `app.services.counterparties`. See
CLAUDE.md's uc123 module section and TASK.md (T-COUNTERPARTIES-API) for the exact paths,
roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.counterparty import (
    CounterpartyResponse,
    CounterpartySearchResponse,
    CreateCounterpartyRequest,
)
from app.services import counterparties as counterparties_service

router = APIRouter(prefix="/counterparties", tags=["counterparties"])

# Dependency declaration order matters here, not just for readability: the role check must
# resolve (and be able to raise 401/403) before `current_tenant_id` ever touches the
# database -- see app/routers/clauses.py for the same convention.


@router.get("", response_model=CounterpartySearchResponse)
def search_counterparties(
    search: str | None = Query(None),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> CounterpartySearchResponse:
    return counterparties_service.search_counterparties(db, tenant_id, search)


@router.post("", response_model=CounterpartyResponse, status_code=201)
def create_counterparty(
    payload: CreateCounterpartyRequest,
    response: Response,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> CounterpartyResponse:
    result = counterparties_service.create_counterparty(db, tenant_id, user, payload)
    response.headers["Location"] = f"/api/v1/counterparties/{result.id}"
    return result
