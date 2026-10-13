"""Business rules for the Turnaround tab and its estimated-turnaround override action:
Period/Date-Range validation (UC10-FV-001), the Period-vs-custom-Date-Range precedence rule
(UC10-BR-006), role-scoped visibility (UC10-BR-005/009/010/011/012), the revised BR-4/BR-7
Estimated Turnaround derivation and 'Not Set'-exclusion rule, the Variance red/green color
coding (UC10-BR-003), and the override audit log (UC10-BR-007).

Window derivation mirrors the sibling tabs (`app.services.tracker_bottleneck` /
`tracker_ownership`): `contract_lifecycle_stage_history`'s open row for a contract is the
clock used for Period/Date-Range windowing, falling back to `contracts.updated_at` when no
stage-history row exists yet (see that module's blockers -- the same gap applies here).

BR-4/BR-7 source of truth: `context.json` names `contract_turnaround_metrics` as this
module's own table for `estimated_turnaround_days`/`estimated_turnaround_source`/
`actual_turnaround_days`/`excluded_from_averages`, but no other module in this codebase
writes to it yet (no UC2 "target completion date" field exists on `contracts`, and nothing
populates an AI-suggested duration). A contract with no `contract_turnaround_metrics` row is
therefore treated as BR-4's "no target completion date was set" case: `estimatedTurnaround`
is `None`, `estimatedTurnaroundNotSet` is `True`, `estimatedTurnaroundSource` is `NOT_SET`,
and the row is excluded from averages. This gap is recorded in this task's `blockers`.
"""
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ForbiddenError, NotFoundError, ValidationFailedError
from app.models.tracker import ContractTurnaroundMetrics, TurnaroundOverrideLog
from app.repositories import tracker_turnaround as repo
from app.schemas.tracker_turnaround import (
    PERIODS,
    EstimatedTurnaroundOverrideRequest,
    TrackerQueryParams,
    TurnaroundRowResponse,
    TurnaroundTabResponse,
)

PERIOD_REQUIRED_MESSAGE = "Period selection is required."
PERIOD_INVALID_MESSAGE = "Period must be one of: Daily, Weekly, Monthly."
DATE_FORMAT_MESSAGE = "Date Range From and Date Range To must be valid dates."
DATE_ORDER_MESSAGE = "Date Range From must be earlier than Date Range To."

NO_CONTRACT_DATA_MESSAGE = "No contract data available to display."
NO_RECORDS_FOR_PERIOD_MESSAGE = "No records found for the selected period."
NO_RECORDS_FOR_FILTERS_MESSAGE = "No records match the selected filters."

# This module contract's role names scope straight onto `contract_owners.role` -- a contract
# owner/legal reviewer/approver is "entitled" to a contract exactly when a row names them in
# that role (UC10-BR-005/009/010/011).
_SCOPED_ROLES = {"CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER"}


def _parse_date(value: str | None, *, field_message: str) -> date | None:
    if value is None or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValidationFailedError(field_message, details=[field_message])


def _validate_and_resolve_window(params: TrackerQueryParams) -> tuple[datetime, datetime]:
    date_from = _parse_date(params.date_range_from, field_message=DATE_FORMAT_MESSAGE)
    date_to = _parse_date(params.date_range_to, field_message=DATE_FORMAT_MESSAGE)

    if date_from is not None and date_to is not None:
        if not date_from < date_to:
            raise ValidationFailedError(DATE_ORDER_MESSAGE, details=[DATE_ORDER_MESSAGE])
        # UC10-BR-006: a valid custom Date Range overrides the Period dropdown.
        window_start = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        window_end = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
        return window_start, window_end

    if params.period is not None and params.period not in PERIODS:
        raise ValidationFailedError(PERIOD_INVALID_MESSAGE, details=[PERIOD_INVALID_MESSAGE])

    if params.period is None:
        # UC10-FV-001: Period is mandatory unless a valid custom Date Range already resolved above.
        raise ValidationFailedError(PERIOD_REQUIRED_MESSAGE, details=[PERIOD_REQUIRED_MESSAGE])

    now = datetime.now(timezone.utc)
    if params.period == "Daily":
        return now - timedelta(hours=24), now
    if params.period == "Weekly":
        return now - timedelta(days=7), now
    return now - timedelta(days=30), now


