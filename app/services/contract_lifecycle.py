"""Business rules for the life-cycle-uc8-uc9 module's contract sub-resources: Document tab,
Versions tab, immutable Activity Log, Folder/Tag assignment, Obligations & Renewal screen,
and the Renew/Amend/Terminate lifecycle actions -- see CLAUDE.md's "life cycle uc8 uc9"
module section and this task's stories (T-CONTRACTS-API/TASK.md, UC8-*/UC9-*).

`GET /api/v1/contracts` and `GET /api/v1/contracts/{contractId}` (search/list and detail) are
NOT implemented here -- see this task's `blockers` for the path collision with uc123's
already-shipped `app.services.contracts`/`app.routers.contracts`, which this module must not
rewrite.
"""
import re
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from app.models.contract import Contract
from app.models.contract_lifecycle import (
    ActivityLogEntry,
    ContractFolderTag,
    ContractLifecycleAction,
    Obligation,
    ObligationAuditLog,
)
from app.models.user import User
from app.repositories import contract_lifecycle as repo
from app.schemas.contract_lifecycle import (
    ActivityLogEntryResponse,
    ActivityLogListResponse,
    AssignFolderTagRequest,
    ContractDocumentResponse,
    ContractFolderTagResponse,
    ContractVersionListResponse,
    ContractVersionResponse,
    CreateObligationRequest,
    DocumentDownloadResponse,
    FolderTagOptionResponse,
    LinkedContractActionResponse,
    ObligationListResponse,
    ObligationResponse,
    RenewalPanelResponse,
    TerminateContractRequest,
    UpdateObligationRequest,
)
from app.schemas.pagination import PageParams

# UC8-BR-006: "the system's supported upload size from UC2" is never given a literal number
# anywhere in this task's contract or stories -- this constant is a judgement call (25 MiB),
# recorded in this task's `blockers`.
OVERSIZED_FILE_BYTES = 25 * 1024 * 1024

OBLIGATION_TYPES = {"Deliverable", "Payment Milestone", "SLA", "Reporting"}
OBLIGATION_STATUSES = {"Pending", "In Progress", "Completed", "Overdue"}
EXECUTED_STATUSES = {"Executed", "Active"}
RENEWAL_THRESHOLDS_DAYS = (90, 60, 30)

_NOT_EXECUTED_MESSAGE = "Obligations are available only after a contract is fully executed"
_NO_PERMISSION_MESSAGE = "You do not have permission to view this contract."
_DUPLICATE_ACTION_MESSAGE = "A renewal action is already in progress for this contract"
_NOTICE_PERIOD_DAYS_RE = re.compile(r"(\d+)")


def _user_uuid(user: CurrentUser) -> uuid.UUID:
    return uuid.UUID(user.user_id)


