"""Business rules for `POST /api/v1/tracker/export`: Period/Date-Range validation
(UC10-FV-001) and tab/format enum validation, role-scoped visibility (UC10-BR-005/009/010/011)
reused from the `Bottleneck` and `CycleTime` tab services, and the three export-outcome tiers:

- UC10-AF-001: the tenant/role has no contracts at all -> export is unavailable (`success=False`).
- UC10-AF-003: the Period/Date-Range/filters resolve to zero records -> the export still
  succeeds, producing a file that represents "no records" rather than failing.
- UC10-AF-004: an unexpected failure while building the export -> `success=False` with the
  fixed "Export failed. Please try again." message, leaving the caller's on-screen view (which
  this stateless endpoint never touches) unchanged.

The export is a real file (UC10): the rows of the requested tab, for the requested Period/
Date Range and filters, written as a genuine `.xlsx` or `.pdf` by the standard-library
writers in `app.services.export_files` (CLAUDE.md forbids adding a generation library). The
bytes land in `settings.export_storage_dir`, the metadata in `uploaded_files`, and `fileUrl`
points at `GET /api/v1/tracker/exports/{fileId}`, which streams them back.
"""
import os
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.config import settings
from app.errors import NotFoundError, ValidationFailedError
from app.models.uploaded_file import UploadedFile
from app.repositories import files as files_repo
from app.repositories import tracker_bottleneck as repo
from app.schemas.tracker_export import FORMATS, TABS, TrackerExportRequest, TrackerExportResponse
from app.services import export_files

PERIOD_REQUIRED_MESSAGE = "Period selection is required."
PERIOD_INVALID_MESSAGE = "Period must be one of: Daily, Weekly, Monthly."
TAB_INVALID_MESSAGE = "Tab must be one of: Ownership, CycleTime, Bottleneck, Turnaround."
FORMAT_INVALID_MESSAGE = "Format must be one of: Excel, PDF."
DATE_FORMAT_MESSAGE = "Date Range From and Date Range To must be valid dates."
DATE_ORDER_MESSAGE = "Date Range From must be earlier than Date Range To."

NO_CONTRACT_DATA_MESSAGE = "No contract data available to display."
EXPORT_FAILED_MESSAGE = "Export failed. Please try again."
NO_ROWS_PLACEHOLDER = "No records found for the selected period and filters."

# Column headers per tab, in the order the tab's own table shows them.
_TAB_HEADERS = {
    "Ownership": [
        "Owner Name",
        "Contracts Owned",
        "In Draft",
        "In Negotiation",
        "In Approval",
        "In Signature",
        "Completed",
        "Average Cycle Time (days)",
    ],
    "CycleTime": ["Stage", "Owner Name", "Contract Type", "Contracts Owned", "Average Cycle Time (days)"],
    "Bottleneck": ["Contract Name", "Owner Name", "Current Stage", "Days In Current Stage", "Stuck Flag"],
    "Turnaround": [
        "Contract Name",
        "Contract Type",
        "Estimated Turnaround (days)",
        "Estimated Turnaround Source",
        "Actual Turnaround (days)",
        "Variance (days)",
        "Variance Color",
        "Excluded From Averages",
    ],
}

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
        # UC10-AF-003: Period/filters narrowing to zero rows does not fail the export -- the
        # file is still produced, carrying the "no records" line instead of data rows.
        rows = _tab_rows(db, tenant_id, user, payload)
        content = export_files.build_file(
            payload.format,
            _export_title(payload),
            _TAB_HEADERS[payload.tab],
            rows or [[NO_ROWS_PLACEHOLDER]],
        )
        file_url = _persist_export(db, tenant_id, user, payload, content)
    except ValidationFailedError:
        raise
    except Exception:
        # UC10-AF-004: an unexpected failure while building the export.
        db.rollback()
        return TrackerExportResponse(success=False, fileUrl=None, failureMessage=EXPORT_FAILED_MESSAGE)

    return TrackerExportResponse(success=True, fileUrl=file_url, failureMessage=None)