def _current_stage_start(contract, open_rows: dict[uuid.UUID, object]) -> datetime | None:
    open_row = open_rows.get(contract.id)
    if open_row is not None:
        return open_row.stage_start_date
    if contract.status not in repo.STATUS_TO_STAGE:
        return None
    return contract.updated_at


def _entitled_contract_ids(db: Session, tenant_id: uuid.UUID, user: CurrentUser) -> set[uuid.UUID] | None:
    """`None` means "no restriction" (Tenant Admin); otherwise the explicit allow-set."""
    if user.role not in _SCOPED_ROLES:
        return None
    try:
        user_uuid = uuid.UUID(user.user_id)
    except (ValueError, AttributeError):
        return set()
    return repo.list_owner_role_contract_ids(db, tenant_id, user_uuid, user.role)


def _row_from_metrics(contract, metrics: ContractTurnaroundMetrics | None) -> TurnaroundRowResponse:
    if metrics is None or metrics.estimated_turnaround_days is None:
        return TurnaroundRowResponse(
            contractId=contract.id,
            contractName=contract.contract_name,
            contractType=contract.contract_type,
            estimatedTurnaround=None,
            estimatedTurnaroundNotSet=True,
            estimatedTurnaroundSource="NOT_SET",
            actualTurnaround=metrics.actual_turnaround_days if metrics else None,
            variance=None,
            varianceColor=None,
            excludedFromAverages=True,
        )

    estimated = metrics.estimated_turnaround_days
    actual = metrics.actual_turnaround_days
    variance: Decimal | None = None
    variance_color: str | None = None
    if actual is not None:
        variance = actual - estimated
        variance_color = "RED" if variance > 0 else "GREEN"

    return TurnaroundRowResponse(
        contractId=contract.id,
        contractName=contract.contract_name,
        contractType=contract.contract_type,
        estimatedTurnaround=estimated,
        estimatedTurnaroundNotSet=False,
        estimatedTurnaroundSource=metrics.estimated_turnaround_source,
        actualTurnaround=actual,
        variance=variance,
        varianceColor=variance_color,
        excludedFromAverages=metrics.excluded_from_averages,
    )


