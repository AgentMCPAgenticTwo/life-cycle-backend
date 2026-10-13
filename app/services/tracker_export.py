"""Business rules for `POST /api/v1/tracker/export`: Period/Date-Range validation
(UC10-FV-001) and tab/format enum validation, role-scoped visibility (UC10-BR-005/009/010/011)
reused from the `Bottleneck` and `CycleTime` tab services, and the three export-outcome tiers:

- UC10-AF-001: the tenant/role has no contracts at all -> export is unavailable (`success=False`).
- UC10-AF-003: the Period/Date-Range/filters resolve to zero records -> the export still
  succeeds, producing a file that represents "no records" rather than failing.
- UC10-AF-004: an unexpected failure while building the export -> `success=False` with the
  fixed "Export failed. Please try again." message, leaving the caller's on-screen view (which
  this stateless endpoint never touches) unchanged.

No Excel/PDF generation library is available in this repo and CLAUDE.md forbids adding one, so
--  consistent with this codebase's existing "file" DTOs (see `app.services.signers`'
`AuditCertificateResponse.file_url`, which is a synthesized path, not a real generated file --
this writes no bytes and returns a deterministic mock `fileUrl` instead.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ValidationFailedError
from app.repositories import tracker_bottleneck as repo
from app.schemas.tracker_export import FORMATS, TABS, TrackerExportRequest, TrackerExportResponse

PERIOD_REQUIRED_MESSAGE = "Period selection is required."
PERIOD_INVALID_MESSAGE = "Period must be one of: Daily, Weekly, Monthly."
TAB_INVALID_MESSAGE = "Tab must be one of: Ownership, CycleTime, Bottleneck, Turnaround."
FORMAT_INVALID_MESSAGE = "Format must be one of: Excel, PDF."
DATE_FORMAT_MESSAGE = "Date Range From and Date Range To must be valid dates."
DATE_ORDER_MESSAGE = "Date Range From must be earlier than Date Range To."

NO_CONTRACT_DATA_MESSAGE = "No contract data available to display."
EXPORT_FAILED_MESSAGE = "Export failed. Please try again."

_EXTENSIONS = {"Excel": "xlsx", "PDF": "pdf"}

# Same role-scoping rule as the other tabs (UC10-BR-005/009/010/011): Tenant Admin sees
# everything, the other three roles are limited to contracts naming them in `contract_owners`.
_SCOPED_ROLES = {"CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER"}


class _ParamsShim:
    """Adapts `TrackerExportRequest`'s filter fields to the duck-typed interface the
    `tracker_bottleneck`/`tracker_cycle_time` tab services expect (`TrackerQueryParams`),
    requesting every row in one page since export has no paging concept of its own.
    """

    def __init__(self, payload: TrackerExportRequest) -> None:
        self.period = payload.period
        self.contract_type_filter = payload.contractTypeFilter
        self.owner_filter = payload.ownerFilter
        self.date_range_from = payload.dateRangeFrom
        self.date_range_to = payload.dateRangeTo
        self.page = 1
        self.page_size = 10_000

    @property
    def offset(self) -> int:
        return 0


def _parse_date(value: str | None) -> date | None:
    if value is None or not value.strip():
        return None
    try:
        return date.fromisoformat(value.strip())
    except ValueError:
        raise ValidationFailedError(DATE_FORMAT_MESSAGE, details=[DATE_FORMAT_MESSAGE])


def _validate_and_resolve_window(payload: TrackerExportRequest) -> tuple[datetime, datetime]:
    date_from = _parse_date(payload.dateRangeFrom)
    date_to = _parse_date(payload.dateRangeTo)

    if date_from is not None and date_to is not None:
        if not date_from < date_to:
            raise ValidationFailedError(DATE_ORDER_MESSAGE, details=[DATE_ORDER_MESSAGE])
        window_start = datetime.combine(date_from, datetime.min.time(), tzinfo=timezone.utc)
        window_end = datetime.combine(date_to, datetime.max.time(), tzinfo=timezone.utc)
        return window_start, window_end

    if payload.period is not None and payload.period not in ("Daily", "Weekly", "Monthly"):
        raise ValidationFailedError(PERIOD_INVALID_MESSAGE, details=[PERIOD_INVALID_MESSAGE])

    if payload.period is None:
        raise ValidationFailedError(PERIOD_REQUIRED_MESSAGE, details=[PERIOD_REQUIRED_MESSAGE])

    now = datetime.now(timezone.utc)
    if payload.period == "Daily":
        return now - timedelta(hours=24), now
    if payload.period == "Weekly":
        return now - timedelta(days=7), now
    return now - timedelta(days=30), now


def _validate_enums(payload: TrackerExportRequest) -> None:
    if payload.tab not in TABS:
        raise ValidationFailedError(TAB_INVALID_MESSAGE, details=[TAB_INVALID_MESSAGE])
    if payload.format not in FORMATS:
        raise ValidationFailedError(FORMAT_INVALID_MESSAGE, details=[FORMAT_INVALID_MESSAGE])


def _entitled_contract_ids(db: Session, tenant_id: uuid.UUID, user: CurrentUser) -> set[uuid.UUID] | None:
    """`None` means "no restriction" (Tenant Admin); otherwise the explicit allow-set."""
    if user.role not in _SCOPED_ROLES:
        return None
    try:
        user_uuid = uuid.UUID(user.user_id)
    except (ValueError, AttributeError):
        return set()
    return repo.list_owner_role_contract_ids(db, tenant_id, user_uuid, user.role)


def _has_any_entitled_contract(db: Session, tenant_id: uuid.UUID, user: CurrentUser) -> bool:
    entitled_ids = _entitled_contract_ids(db, tenant_id, user)
    contracts = repo.list_tenant_contracts(db, tenant_id)
    if entitled_ids is not None:
        contracts = [c for c in contracts if c.id in entitled_ids]
    return bool(contracts)


def _as_aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def export_tracker_tab(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: TrackerExportRequest
) -> TrackerExportResponse:
    _validate_enums(payload)
    _validate_and_resolve_window(payload)

    # UC10-AF-001: no contract data at all for this tenant/role -> no export is available.
    if not _has_any_entitled_contract(db, tenant_id, user):
        return TrackerExportResponse(success=False, fileUrl=None, failureMessage=NO_CONTRACT_DATA_MESSAGE)

    try:
        # UC10-AF-003: Period/filters narrowing to zero rows does not fail the export -- it
        # still produces a file (this codebase has no byte-generation backend to vary the
        # file's content by, so the only observable difference is the fixed success response;
        # see this task's `blockers`).
        _ = _tab_has_rows(db, tenant_id, user, payload)
    except ValidationFailedError:
        raise
    except Exception:
        # UC10-AF-004: an unexpected failure while building the export.
        return TrackerExportResponse(success=False, fileUrl=None, failureMessage=EXPORT_FAILED_MESSAGE)

    extension = _EXTENSIONS[payload.format]
    file_url = f"/files/tracker-exports/{uuid.uuid4()}.{extension}"
    return TrackerExportResponse(success=True, fileUrl=file_url, failureMessage=None)


def _tab_has_rows(db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: TrackerExportRequest) -> bool:
    """Dispatches to each tab's own row-producing logic so export honors the same filters,
    role scoping and Period/Date-Range precedence as the tab the user is looking at.

    `Bottleneck` and `CycleTime` reuse their real tab services end to end. `Ownership` and
    `Turnaround` have no dedicated tab service in this codebase yet (separate tasks own those
    endpoints), so this computes just enough -- entitled contracts within the resolved window
    and filters -- to know whether the export has any rows; see this task's `blockers`.
    """
    if payload.tab == "Bottleneck":
        from app.services import tracker_bottleneck as bottleneck_service

        response = bottleneck_service.get_bottleneck_tab(db, tenant_id, user, _ParamsShim(payload))
        return not response.isEmpty

    if payload.tab == "CycleTime":
        from app.services import tracker_cycle_time as cycle_time_service

        response = cycle_time_service.get_cycle_time_tab(db, tenant_id, user, _ParamsShim(payload))
        return not response.isEmpty

    # Ownership / Turnaround: both are contract-level (not stage-level) views, so the window
    # is resolved against each contract's own `created_at` as the closest available proxy for
    # "when this contract entered the tenant's tracked population" -- see this task's `blockers`.
    window_start, window_end = _validate_and_resolve_window(payload)
    entitled_ids = _entitled_contract_ids(db, tenant_id, user)
    contracts = repo.list_tenant_contracts(db, tenant_id)
    if entitled_ids is not None:
        contracts = [c for c in contracts if c.id in entitled_ids]

    type_filter = (payload.contractTypeFilter or "").strip()
    owner_filter = (payload.ownerFilter or "").strip()
    owner_ids = {c.contract_owner_id for c in contracts if c.contract_owner_id} | {
        c.owner_id for c in contracts if c.owner_id
    }
    owner_names = repo.get_user_names(db, owner_ids)

    for contract in contracts:
        created_at = _as_aware(contract.created_at)
        if not (window_start <= created_at <= window_end):
            continue
        if type_filter and type_filter.lower() != "all" and contract.contract_type.lower() != type_filter.lower():
            continue
        if owner_filter and owner_filter.lower() != "all":
            owner_name = owner_names.get(contract.contract_owner_id) or owner_names.get(contract.owner_id)
            if not owner_name or owner_filter.lower() not in owner_name.lower():
                continue
        return True
    return False
