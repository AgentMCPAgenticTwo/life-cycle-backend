"""Business rules for the dashboard and lookup endpoints: status-card and expiring-window
counts, role-scoped My Tasks and High Risk panels, filter-option assembly and the Contract
Owner dropdown. See CLAUDE.md's uc123 module section and this task's stories UC1-AF-001..005,
UC1-BR-001..014, UC1-FV-001..004, UC1-GC-001/002, UC1-MF-001, UC2-BR-003/012, UC2-MF-001
(T-LOOKUPS-API/TASK.md).
"""
import uuid
from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.repositories import lookups as lookups_repo
from app.schemas.contract import ContractType
from app.schemas.lookup import (
    CounterpartyOptionResponse,
    DashboardFilterOptionsResponse,
    HighRiskContractResponse,
    HighRiskContractsResponse,
    DashboardSummaryResponse,
    MyTaskItemResponse,
    MyTasksResponse,
    OwnerOptionResponse,
    UserOptionListResponse,
    UserOptionResponse,
)

_DEFAULT_HIGH_RISK_THRESHOLD = 70
_STATUSES = ("Draft", "In Negotiation", "Pending Approval", "Pending Signature", "Executed")


@dataclass
class DashboardFilters:
    """The Contract Type / Department / Counterparty / Owner / Date Range filters shared by
    the summary, My Tasks and High Risk endpoints (UC1-BR-008, UC1-FV-004)."""

    contract_type: str | None = None
    department: str | None = None
    counterparty_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    start_date: date | None = None
    end_date: date | None = None

    @property
    def any_applied(self) -> bool:
        return any(
            v is not None
            for v in (
                self.contract_type,
                self.department,
                self.counterparty_id,
                self.owner_id,
                self.start_date,
                self.end_date,
            )
        )


def _resolve_counterparty_name(db: Session, counterparty_id: uuid.UUID) -> str:
    row = lookups_repo.get_counterparty(db, counterparty_id)
    return row.name if row is not None else "Unknown"


def get_dashboard_summary(
    db: Session, tenant_id: uuid.UUID, filters: DashboardFilters
) -> DashboardSummaryResponse:
    tenant_total = lookups_repo.count_tenant_contracts(db, tenant_id)
    rows = lookups_repo.list_filtered_contracts(
        db,
        tenant_id,
        contract_type=filters.contract_type,
        department=filters.department,
        counterparty_id=filters.counterparty_id,
        owner_id=filters.owner_id,
        start_date=filters.start_date,
        end_date=filters.end_date,
    )

    counts = dict.fromkeys(_STATUSES, 0)
    expiring_30 = expiring_60 = expiring_90 = 0
    today = date.today()
    for row in rows:
        if row.status in counts:
            counts[row.status] += 1
        # UC1-BR-002: remaining days = end date - today; a contract still counts in every
        # wider window it also fits (20 days -> 30/60/90; 45 days -> 60/90 only; etc).
        remaining_days = (row.end_date - today).days
        if 0 <= remaining_days <= 90:
            expiring_90 += 1
            if remaining_days <= 60:
                expiring_60 += 1
            if remaining_days <= 30:
                expiring_30 += 1

    no_contracts_message = None
    no_match_message = None
    if tenant_total == 0:
        # UC1-AF-001: nothing has ever been created for this tenant.
        no_contracts_message = "No contracts yet. Click New Contract to get started."
    elif not rows and filters.any_applied:
        # UC1-AF-004: contracts exist, but the applied filters match none of them.
        no_match_message = "No contracts match the selected filters"

    return DashboardSummaryResponse(
        totalContractsCount=len(rows),
        inDraftCount=counts["Draft"],
        inNegotiationCount=counts["In Negotiation"],
        pendingApprovalCount=counts["Pending Approval"],
        pendingSignatureCount=counts["Pending Signature"],
        executedCount=counts["Executed"],
        expiring30DaysCount=expiring_30,
        expiring60DaysCount=expiring_60,
        expiring90DaysCount=expiring_90,
        noContractsMessage=no_contracts_message,
        noMatchMessage=no_match_message,
    )