def _resolve_user_name(db: Session, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    row = db.query(User).filter(User.id == user_id).first()
    return row.name if row is not None else "Unknown"


def _is_owner(contract: Contract, user_id: uuid.UUID) -> bool:
    if contract.owner_id is not None:
        return contract.owner_id == user_id
    return contract.contract_owner_id == user_id


def _get_contract_or_404(db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID) -> Contract:
    contract = repo.get_contract(db, tenant_id, contract_id)
    if contract is None:
        raise NotFoundError("contract not found")
    return contract


def _assert_viewable(db: Session, user: CurrentUser, contract: Contract) -> None:
    """TENANT_ADMIN always; CONTRACT_OWNER only if they own it; LEGAL_REVIEWER/APPROVER only
    if assigned -- UC8-BR-001/BR-007/BR-008/BR-009/BR-010's direct-link access control."""
    if user.role == "TENANT_ADMIN":
        return
    user_id = _user_uuid(user)
    if user.role == "CONTRACT_OWNER":
        if _is_owner(contract, user_id):
            return
        raise ForbiddenError(_NO_PERMISSION_MESSAGE)
    if user.role in ("LEGAL_REVIEWER", "APPROVER"):
        if repo.get_assignment(db, contract.id, user_id, user.role) is not None:
            return
        raise ForbiddenError(_NO_PERMISSION_MESSAGE)
    raise ForbiddenError(_NO_PERMISSION_MESSAGE)


def _assert_owner_or_admin(user: CurrentUser, contract: Contract) -> None:
    """For write actions restricted to TENANT_ADMIN/CONTRACT_OWNER at the role layer -- this
    adds the per-resource ownership check UC8-BR-008 requires on top of that."""
    if user.role == "TENANT_ADMIN":
        return
    if user.role == "CONTRACT_OWNER" and _is_owner(contract, _user_uuid(user)):
        return
    raise ForbiddenError(_NO_PERMISSION_MESSAGE)


def _require_executed_or_active(contract: Contract) -> None:
    if contract.status not in EXECUTED_STATUSES:
        raise ConflictError(_NOT_EXECUTED_MESSAGE)


# --------------------------------------------------------------------------- Document tab ---


def get_document(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> ContractDocumentResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_viewable(db, user, contract)
    doc = repo.get_current_document(db, contract.id)
    if doc is None:
        return ContractDocumentResponse(
            contractId=contract.id,
            fileName="",
            fileType="",
            fileSizeBytes=0,
            isOversized=False,
            isCorruptedOrMissing=True,
            downloadEnabled=False,
        )
    is_oversized = doc.file_size_bytes > OVERSIZED_FILE_BYTES
    download_enabled = not (is_oversized or doc.is_corrupted_or_missing)
    return ContractDocumentResponse(
        contractId=contract.id,
        documentUrl=doc.storage_path if download_enabled else None,
        fileName=doc.file_name,
        fileType=doc.file_type,
        fileSizeBytes=doc.file_size_bytes,
        isOversized=is_oversized,
        isCorruptedOrMissing=doc.is_corrupted_or_missing,
        downloadEnabled=download_enabled,
        unavailableComment="File unavailable" if is_oversized else None,
    )


def download_document(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> DocumentDownloadResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_viewable(db, user, contract)
    doc = repo.get_current_document(db, contract.id)
    # UC8-AF-005: corrupted/missing file -- same message for either cause, no file transferred.
    if doc is None or doc.is_corrupted_or_missing:
        return DocumentDownloadResponse(
            success=False,
            errorMessage="This document could not be retrieved. Please contact your administrator.",
        )
    # UC8-BR-006: oversized documents are blocked from download with 'File unavailable'.
    if doc.file_size_bytes > OVERSIZED_FILE_BYTES:
        return DocumentDownloadResponse(success=False, errorMessage="File unavailable")
    return DocumentDownloadResponse(success=True, fileUrl=doc.storage_path)


# --------------------------------------------------------------------------- Versions tab ---


def list_versions(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, page_params: PageParams
) -> ContractVersionListResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_viewable(db, user, contract)
    rows, total = repo.list_versions(db, contract.id, offset=page_params.offset, limit=page_params.page_size)
    items = [
        ContractVersionResponse(
            versionId=row.id,
            versionNumber=row.version_number,
            createdAt=row.created_at,
            createdBy=_resolve_user_name(db, row.created_by) or "Unknown",
            changeSummary=row.change_summary,
        )
        for row in rows
    ]
    return ContractVersionListResponse(
        items=items, page=page_params.page, pageSize=page_params.page_size, totalCount=total
    )


# ------------------------------------------------------------------------ Activity Log tab ---


def list_activity_log(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, page_params: PageParams
) -> ActivityLogListResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_viewable(db, user, contract)
    rows, total = repo.list_activity_log(
        db, contract.id, offset=page_params.offset, limit=page_params.page_size
    )
    items = [
        ActivityLogEntryResponse(
            entryId=row.id,
            contractId=row.contract_id,
            actionType=row.action_type,
            performedBy=_resolve_user_name(db, row.performed_by) or "Unknown",
            performedAt=row.performed_at,
            details=row.details,
        )
        for row in rows
    ]
    return ActivityLogListResponse(
        items=items, page=page_params.page, pageSize=page_params.page_size, totalCount=total
    )


# --------------------------------------------------------------------------- Folder / Tag ---


def list_folder_tag_options(db: Session, tenant_id: uuid.UUID) -> list[FolderTagOptionResponse]:
    rows = repo.list_folder_tags_for_tenant(db, tenant_id)
    return [FolderTagOptionResponse(id=row.id, name=row.name, kind=row.kind) for row in rows]


def _folder_tags_response(db: Session, contract_id: uuid.UUID) -> ContractFolderTagResponse:
    pairs = repo.list_contract_folder_tags(db, contract_id)
    return ContractFolderTagResponse(
        contractId=contract_id,
        folderTags=[
            FolderTagOptionResponse(id=tag.id, name=tag.name, kind=tag.kind) for _link, tag in pairs
        ],
    )


def assign_folder_tags(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    payload: AssignFolderTagRequest,
) -> ContractFolderTagResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_owner_or_admin(user, contract)
    if not payload.folderTagIds:
        raise ValidationFailedError(
            "At least one folder or tag must be selected.",
            details=["folderTagIds must contain at least one id."],
        )
    user_id = _user_uuid(user)
    added_names: list[str] = []
    for folder_tag_id in payload.folderTagIds:
        tag = repo.get_folder_tag(db, tenant_id, folder_tag_id)
        if tag is None:
            raise ValidationFailedError(
                "Folder/tag not found.", details=[f"folder/tag {folder_tag_id} not found."]
            )
        if repo.get_contract_folder_tag(db, contract.id, tag.id) is None:
            repo.insert_contract_folder_tag(
                db,
                ContractFolderTag(
                    id=uuid.uuid4(),
                    contract_id=contract.id,
                    folder_tag_id=tag.id,
                    created_by=user_id,
                    updated_by=user_id,
                ),
            )
            added_names.append(tag.name)
    if added_names:
        repo.insert_activity_log(
            db,
            ActivityLogEntry(
                id=uuid.uuid4(),
                contract_id=contract.id,
                action_type="TAG",
                performed_by=user_id,
                performed_at=datetime.now(timezone.utc),
                details=f"Assigned folder/tag(s): {', '.join(added_names)}",
                created_by=user_id,
            ),
        )
    db.commit()
    return _folder_tags_response(db, contract.id)


# --------------------------------------------------------------------------- Obligations ---


def _obligation_to_response(db: Session, obligation: Obligation, *, read_only: bool) -> ObligationResponse:
    return ObligationResponse(
        obligationId=obligation.id,
        contractId=obligation.contract_id,
        obligationDescription=obligation.obligation_description,
        obligationType=obligation.obligation_type,
        owner=_resolve_user_name(db, obligation.owner_id),
        dueDate=obligation.due_date,
        status=obligation.status,
        source=obligation.source,
        confirmationLabel=obligation.confirmation_label,
        evidenceReference=obligation.evidence_reference,
        readOnly=read_only,
    )


def _apply_overdue_transition(db: Session, obligation: Obligation, today: date) -> None:
    """UC9-BR-002/BR-015: Pending/In Progress obligations whose Due Date has passed
    automatically become Overdue. No scheduler exists in this service, so this is applied
    lazily whenever an obligation is read or written -- functionally equivalent for a
    request/response API with no background jobs. Recorded in this task's `blockers`."""
    if obligation.due_date is not None and obligation.due_date < today and obligation.status in (
        "Pending",
        "In Progress",
    ):
        obligation.status = "Overdue"
        db.flush()


def _parse_owner_id(owner: str) -> uuid.UUID:
    # The contract types `CreateObligationRequest.owner`/`UpdateObligationRequest.owner` as
    # `string`, but the persisted `obligations.owner_id` column is a UUID FK to `users` (per
    # context.json's table). The Owner field is populated from an "Owner dropdown" of tenant
    # users (UC9-FV-001/MF-001), so this is interpreted as the selected user's id carried as a
    # string, not a free-text name. Recorded in this task's `blockers`.
    try:
        return uuid.UUID(owner)
    except ValueError:
        raise ValidationFailedError(
            "owner must be a valid user id.", details=["owner must be a valid user id."]
        )


def list_obligations(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, page_params: PageParams
) -> ObligationListResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_viewable(db, user, contract)
    _require_executed_or_active(contract)
    read_only = user.role == "LEGAL_REVIEWER"
    today = date.today()
    rows, total = repo.list_obligations(
        db, contract.id, offset=page_params.offset, limit=page_params.page_size
    )
    for row in rows:
        _apply_overdue_transition(db, row, today)
    db.commit()
    items = [_obligation_to_response(db, row, read_only=read_only) for row in rows]
    return ObligationListResponse(
        items=items, page=page_params.page, pageSize=page_params.page_size, totalCount=total
    )


def create_obligation(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    payload: CreateObligationRequest,
) -> ObligationResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_owner_or_admin(user, contract)
    _require_executed_or_active(contract)
    if payload.obligationType not in OBLIGATION_TYPES:
        raise ValidationFailedError(
            "Invalid obligation type.", details=[f"obligationType must be one of {sorted(OBLIGATION_TYPES)}."]
        )
    if payload.status not in OBLIGATION_STATUSES:
        raise ValidationFailedError(
            "Invalid status.", details=[f"status must be one of {sorted(OBLIGATION_STATUSES)}."]
        )
    if payload.dueDate < date.today():
        raise ValidationFailedError(
            "Due date cannot be in the past", details=["dueDate must be on or after today."]
        )
    owner_id = _parse_owner_id(payload.owner)
    user_id = _user_uuid(user)
    obligation = Obligation(
        id=uuid.uuid4(),
        contract_id=contract.id,
        obligation_description=payload.obligationDescription,
        obligation_type=payload.obligationType,
        owner_id=owner_id,
        due_date=payload.dueDate,
        status=payload.status,
        source="Manually Added",
        confirmation_label="Confirmed",
        created_by=user_id,
        updated_by=user_id,
    )
    repo.insert_obligation(db, obligation)
    repo.insert_obligation_audit(
        db,
        ObligationAuditLog(
            id=uuid.uuid4(),
            contract_id=contract.id,
            obligation_id=obligation.id,
            action_type="CREATE",
            field_name="obligationDescription",
            before_value=None,
            after_value=payload.obligationDescription,
            performed_by=user_id,
            performed_at=datetime.now(timezone.utc),
            created_by=user_id,
        ),
    )
    db.commit()
    return _obligation_to_response(db, obligation, read_only=False)


_FIELD_MAP = {
    "obligationDescription": "obligation_description",
    "obligationType": "obligation_type",
    "owner": "owner_id",
    "dueDate": "due_date",
    "status": "status",
    "evidenceReference": "evidence_reference",
}


def update_obligation(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    obligation_id: uuid.UUID,
    payload: UpdateObligationRequest,
) -> ObligationResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_owner_or_admin(user, contract)
    _require_executed_or_active(contract)
    obligation = repo.get_obligation(db, contract.id, obligation_id)
    if obligation is None:
        raise NotFoundError("obligation not found")
    today = date.today()
    _apply_overdue_transition(db, obligation, today)

    if payload.obligationType is not None and payload.obligationType not in OBLIGATION_TYPES:
        raise ValidationFailedError(
            "Invalid obligation type.", details=[f"obligationType must be one of {sorted(OBLIGATION_TYPES)}."]
        )
    if payload.dueDate is not None and payload.dueDate < today:
        raise ValidationFailedError(
            "Due date cannot be in the past", details=["dueDate must be on or after today."]
        )
    if payload.status is not None and payload.status not in OBLIGATION_STATUSES:
        raise ValidationFailedError(
            "Invalid status.", details=[f"status must be one of {sorted(OBLIGATION_STATUSES)}."]
        )
    # UC9-BR-013/BR-014: Status may only advance Pending -> In Progress -> Completed, and
    # Completed requires evidence.
    if payload.status is not None and payload.status != obligation.status:
        if payload.status == "In Progress" and obligation.status != "Pending":
            raise ConflictError("Status can only move to 'In Progress' from 'Pending'.")
        if payload.status == "Completed":
            if obligation.status != "In Progress":
                raise ConflictError("Status can only move to 'Completed' from 'In Progress'.")
            evidence = payload.evidenceReference or obligation.evidence_reference
            if not evidence:
                raise ValidationFailedError(
                    "Evidence is required to mark this obligation Completed.",
                    details=["evidenceReference is required when status is Completed."],
                )

    user_id = _user_uuid(user)
    now = datetime.now(timezone.utc)
    changed_any_core_field = False
    updates: dict[str, object] = {}
    if payload.obligationDescription is not None:
        updates["obligationDescription"] = payload.obligationDescription
    if payload.obligationType is not None:
        updates["obligationType"] = payload.obligationType
    if payload.owner is not None:
        updates["owner"] = _parse_owner_id(payload.owner)
    if payload.dueDate is not None:
        updates["dueDate"] = payload.dueDate
    if payload.status is not None:
        updates["status"] = payload.status
    if payload.evidenceReference is not None:
        updates["evidenceReference"] = payload.evidenceReference

    for wire_name, value in updates.items():
        attr = _FIELD_MAP[wire_name]
        before = getattr(obligation, attr)
        if before == value:
            continue
        repo.insert_obligation_audit(
            db,
            ObligationAuditLog(
                id=uuid.uuid4(),
                contract_id=contract.id,
                obligation_id=obligation.id,
                action_type="EDIT",
                field_name=wire_name,
                before_value=str(before) if before is not None else None,
                after_value=str(value) if value is not None else None,
                performed_by=user_id,
                performed_at=now,
                created_by=user_id,
            ),
        )
        setattr(obligation, attr, value)
        if wire_name != "evidenceReference":
            changed_any_core_field = True

    # UC9-BR-005: any edit to the AI-suggested fields confirms the obligation.
    if changed_any_core_field and obligation.confirmation_label == "AI Suggested":
        obligation.confirmation_label = "Confirmed"

    obligation.updated_by = user_id
    db.commit()
    read_only = user.role == "LEGAL_REVIEWER"
    return _obligation_to_response(db, obligation, read_only=read_only)


def accept_obligation(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, obligation_id: uuid.UUID
) -> ObligationResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_owner_or_admin(user, contract)
    _require_executed_or_active(contract)
    obligation = repo.get_obligation(db, contract.id, obligation_id)
    if obligation is None:
        raise NotFoundError("obligation not found")
    user_id = _user_uuid(user)
    if obligation.confirmation_label != "Confirmed":
        repo.insert_obligation_audit(
            db,
            ObligationAuditLog(
                id=uuid.uuid4(),
                contract_id=contract.id,
                obligation_id=obligation.id,
                action_type="ACCEPT",
                field_name="confirmationLabel",
                before_value=obligation.confirmation_label,
                after_value="Confirmed",
                performed_by=user_id,
                performed_at=datetime.now(timezone.utc),
                created_by=user_id,
            ),
        )
        obligation.confirmation_label = "Confirmed"
        obligation.updated_by = user_id
        db.commit()
    read_only = user.role == "LEGAL_REVIEWER"
    return _obligation_to_response(db, obligation, read_only=read_only)


# ------------------------------------------------------------------------------- Renewal ---


def _parse_notice_period_days(notice_period_text: str | None) -> int | None:
    if not notice_period_text:
        return None
    match = _NOTICE_PERIOD_DAYS_RE.search(notice_period_text)
    return int(match.group(1)) if match else None


def _compute_renewal_alert(contract: Contract) -> tuple[str | None, int | None]:
    """UC9-BR-003: a banner at exactly 90/60/30 days before the Contract End Date, and
    separately before the Notice Period deadline. `notice_period` is a free-text column
    (e.g. '30 days') per context.json, not a structured duration -- the leading integer is
    parsed out to compute the Notice Period deadline; unparsable text skips that alert.
    Recorded in this task's `blockers`."""
    today = date.today()
    candidates: list[tuple[int, str]] = []
    if contract.end_date is not None:
        days = (contract.end_date - today).days
        if days in RENEWAL_THRESHOLDS_DAYS:
            candidates.append((days, "Contract End Date"))
        notice_days = _parse_notice_period_days(contract.notice_period_text)
        if notice_days is not None:
            deadline = contract.end_date - timedelta(days=notice_days)
            days2 = (deadline - today).days
            if days2 in RENEWAL_THRESHOLDS_DAYS:
                candidates.append((days2, "Notice Period deadline"))
    if not candidates:
        return None, None
    days, basis = min(candidates, key=lambda c: c[0])
    return f"Renewal action required: {days} days remaining before the {basis}.", days


def get_renewal_panel(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> RenewalPanelResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _assert_viewable(db, user, contract)
    _require_executed_or_active(contract)
    banner, threshold_days = _compute_renewal_alert(contract)
    read_only = user.role == "LEGAL_REVIEWER"
    today = date.today()
    rows, _total = repo.list_obligations(db, contract.id, offset=0, limit=1000)
    for row in rows:
        _apply_overdue_transition(db, row, today)
    db.commit()
    obligations = [_obligation_to_response(db, row, read_only=read_only) for row in rows]
    latest_action = repo.get_latest_lifecycle_action(db, contract.id)
    termination_reason = None
    effective_termination_date = None
    if latest_action is not None and latest_action.action_type == "TERMINATE":
        termination_reason = latest_action.termination_reason
        effective_termination_date = latest_action.effective_termination_date
    actions_enabled = contract.status in EXECUTED_STATUSES and not contract.renewal_action_in_progress
    return RenewalPanelResponse(
        contractId=contract.id,
        renewalAlertBanner=banner,
        contractEndDate=contract.end_date,
        noticePeriod=contract.notice_period_text,
        alertThresholdDays=threshold_days,
        renewEnabled=actions_enabled,
        amendEnabled=actions_enabled,
        terminateEnabled=actions_enabled,
        actionInProgress=contract.renewal_action_in_progress,
        linkedContractId=contract.linked_contract_id,
        linkedContractRelation=contract.linked_relation_type,
        obligations=obligations,
        terminationReason=termination_reason,
        effectiveTerminationDate=effective_termination_date,
    )


def _start_lifecycle_action(user: CurrentUser, contract: Contract, action_label: str) -> None:
    _assert_owner_or_admin(user, contract)
    if contract.renewal_action_in_progress:
        raise ConflictError(_DUPLICATE_ACTION_MESSAGE)
    if contract.status not in EXECUTED_STATUSES:
        raise ConflictError(f"The {action_label} button is disabled for the current contract status.")
    contract.renewal_action_in_progress = True


def _create_linked_contract(
    db: Session, original: Contract, relation_type: str, user_id: uuid.UUID
) -> Contract:
    new_contract = Contract(
        id=uuid.uuid4(),
        tenant_id=original.tenant_id,
        contract_name=f"{original.contract_name} ({relation_type.title()})",
        contract_type=original.contract_type,
        industry=original.industry,
        counterparty_id=original.counterparty_id,
        counterparty=original.counterparty,
        contract_owner_id=original.contract_owner_id,
        owner_id=original.owner_id,
        contract_value=original.contract_value,
        value=original.value,
        currency=original.currency,
        start_date=original.end_date or original.start_date,
        end_date=None,
        renewal_type=original.renewal_type,
        notice_period_text=original.notice_period_text,
        assigned_date=date.today(),
        due_date=original.due_date or date.today(),
        status="Draft",
        document_index_status=None,
        linked_contract_id=original.id,
        linked_relation_type=relation_type,
        renewal_action_in_progress=False,
        created_by=user_id,
        updated_by=user_id,
    )
    repo.insert_contract(db, new_contract)
    return new_contract


def _finish_lifecycle_action(
    db: Session,
    original: Contract,
    new_contract: Contract,
    *,
    action_type: str,
    new_status: str,
    relation_type: str,
    user_id: uuid.UUID,
    termination_reason: str | None = None,
    effective_termination_date: date | None = None,
) -> LinkedContractActionResponse:
    before_status = original.status
    original.status = new_status
    original.linked_contract_id = new_contract.id
    original.linked_relation_type = relation_type
    original.renewal_action_in_progress = False
    original.updated_by = user_id

    repo.insert_lifecycle_action(
        db,
        ContractLifecycleAction(
            id=uuid.uuid4(),
            original_contract_id=original.id,
            linked_contract_id=new_contract.id,
            action_type=action_type,
            status="Completed",
            termination_reason=termination_reason,
            effective_termination_date=effective_termination_date,
            contract_end_date_snapshot=original.end_date,
            notice_period_snapshot=original.notice_period_text,
            renewal_alert_banner_snapshot=_compute_renewal_alert(original)[0],
            created_by=user_id,
            updated_by=user_id,
        ),
    )
    repo.insert_obligation_audit(
        db,
        ObligationAuditLog(
            id=uuid.uuid4(),
            contract_id=original.id,
            obligation_id=None,
            action_type=action_type,
            field_name="status",
            before_value=before_status,
            after_value=new_status,
            performed_by=user_id,
            performed_at=datetime.now(timezone.utc),
            created_by=user_id,
        ),
    )
    db.commit()
    return LinkedContractActionResponse(
        originalContractId=original.id,
        originalContractStatus=original.status,
        linkedContractId=new_contract.id,
        linkedContractReference=new_contract.id,
        terminationReason=termination_reason,
        effectiveTerminationDate=effective_termination_date,
        contractEndDate=original.end_date,
        noticePeriod=original.notice_period_text,
        renewalAlertBanner=_compute_renewal_alert(original)[0],
    )


def renew_contract(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> LinkedContractActionResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _start_lifecycle_action(user, contract, "Renew")
    user_id = _user_uuid(user)
    new_contract = _create_linked_contract(db, contract, "RENEWAL", user_id)
    return _finish_lifecycle_action(
        db, contract, new_contract, action_type="RENEW", new_status="Renewed",
        relation_type="RENEWAL", user_id=user_id,
    )


def amend_contract(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> LinkedContractActionResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _start_lifecycle_action(user, contract, "Amend")
    user_id = _user_uuid(user)
    new_contract = _create_linked_contract(db, contract, "AMENDMENT", user_id)
    return _finish_lifecycle_action(
        db, contract, new_contract, action_type="AMEND", new_status="Amended",
        relation_type="AMENDMENT", user_id=user_id,
    )


def terminate_contract(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    payload: TerminateContractRequest,
) -> LinkedContractActionResponse:
    if not payload.terminationReason or not payload.terminationReason.strip():
        raise ValidationFailedError(
            "Termination reason is required", details=["terminationReason is required."]
        )
    if payload.effectiveTerminationDate < date.today():
        raise ValidationFailedError(
            "Effective Termination Date must be on or after today",
            details=["effectiveTerminationDate must be on or after today."],
        )
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    _start_lifecycle_action(user, contract, "Terminate")
    user_id = _user_uuid(user)
    new_contract = _create_linked_contract(db, contract, "TERMINATION", user_id)
    return _finish_lifecycle_action(
        db, contract, new_contract, action_type="TERMINATE", new_status="Terminated",
        relation_type="TERMINATION", user_id=user_id,
        termination_reason=payload.terminationReason,
        effective_termination_date=payload.effectiveTerminationDate,
    )
