"""Business rules for `GET /api/v1/tracker/bottleneck`: Period/Date-Range validation
(UC10-FV-001), the Period-vs-custom-Date-Range precedence rule (UC10-BR-006), role-scoped
visibility (UC10-BR-005/009/010/011/012), the tenant-configured stuck-flag threshold per
stage (UC10-BR-002/GC-003), and the three empty-state message tiers (UC10-AF-001/003/005).
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ValidationFailedError
from app.repositories import tracker_bottleneck as repo
from app.schemas.tracker_bottleneck import PERIODS, BottleneckRowResponse, BottleneckTabResponse, TrackerQueryParams

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


def _validate_and_resolve_window(params: TrackerQueryParams) -> tuple[datetime | None, datetime | None]:
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


def _current_stage_and_start(
    contract, open_rows: dict[uuid.UUID, object]
) -> tuple[str, datetime] | None:
    open_row = open_rows.get(contract.id)
    if open_row is not None:
        return open_row.stage, open_row.stage_start_date
    stage = repo.STATUS_TO_STAGE.get(contract.status)
    if stage is None:
        return None
    # No stage-history row exists for this contract yet (see this module's blockers) -- the
    # contract's own `updated_at` is the closest available proxy for "when it entered this status".
    return stage, contract.updated_at


def _entitled_contract_ids(db: Session, tenant_id: uuid.UUID, user: CurrentUser) -> set[uuid.UUID] | None:
    """`None` means "no restriction" (Tenant Admin); otherwise the explicit allow-set."""
    if user.role not in _SCOPED_ROLES:
        return None
    try:
        user_uuid = uuid.UUID(user.user_id)
    except (ValueError, AttributeError):
        return set()
    return repo.list_owner_role_contract_ids(db, tenant_id, user_uuid, user.role)


def get_bottleneck_tab(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, params: TrackerQueryParams
) -> BottleneckTabResponse:
    window_start, window_end = _validate_and_resolve_window(params)

    entitled_ids = _entitled_contract_ids(db, tenant_id, user)
    contracts = repo.list_tenant_contracts(db, tenant_id)
    if entitled_ids is not None:
        contracts = [c for c in contracts if c.id in entitled_ids]

    # UC10-AF-001: no contracts visible to this user/tenant at all.
    if not contracts:
        return _empty_response(params, NO_CONTRACT_DATA_MESSAGE)

    open_rows = repo.list_open_stage_rows(db, tenant_id)
    thresholds = repo.get_thresholds(db, tenant_id)
    now = datetime.now(timezone.utc)

    staged: list[tuple] = []
    for contract in contracts:
        derived = _current_stage_and_start(contract, open_rows)
        if derived is None:
            continue
        stage, stage_start = derived
        if stage_start.tzinfo is None:
            stage_start = stage_start.replace(tzinfo=timezone.utc)
        staged.append((contract, stage, stage_start))

    # UC10-AF-003 / UC10-BR-006: Period or Date Range applied before the other filters.
    in_window = [row for row in staged if window_start <= row[2] <= window_end]
    if not in_window:
        return _empty_response(params, NO_RECORDS_FOR_PERIOD_MESSAGE)

    type_filter = (params.contract_type_filter or "").strip()
    owner_filter = (params.owner_filter or "").strip()
    owner_ids = {c.contract_owner_id for c, _, _ in in_window if c.contract_owner_id} | {
        c.owner_id for c, _, _ in in_window if c.owner_id
    }
    owner_names = repo.get_user_names(db, owner_ids)

    filtered: list[tuple] = []
    for contract, stage, stage_start in in_window:
        if type_filter and type_filter.lower() != "all" and contract.contract_type.lower() != type_filter.lower():
            continue
        owner_name = owner_names.get(contract.contract_owner_id) or owner_names.get(contract.owner_id)
        if owner_filter and owner_filter.lower() != "all":
            if not owner_name or owner_filter.lower() not in owner_name.lower():
                continue
        filtered.append((contract, stage, stage_start, owner_name))

    # UC10-AF-005: Period/Date Range matched, but the Contract Type/Owner combination doesn't.
    if not filtered:
        return _empty_response(params, NO_RECORDS_FOR_FILTERS_MESSAGE)

    filtered.sort(key=lambda row: row[0].contract_name)
    total = len(filtered)
    page_slice = filtered[params.offset : params.offset + params.page_size]

    rows = []
    for contract, stage, stage_start, owner_name in page_slice:
        days_in_stage = max(0, (now - stage_start).days)
        threshold = thresholds.get(stage, repo.DEFAULT_THRESHOLDS.get(stage, 5))
        stuck_flag = "Yes" if days_in_stage > threshold else "No"
        rows.append(
            BottleneckRowResponse(
                contractId=contract.id,
                contractName=contract.contract_name,
                ownerName=owner_name,
                currentStage=stage,
                daysInCurrentStage=days_in_stage,
                stuckFlag=stuck_flag,
            )
        )

    return BottleneckTabResponse(
        rows=rows, isEmpty=False, emptyStateMessage=None, totalCount=total, page=params.page, pageSize=params.page_size
    )


def _empty_response(params: TrackerQueryParams, message: str) -> BottleneckTabResponse:
    return BottleneckTabResponse(
        rows=[], isEmpty=True, emptyStateMessage=message, totalCount=0, page=params.page, pageSize=params.page_size
    )
