"""`/api/v1/contracts` -- thin HTTP binding over `app.services.contracts`. See CLAUDE.md's
uc123 module section and TASK.md (T-CONTRACTS-API) for the exact paths, roles and DTOs this
router must match.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.contract import ContractListResponse, ContractResponse, CreateContractRequest
from app.schemas.pagination import PageParams
from app.services import contracts as contracts_service

router = APIRouter(prefix="/contracts", tags=["contracts"])

_ALL_ROLES = ("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER", "SIGNER")

# Dependency declaration order matters here, not just for readability: the role check must
# resolve (and be able to raise 401/403) before `current_tenant_id` ever touches the
# database -- see app/routers/clauses.py for the same convention.


@router.get("", response_model=ContractListResponse)
def list_contracts(
    page_params: PageParams = Depends(),
    status: str | None = Query(None),
    contractType: str | None = Query(None),
    department: str | None = Query(None),
    counterpartyId: uuid.UUID | None = Query(None),
    ownerId: uuid.UUID | None = Query(None),
    startDate: date | None = Query(None),
    endDate: date | None = Query(None),
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ContractListResponse:
    return contracts_service.list_contracts(
        db,
        tenant_id,
        page_params,
        status=status,
        contract_type=contractType,
        department=department,
        counterparty_id=counterpartyId,
        owner_id=ownerId,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/{id}", response_model=ContractResponse)
def get_contract(
    id: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ContractResponse:
    return contracts_service.get_contract_detail(db, tenant_id, user, id)


@router.post("", response_model=ContractResponse, status_code=201)
def create_contract(
    payload: CreateContractRequest,
    response: Response,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ContractResponse:
    result = contracts_service.create_contract(db, tenant_id, user, payload)
    response.headers["Location"] = f"/api/v1/contracts/{result.id}"
    return result
