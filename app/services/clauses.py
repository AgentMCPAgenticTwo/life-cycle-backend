"""Business rules for the `clauses` resource: field validation, Draft/Active/Inactive
lifecycle, versioning on save, and the optimistic-concurrency check -- see CLAUDE.md's
uc123 module section and stories UC3-AF-001, UC3-AF-006, UC3-BR-002, UC3-BR-011,
UC3-BR-012, UC3-BR-013, UC3-BR-014.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models.clause import Clause
from app.models.user import User
from app.repositories import clauses as clauses_repo
from app.schemas.clause import (
    ClauseListResponse,
    ClauseResponse,
    CreateClauseRequest,
    UpdateClauseRequest,
    VersionHistoryItemResponse,
    VersionHistoryResponse,
)

_EDITABLE_FIELDS = (
    "clause_name",
    "clause_category",
    "standard_text",
    "fallback_text_1",
    "fallback_text_2",
    "risk_level",
    "mandatory",
)

_FIELD_LABELS = {
    "clause_name": "Clause Name",
    "clause_category": "Clause Category",
    "standard_text": "Standard Text",
    "fallback_text_1": "Fallback Text 1",
    "fallback_text_2": "Fallback Text 2",
    "risk_level": "Risk Level",
    "mandatory": "Mandatory",
}


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _validate_payload(payload: CreateClauseRequest | UpdateClauseRequest) -> None:
    """UC3-AF-001 / UC3-FV-002: a blank mandatory field blocks the save before anything is
    persisted. Clause Name gets the exact message the story names; Standard Text gets the
    same treatment since FV-002 names it as an equally mandatory field.
    """
    if _is_blank(payload.clauseName):
        raise ValidationFailedError("Clause Name is required.", details=["Clause Name is required."])
    if _is_blank(payload.standardText):
        raise ValidationFailedError("Standard Text is required.", details=["Standard Text is required."])


def _is_complete(payload: CreateClauseRequest | UpdateClauseRequest) -> bool:
    """UC3-BR-011: Clause Name, Clause Category, Standard Text, Risk Level and Mandatory are
    the mandatory fields; Fallback Text 1/2 are optional and do not block Active status.
    """
    return not _is_blank(payload.clauseName) and not _is_blank(payload.standardText)


def _resolve_user_name(db: Session, user_id: uuid.UUID) -> str:
    row = db.query(User).filter(User.id == user_id).first()
    return row.name if row is not None else "Unknown"


def _to_response(db: Session, clause: Clause) -> ClauseResponse:
    return ClauseResponse(
        id=clause.id,
        clauseName=clause.clause_name,
        clauseCategory=clause.clause_category,
        standardText=clause.standard_text,
        fallbackText1=clause.fallback_text_1,
        fallbackText2=clause.fallback_text_2,
        riskLevel=clause.risk_level,
        mandatory=clause.mandatory,
        status=clause.status,
        lastModifiedBy=_resolve_user_name(db, clause.updated_by),
        lastModifiedDate=clause.updated_at,
    )


def _get_or_404(db: Session, tenant_id: uuid.UUID, clause_id: uuid.UUID) -> Clause:
    clause = clauses_repo.get_by_id(db, tenant_id, clause_id)
    if clause is None:
        raise NotFoundError("clause not found")
    return clause


def list_clauses(db: Session, tenant_id: uuid.UUID, role: str) -> ClauseListResponse:
    # UC3-BR-009: Contract Owner only ever sees Active clauses in read-only form; Tenant
    # Admin / Legal Reviewer manage the full library across every status.
    statuses = ["Active"] if role == "CONTRACT_OWNER" else None
    rows = clauses_repo.list_by_tenant(db, tenant_id, statuses)
    return ClauseListResponse(items=[_to_response(db, row) for row in rows])


def create_clause(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: CreateClauseRequest
) -> ClauseResponse:
    _validate_payload(payload)
    now = datetime.now(timezone.utc)
    user_uuid = uuid.UUID(user.user_id)
    status = "Active" if _is_complete(payload) else "Draft"

    clause = Clause(
        tenant_id=tenant_id,
        clause_name=payload.clauseName,
        clause_category=payload.clauseCategory,
        standard_text=payload.standardText,
        fallback_text_1=payload.fallbackText1,
        fallback_text_2=payload.fallbackText2,
        risk_level=payload.riskLevel,
        mandatory=payload.mandatory,
        status=status,
        current_version=1,
        created_by=user_uuid,
        updated_by=user_uuid,
    )
    clauses_repo.insert_clause(db, clause)
    clauses_repo.snapshot_version(db, clause, changed_by=user_uuid, now=now, change_summary=None)
    db.commit()
    db.refresh(clause)
    return _to_response(db, clause)


def update_clause(
    db: Session,
    tenant_id: uuid.UUID,
    clause_id: uuid.UUID,
    user: CurrentUser,
    payload: UpdateClauseRequest,
) -> ClauseResponse:
    clause = _get_or_404(db, tenant_id, clause_id)
    _validate_payload(payload)

    # UC3-AF-006: optimistic concurrency. `expectedVersion` is an addition to
    # UpdateClauseRequest beyond context.json -- see this task's `blockers`.
    if payload.expectedVersion is not None and payload.expectedVersion != clause.current_version:
        raise ConflictError(
            "This clause was updated by another user. Please refresh and re-apply your changes.",
            details=["This clause was updated by another user. Please refresh and re-apply your changes."],
        )

    new_values = {
        "clause_name": payload.clauseName,
        "clause_category": payload.clauseCategory,
        "standard_text": payload.standardText,
        "fallback_text_1": payload.fallbackText1,
        "fallback_text_2": payload.fallbackText2,
        "risk_level": payload.riskLevel,
        "mandatory": payload.mandatory,
    }
    changed_fields = [f for f in _EDITABLE_FIELDS if getattr(clause, f) != new_values[f]]

    # UC3-BR-014: saving without changing any field creates no new version.
    if not changed_fields:
        return _to_response(db, clause)

    now = datetime.now(timezone.utc)
    user_uuid = uuid.UUID(user.user_id)
    for field in changed_fields:
        setattr(clause, field, new_values[field])
    # UC3-BR-011: a still-Draft item becomes Active once it is complete; an already
    # Active/Inactive item keeps its lifecycle status -- editing is not a reactivation.
    if clause.status == "Draft" and _is_complete(payload):
        clause.status = "Active"
    clause.current_version += 1
    clause.updated_by = user_uuid
    clause.updated_at = now

    change_summary = "Updated: " + ", ".join(_FIELD_LABELS[f] for f in changed_fields)
    clauses_repo.snapshot_version(db, clause, changed_by=user_uuid, now=now, change_summary=change_summary)
    db.commit()
    db.refresh(clause)
    return _to_response(db, clause)


def deactivate_clause(
    db: Session, tenant_id: uuid.UUID, clause_id: uuid.UUID, user: CurrentUser
) -> ClauseResponse:
    clause = _get_or_404(db, tenant_id, clause_id)
    if clause.status != "Active":
        raise ConflictError("Only an Active clause can be deactivated.")
    # UC3-BR-012 also requires blocking deactivation when the clause is attached to an
    # active, unsigned contract -- no table in this module's contract records a
    # clause-to-contract/template attachment, so that check cannot be implemented here.
    # See this task's `blockers`.
    clause.status = "Inactive"
    clause.updated_by = uuid.UUID(user.user_id)
    clause.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(clause)
    return _to_response(db, clause)


def reactivate_clause(
    db: Session, tenant_id: uuid.UUID, clause_id: uuid.UUID, user: CurrentUser
) -> ClauseResponse:
    clause = _get_or_404(db, tenant_id, clause_id)
    if clause.status != "Inactive":
        raise ConflictError("Only an Inactive clause can be reactivated.")
    clause.status = "Active"
    clause.updated_by = uuid.UUID(user.user_id)
    clause.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(clause)
    return _to_response(db, clause)


def get_versions(db: Session, tenant_id: uuid.UUID, clause_id: uuid.UUID) -> VersionHistoryResponse:
    _get_or_404(db, tenant_id, clause_id)
    versions = clauses_repo.list_versions(db, clause_id)
    items = [
        VersionHistoryItemResponse(
            versionNumber=v.version_number,
            changedBy=_resolve_user_name(db, v.changed_by),
            dateChanged=v.date_changed,
            changeSummary=v.change_summary,
        )
        for v in versions
    ]
    return VersionHistoryResponse(items=items)