def _export_title(payload: TrackerExportRequest) -> str:
    scope = payload.period or ""
    if payload.dateRangeFrom and payload.dateRangeTo:
        scope = f"{payload.dateRangeFrom} to {payload.dateRangeTo}"
    parts = [f"{payload.tab} Tracker Export", scope]
    if payload.contractTypeFilter:
        parts.append(f"Contract Type: {payload.contractTypeFilter}")
    if payload.ownerFilter:
        parts.append(f"Owner: {payload.ownerFilter}")
    return " -- ".join(part for part in parts if part)


def _persist_export(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    payload: TrackerExportRequest,
    content: bytes,
) -> str:
    """Writes the generated bytes to `settings.export_storage_dir` and records them in
    `uploaded_files` so the download endpoint can find them by id."""
    file_id = uuid.uuid4()
    extension = export_files.EXTENSIONS[payload.format]
    directory = settings.export_storage_dir
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, f"{file_id}.{extension}")
    with open(path, "wb") as handle:
        handle.write(content)

    user_uuid = uuid.UUID(user.user_id)
    files_repo.insert_uploaded_file(
        db,
        UploadedFile(
            id=file_id,
            tenant_id=tenant_id,
            file_name=f"{payload.tab}-tracker-export.{extension}",
            file_size=len(content),
            file_format=extension.upper(),
            storage_url=path,
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )
    db.commit()
    return f"/api/v1/tracker/exports/{file_id}"


def get_export_file(
    db: Session, tenant_id: uuid.UUID, file_id: uuid.UUID
) -> tuple[bytes, str, str]:
    """Returns `(content, content_type, file_name)` for a previously generated export."""
    record = files_repo.get_uploaded_file(db, tenant_id, file_id)
    if record is None or not os.path.isfile(record.storage_url):
        raise NotFoundError("export file not found")
    with open(record.storage_url, "rb") as handle:
        content = handle.read()
    content_type = (
        export_files.CONTENT_TYPES["Excel"]
        if record.file_format.upper() == "XLSX"
        else export_files.CONTENT_TYPES["PDF"]
    )
    return content, content_type, record.file_name


def _cell(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (Decimal, float)):
        return f"{float(value):g}"
    return str(value)


def _tab_rows(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: TrackerExportRequest
) -> list[list[str]]:
    """Dispatches to each tab's own service so the exported file carries exactly the rows the
    tab shows -- same filters, same role scoping, same Period/Date-Range precedence. An empty
    tab (any of the UC10-AF-001/003/005 empty states) yields no rows, not a failure."""
    shim = _ParamsShim(payload)

    if payload.tab == "Ownership":
        from app.services import tracker_ownership as ownership_service

        response = ownership_service.get_ownership_tab(db, tenant_id, user, shim)
        return [
            [
                _cell(row.ownerName),
                _cell(row.contractsOwned),
                _cell(row.inDraftCount),
                _cell(row.inNegotiationCount),
                _cell(row.inApprovalCount),
                _cell(row.inSignatureCount),
                _cell(row.completedCount),
                _cell(row.averageCycleTime),
            ]
            for row in response.rows
        ]

    if payload.tab == "CycleTime":
        from app.services import tracker_cycle_time as cycle_time_service

        response = cycle_time_service.get_cycle_time_tab(db, tenant_id, user, shim)
        return [
            [
                _cell(row.stage),
                _cell(row.ownerName),
                _cell(row.contractType),
                _cell(row.contractsOwned),
                _cell(row.averageCycleTime),
            ]
            for row in response.rows
        ]

    if payload.tab == "Bottleneck":
        from app.services import tracker_bottleneck as bottleneck_service

        response = bottleneck_service.get_bottleneck_tab(db, tenant_id, user, shim)
        return [
            [
                _cell(row.contractName),
                _cell(row.ownerName),
                _cell(row.currentStage),
                _cell(row.daysInCurrentStage),
                _cell(row.stuckFlag),
            ]
            for row in response.rows
        ]

    from app.services import tracker_turnaround as turnaround_service

    response = turnaround_service.get_turnaround_tab(db, tenant_id, user, shim)
    return [
        [
            _cell(row.contractName),
            _cell(row.contractType),
            "" if row.estimatedTurnaroundNotSet else _cell(row.estimatedTurnaround),
            _cell(row.estimatedTurnaroundSource),
            _cell(row.actualTurnaround),
            _cell(row.variance),
            _cell(row.varianceColor),
            _cell(row.excludedFromAverages),
        ]
        for row in response.rows
    ]
