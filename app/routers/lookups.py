"""`/api/v1/dashboard/*` and `/api/v1/users` -- thin HTTP binding over `app.services.lookups`.
See CLAUDE.md's uc123 module section and TASK.md (T-LOOKUPS-API) for the exact paths, roles
and DTOs these routes must match.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.lookup import (
    DashboardFilterOptionsResponse,
    DashboardSummaryResponse,
    HighRiskContractsResponse,
    MyTasksResponse,
    UserOptionListResponse,
)
from app.services import lookups as lookups_service
from app.services.lookups import DashboardFilters

router = APIRouter(tags=["lookups"])

_ALL_ROLES = ("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER", "SIGNER")
_HIGH_RISK_ROLES = ("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")

# Dependency declaration order matters here, not just for readability: the role check must
# resolve (and be able to raise 401/403) before `current_tenant_id` ever touches the
# database -- see app/routers/contracts.py for the same convention.


def _dashboard_filters(
    contractType: str | None = Query(None),
    department: str | None = Query(None),
    counterpartyId: uuid.UUID | None = Query(None),
    ownerId: uuid.UUID | None = Query(None),
    startDate: date | None = Query(None),
    endDate: date | None = Query(None),
) -> DashboardFilters:
    return DashboardFilters(
        contract_type=contractType,
        department=department,
        counterparty_id=counterpartyId,
        owner_id=ownerId,
        start_date=startDate,
        end_date=endDate,
    )


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    filters: DashboardFilters = Depends(_dashboard_filters),
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> DashboardSummaryResponse:
    return lookups_service.get_dashboard_summary(db, tenant_id, filters)


@router.get("/dashboard/my-tasks", response_model=MyTasksResponse)
def get_my_tasks(
    filters: DashboardFilters = Depends(_dashboard_filters),
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> MyTasksResponse:
    return lookups_service.get_my_tasks(db, tenant_id, user, filters)


@router.get("/dashboard/high-risk-contracts", response_model=HighRiskContractsResponse)
def get_high_risk_contracts(
    filters: DashboardFilters = Depends(_dashboard_filters),
    user: CurrentUser = Depends(require_roles(*_HIGH_RISK_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> HighRiskContractsResponse:
    return lookups_service.get_high_risk_contracts(db, tenant_id, user, filters)


@router.get("/dashboard/filters", response_model=DashboardFilterOptionsResponse)
def get_dashboard_filter_options(
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> DashboardFilterOptionsResponse:
    return lookups_service.get_filter_options(db, tenant_id)


@router.get("/users", response_model=UserOptionListResponse)
def list_users(
    role: str | None = Query(None),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> UserOptionListResponse:
    return lookups_service.get_user_options(db, tenant_id, role)