def get_my_tasks(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, filters: DashboardFilters
) -> MyTasksResponse:
    user_uuid = uuid.UUID(user.user_id)
    items: list[MyTaskItemResponse] = []

    if user.role == "CONTRACT_OWNER":
        # UC1-BR-011: Contract Owner's My Tasks is "contracts I own awaiting any action", not
        # restricted to a specific pending step the way the other roles are.
        rows = lookups_repo.list_owned_open_contracts(
            db,
            tenant_id,
            user_uuid,
            contract_type=filters.contract_type,
            department=filters.department,
            counterparty_id=filters.counterparty_id,
            start_date=filters.start_date,
            end_date=filters.end_date,
        )
        for contract in rows:
            items.append(
                MyTaskItemResponse(
                    contractId=contract.id,
                    contractName=contract.contract_name,
                    counterparty=_resolve_counterparty_name(db, contract.counterparty_id),
                    status=contract.status,
                    dueDate=contract.due_date,
                )
            )
    else:
        # TENANT_ADMIN / LEGAL_REVIEWER / APPROVER / SIGNER (UC1-BR-003/009/010/012/013): only
        # contracts where this user is the current pending step's assignee.
        pairs = lookups_repo.list_current_tasks_for_assignee(
            db,
            tenant_id,
            user_uuid,
            contract_type=filters.contract_type,
            department=filters.department,
            counterparty_id=filters.counterparty_id,
            owner_id=filters.owner_id,
            start_date=filters.start_date,
            end_date=filters.end_date,
        )
        for task, contract in pairs:
            items.append(
                MyTaskItemResponse(
                    contractId=contract.id,
                    contractName=contract.contract_name,
                    counterparty=_resolve_counterparty_name(db, contract.counterparty_id),
                    status=contract.status,
                    dueDate=task.due_date,
                )
            )

    empty_message = "You have no pending tasks" if not items else None
    return MyTasksResponse(items=items, emptyMessage=empty_message)


def get_high_risk_contracts(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, filters: DashboardFilters
) -> HighRiskContractsResponse:
    tenant = lookups_repo.get_tenant(db, tenant_id)
    # UC1-BR-004: fall back to the documented default of 70 if the tenant row is somehow
    # unresolvable; in practice `tenants.high_risk_threshold` is NOT NULL and always set.
    threshold = tenant.high_risk_threshold if tenant is not None else _DEFAULT_HIGH_RISK_THRESHOLD

    rows = lookups_repo.list_filtered_contracts(
        db,
        tenant_id,
        contract_type=filters.contract_type,
        department=filters.department,
        counterparty_id=filters.counterparty_id,
        owner_id=filters.owner_id,
        start_date=filters.start_date,
        end_date=filters.end_date,
    )
    if user.role == "CONTRACT_OWNER":
        # UC1-BR-011 / UC1-FV-003: Contract Owner's High Risk panel is limited to contracts
        # they own; every other allowed role sees all qualifying tenant contracts (UC1-BR-010).
        user_uuid = uuid.UUID(user.user_id)
        rows = [r for r in rows if r.contract_owner_id == user_uuid]

    high_risk = [r for r in rows if r.risk_score is not None and r.risk_score > threshold]
    high_risk.sort(key=lambda r: r.risk_score, reverse=True)

    items = [
        HighRiskContractResponse(
            contractId=r.id,
            contractName=r.contract_name,
            counterparty=_resolve_counterparty_name(db, r.counterparty_id),
            riskScore=r.risk_score,
        )
        for r in high_risk
    ]
    empty_message = "No high risk contracts found" if not items else None
    return HighRiskContractsResponse(items=items, emptyMessage=empty_message)


def get_filter_options(db: Session, tenant_id: uuid.UUID) -> DashboardFilterOptionsResponse:
    departments = lookups_repo.list_distinct_departments(db, tenant_id)
    counterparties = [
        CounterpartyOptionResponse(id=c.id, name=c.name)
        for c in lookups_repo.list_counterparties(db, tenant_id)
    ]
    owners = [
        OwnerOptionResponse(id=u.id, name=u.name)
        for u in lookups_repo.list_users_by_role(db, tenant_id, "CONTRACT_OWNER")
    ]
    # Contract Type is a fixed, system-wide enum (the same list CreateContractRequest accepts)
    # rather than data derived from existing contracts, so the filter stays populated even for
    # a brand-new tenant with zero contracts (UC1-AF-001).
    return DashboardFilterOptionsResponse(
        contractTypes=list(ContractType.__args__),
        departments=departments,
        counterparties=counterparties,
        owners=owners,
    )


def get_user_options(db: Session, tenant_id: uuid.UUID, role: str | None) -> UserOptionListResponse:
    rows = lookups_repo.list_users_by_role(db, tenant_id, role)
    items = [UserOptionResponse(id=u.id, name=u.name, email=u.email, role=u.role) for u in rows]
    return UserOptionListResponse(items=items)
