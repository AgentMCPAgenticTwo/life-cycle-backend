"""Business rules for `GET /api/v1/tracker/cycle-time`: Period/Date-Range validation
(UC10-FV-001), the Period-vs-custom-Date-Range precedence rule (UC10-BR-006), role-scoped
visibility (UC10-BR-005/009/010/011/012), the average-cycle-time-per-stage calculation
(UC10-BR-001) grouped by user and by contract type (UC10-GC-002), and the three empty-state
message tiers (UC10-AF-001/003/005).

Grouping key: `context.json`'s `CycleTimeRowResponse` carries both an optional `ownerName`
and an optional `contractType` on the same row with no further guidance on how "grouped by
user and by contract type" (UC10-GC-002) combines the two dimensions. This module groups by
the full `(stage, ownerName, contractType)` combination -- the most granular reading that
still satisfies both groupings simultaneously -- and records this judgement call in this
task's `blockers`.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ValidationFailedError
from app.models.contract import Contract
from app.repositories import tracker_cycle_time as repo
from app.schemas.tracker_cycle_time import PERIODS, CycleTimeRowResponse, CycleTimeTabResponse, TrackerQueryParams

PERIOD_REQUIRED_MESSAGE = "Period selection is required."
PERIOD_INVALID_MESSAGE = "Period must be one of: Daily, Weekly, Monthly."
DATE_FORMAT_MESSAGE = "Date Range From and Date Range To must be valid dates."
DATE_ORDER_MESSAGE = "Date Range From must be earlier than Date Range To."

NO_CONTRACT_DATA_MESSAGE = "No contract data available to display."
NO_RECORDS_FOR_PERIOD_MESSAGE = "No records found for the selected period."
NO_RECORDS_FOR_FILTERS_MESSAGE = "No records match the selected filters."

STAGE_ORDER = ("Drafting", "Negotiation", "Approval", "Signature")

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


def _entitled_contract_ids(db: Session, tenant_id: uuid.UUID, user: CurrentUser) -> set[uuid.UUID] | None:
    """`None` means "no restriction" (Tenant Admin); otherwise the explicit allow-set."""
    if user.role not in _SCOPED_ROLES:
        return None
    try:
        user_uuid = uuid.UUID(user.user_id)
    except (ValueError, AttributeError):
        return set()
    return repo.list_owner_role_contract_ids(db, tenant_id, user_uuid, user.role)


def get_cycle_time_tab(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, params: TrackerQueryParams
) -> CycleTimeTabResponse:
    window_start, window_end = _validate_and_resolve_window(params)

    entitled_ids = _entitled_contract_ids(db, tenant_id, user)
    contracts = repo.list_tenant_contracts(db, tenant_id)
    if entitled_ids is not None:
        contracts = [c for c in contracts if c.id in entitled_ids]

    # UC10-AF-001: no contracts visible to this user/tenant at all.
    if not contracts:
        return _empty_response(params, NO_CONTRACT_DATA_MESSAGE)

    contracts_by_id: dict[uuid.UUID, Contract] = {c.id: c for c in contracts}
    completed_rows = [row for row in repo.list_completed_stage_rows(db, tenant_id) if row.contract_id in contracts_by_id]

    def _end_date(row) -> datetime:
        end = row.stage_end_date
        return end if end.tzinfo is not None else end.replace(tzinfo=timezone.utc)

    # UC10-BR-001 / UC10-BR-006: only stages completed within the resolved Period/Date Range.
    in_window = [row for row in completed_rows if window_start <= _end_date(row) <= window_end]
    if not in_window:
        return _empty_response(params, NO_RECORDS_FOR_PERIOD_MESSAGE)

    type_filter = (params.contract_type_filter or "").strip()
    owner_filter = (params.owner_filter or "").strip()
    owner_ids = {contracts_by_id[row.contract_id].contract_owner_id for row in in_window} | {
        contracts_by_id[row.contract_id].owner_id for row in in_window if contracts_by_id[row.contract_id].owner_id
    }
    owner_names = repo.get_user_names(db, owner_ids)

    filtered: list[tuple] = []
    for row in in_window:
        contract = contracts_by_id[row.contract_id]
        if type_filter and type_filter.lower() != "all" and contract.contract_type.lower() != type_filter.lower():
            continue
        owner_name = owner_names.get(contract.contract_owner_id) or owner_names.get(contract.owner_id)
        if owner_filter and owner_filter.lower() != "all":
            if not owner_name or owner_filter.lower() not in owner_name.lower():
                continue
        filtered.append((row, contract, owner_name))

    # UC10-AF-005: Period/Date Range matched, but the Contract Type/Owner combination doesn't.
    if not filtered:
        return _empty_response(params, NO_RECORDS_FOR_FILTERS_MESSAGE)

    groups: dict[tuple[str, str | None, str | None], dict] = {}
    for row, contract, owner_name in filtered:
        key = (row.stage, owner_name, contract.contract_type)
        group = groups.setdefault(key, {"total_days": 0.0, "count": 0, "contract_ids": set()})
        duration_days = (_end_date(row) - _as_aware(row.stage_start_date)).total_seconds() / 86400
        group["total_days"] += duration_days
        group["count"] += 1
        group["contract_ids"].add(contract.id)

    def _sort_key(item):
        (stage, owner_name, contract_type), _ = item
        stage_rank = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else len(STAGE_ORDER)
        return (stage_rank, owner_name or "", contract_type or "")

    ordered_groups = sorted(groups.items(), key=_sort_key)
    total = len(ordered_groups)
    page_slice = ordered_groups[params.offset : params.offset + params.page_size]

    rows = [
        CycleTimeRowResponse(
            stage=stage,
            ownerName=owner_name,
            contractType=contract_type,
            contractsOwned=len(group["contract_ids"]),
            averageCycleTime=round(group["total_days"] / group["count"], 2) if group["count"] else None,
        )
        for (stage, owner_name, contract_type), group in page_slice
    ]

    return CycleTimeTabResponse(
        rows=rows, isEmpty=False, emptyStateMessage=None, totalCount=total, page=params.page, pageSize=params.page_size
    )


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _empty_response(params: TrackerQueryParams, message: str) -> CycleTimeTabResponse:
    return CycleTimeTabResponse(
        rows=[], isEmpty=True, emptyStateMessage=message, totalCount=0, page=params.page, pageSize=params.page_size
    )