def get_turnaround_tab(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, params: TrackerQueryParams
) -> TurnaroundTabResponse:
    window_start, window_end = _validate_and_resolve_window(params)

    entitled_ids = _entitled_contract_ids(db, tenant_id, user)
    contracts = repo.list_tenant_contracts(db, tenant_id)
    if entitled_ids is not None:
        contracts = [c for c in contracts if c.id in entitled_ids]

    # UC10-AF-001: no contracts visible to this user/tenant at all.
    if not contracts:
        return _empty_response(params, NO_CONTRACT_DATA_MESSAGE)

    open_rows = repo.list_open_stage_rows(db, tenant_id)

    staged: list[tuple] = []
    for contract in contracts:
        stage_start = _current_stage_start(contract, open_rows)
        if stage_start is None:
            continue
        if stage_start.tzinfo is None:
            stage_start = stage_start.replace(tzinfo=timezone.utc)
        staged.append((contract, stage_start))

    # UC10-AF-003 / UC10-BR-006: Period or Date Range applied before the other filters.
    in_window = [row for row in staged if window_start <= row[1] <= window_end]
    if not in_window:
        return _empty_response(params, NO_RECORDS_FOR_PERIOD_MESSAGE)

    type_filter = (params.contract_type_filter or "").strip()
    owner_filter = (params.owner_filter or "").strip()
    from app.repositories.tracker_bottleneck import get_user_names

    owner_ids = {c.contract_owner_id for c, _ in in_window if c.contract_owner_id} | {
        c.owner_id for c, _ in in_window if c.owner_id
    }
    owner_names = get_user_names(db, owner_ids)

    filtered: list = []
    for contract, _ in in_window:
        if type_filter and type_filter.lower() != "all" and contract.contract_type.lower() != type_filter.lower():
            continue
        owner_name = owner_names.get(contract.contract_owner_id) or owner_names.get(contract.owner_id)
        if owner_filter and owner_filter.lower() != "all":
            if not owner_name or owner_filter.lower() not in owner_name.lower():
                continue
        filtered.append(contract)

    # UC10-AF-005: Period/Date Range matched, but the Contract Type/Owner combination doesn't.
    if not filtered:
        return _empty_response(params, NO_RECORDS_FOR_FILTERS_MESSAGE)

    filtered.sort(key=lambda c: c.contract_name)
    total = len(filtered)
    page_slice = filtered[params.offset : params.offset + params.page_size]

    metrics_by_contract = repo.get_metrics_by_contract(db, tenant_id, {c.id for c in page_slice})
    rows = [_row_from_metrics(contract, metrics_by_contract.get(contract.id)) for contract in page_slice]

    return TurnaroundTabResponse(
        rows=rows, isEmpty=False, emptyStateMessage=None, totalCount=total, page=params.page, pageSize=params.page_size
    )


def _empty_response(params: TrackerQueryParams, message: str) -> TurnaroundTabResponse:
    return TurnaroundTabResponse(
        rows=[], isEmpty=True, emptyStateMessage=message, totalCount=0, page=params.page, pageSize=params.page_size
    )


def override_estimated_turnaround(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    payload: EstimatedTurnaroundOverrideRequest,
) -> TurnaroundRowResponse:
    entitled_ids = _entitled_contract_ids(db, tenant_id, user)
    contracts = {c.id: c for c in repo.list_tenant_contracts(db, tenant_id)}
    contract = contracts.get(contract_id)
    if contract is None:
        raise NotFoundError("contract not found")
    if entitled_ids is not None and contract_id not in entitled_ids:
        # UC10-BR-009/010/011: scoped roles may not override turnaround data outside their
        # own entitled contracts, even via direct API manipulation.
        raise ForbiddenError("you do not have access to this contract's Tracker data")

    metrics = repo.get_metrics_for_contract(db, tenant_id, contract_id)
    original_value = payload.originalAiSuggestedValue
    if metrics is None:
        metrics = ContractTurnaroundMetrics(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            contract_id=contract_id,
            estimated_turnaround_days=payload.newEstimatedTurnaround,
            estimated_turnaround_source="AI_SUGGESTED",
            actual_turnaround_days=None,
            excluded_from_averages=False,
            created_by=payload.overriddenBy,
            updated_by=payload.overriddenBy,
        )
        db.add(metrics)
    else:
        if original_value is None:
            original_value = metrics.estimated_turnaround_days
        metrics.estimated_turnaround_days = payload.newEstimatedTurnaround
        metrics.excluded_from_averages = False
        metrics.updated_by = payload.overriddenBy

    db.commit()
    db.refresh(metrics)

    # UC10-BR-007: every override is logged with the original AI-suggested value, the new
    # value, the user, and the timestamp -- the platform's standard accept/reject audit rule.
    repo.add_override_log(
        db,
        TurnaroundOverrideLog(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            contract_id=contract_id,
            original_ai_value=original_value,
            new_value=payload.newEstimatedTurnaround,
            override_user_id=payload.overriddenBy,
            override_timestamp=payload.overrideTimestamp,
            decision="OVERRIDDEN",
            created_by=payload.overriddenBy,
            updated_by=payload.overriddenBy,
        ),
    )

    return _row_from_metrics(contract, metrics)
