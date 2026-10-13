"""Business rules for `GET /api/v1/tracker/ownership`: Period/Date-Range validation
(UC10-FV-001), the Period-vs-custom-Date-Range precedence rule (UC10-BR-006), role-scoped
visibility (UC10-BR-005/009/010/011/012), the Contracts-by-Owner stage-count breakdown
(UC10-GC-001/MF-001), and the three empty-state message tiers (UC10-AF-001/003/005).

Stage/window derivation mirrors the Bottleneck tab (`app.services.tracker_bottleneck`):
`contract_lifecycle_stage_history`'s open row for a contract is its current stage and the
clock used for Period/Date-Range windowing; contracts with no open stage-history row fall
back to a status-derived stage with `contracts.updated_at` as the "entered this status"
proxy (see that module's blockers -- the same gap applies here). Contracts whose status is
"Executed"/"Active" (this codebase's existing executed-contract set, reused from
`app.services.contract_lifecycle.EXECUTED_STATUSES` for consistency) count as "Completed"
for the Ownership tab's stage breakdown rather than being dropped as untrackable.

Grouping key: `OwnershipRowResponse.ownerName` is a required (non-nullable) field, so
contracts with no resolvable owner name (no `contract_owner_id`/`owner_id` match in `users`)
are excluded from this tab's rows -- there is no "Unassigned" bucket in the contract. This
judgement call is recorded in this task's `blockers`.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ValidationFailedError
from app.repositories import tracker_ownership as repo
from app.schemas.tracker_ownership import OwnershipRowResponse, OwnershipTabResponse, PERIODS, TrackerQueryParams
from app.services.contract_lifecycle import EXECUTED_STATUSES

PERIOD_REQUIRED_MESSAGE = "Period selection is required."
PERIOD_INVALID_MESSAGE = "Period must be one of: Daily, Weekly, Monthly."
DATE_FORMAT_MESSAGE = "Date Range From and Date Range To must be valid dates."
DATE_ORDER_MESSAGE = "Date Range From must be earlier than Date Range To."

NO_CONTRACT_DATA_MESSAGE = "No contract data available to display."
NO_RECORDS_FOR_PERIOD_MESSAGE = "No records found for the selected period."
NO_RECORDS_FOR_FILTERS_MESSAGE = "No records match the selected filters."

COMPLETED_STAGE = "Completed"

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


def _current_stage_and_start(
    contract, open_rows: dict[uuid.UUID, object]
) -> tuple[str, datetime] | None:
    open_row = open_rows.get(contract.id)
    if open_row is not None:
        return open_row.stage, open_row.stage_start_date
    if contract.status in EXECUTED_STATUSES:
        return COMPLETED_STAGE, contract.updated_at
    stage = repo.STATUS_TO_STAGE.get(contract.status)
    if stage is None:
        return None
    # No stage-history row exists for this contract yet -- the contract's own `updated_at` is
    # the closest available proxy for "when it entered this status" (see module docstring).
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


def get_ownership_tab(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, params: TrackerQueryParams
) -> OwnershipTabResponse:
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
        if owner_name is None:
            # OwnershipRowResponse.ownerName is required; contracts with no resolvable owner
            # name have nowhere to aggregate to (see module docstring).
            continue
        if owner_filter and owner_filter.lower() != "all":
            if owner_filter.lower() not in owner_name.lower():
                continue
        filtered.append((contract, stage, owner_name))

    # UC10-AF-005: Period/Date Range matched, but the Contract Type/Owner combination doesn't.
    if not filtered:
        return _empty_response(params, NO_RECORDS_FOR_FILTERS_MESSAGE)

    filtered_contract_ids = {contract.id for contract, _, _ in filtered}
    completed_rows = [
        row for row in repo.list_completed_stage_rows(db, tenant_id) if row.contract_id in filtered_contract_ids
    ]
    durations_by_contract: dict[uuid.UUID, list[float]] = {}
    for row in completed_rows:
        end = row.stage_end_date if row.stage_end_date.tzinfo is not None else row.stage_end_date.replace(tzinfo=timezone.utc)
        start = row.stage_start_date if row.stage_start_date.tzinfo is not None else row.stage_start_date.replace(tzinfo=timezone.utc)
        durations_by_contract.setdefault(row.contract_id, []).append((end - start).total_seconds() / 86400)

    groups: dict[str, dict] = {}
    for contract, stage, owner_name in filtered:
        group = groups.setdefault(
            owner_name,
            {
                "contract_ids": set(),
                "inDraftCount": 0,
                "inNegotiationCount": 0,
                "inApprovalCount": 0,
                "inSignatureCount": 0,
                "completedCount": 0,
            },
        )
        group["contract_ids"].add(contract.id)
        if stage == "Drafting":
            group["inDraftCount"] += 1
        elif stage == "Negotiation":
            group["inNegotiationCount"] += 1
        elif stage == "Approval":
            group["inApprovalCount"] += 1
        elif stage == "Signature":
            group["inSignatureCount"] += 1
        elif stage == COMPLETED_STAGE:
            group["completedCount"] += 1

    ordered_owner_names = sorted(groups.keys())
    total = len(ordered_owner_names)
    page_slice = ordered_owner_names[params.offset : params.offset + params.page_size]

    rows = []
    for owner_name in page_slice:
        group = groups[owner_name]
        all_durations = [d for cid in group["contract_ids"] for d in durations_by_contract.get(cid, [])]
        average_cycle_time = round(sum(all_durations) / len(all_durations), 2) if all_durations else None
        rows.append(
            OwnershipRowResponse(
                ownerName=owner_name,
                contractsOwned=len(group["contract_ids"]),
                inDraftCount=group["inDraftCount"],
                inNegotiationCount=group["inNegotiationCount"],
                inApprovalCount=group["inApprovalCount"],
                inSignatureCount=group["inSignatureCount"],
                completedCount=group["completedCount"],
                averageCycleTime=average_cycle_time,
            )
        )

    return OwnershipTabResponse(
        rows=rows, isEmpty=False, emptyStateMessage=None, totalCount=total, page=params.page, pageSize=params.page_size
    )


def _empty_response(params: TrackerQueryParams, message: str) -> OwnershipTabResponse:
    return OwnershipTabResponse(
        rows=[], isEmpty=True, emptyStateMessage=message, totalCount=0, page=params.page, pageSize=params.page_size
    )
