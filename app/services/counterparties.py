"""Business rules for the `counterparties` resource: search with GST/Tax ID duplicate
detection and mandatory-field/email/duplicate validation on create -- see CLAUDE.md's uc123
module section and stories UC2-AF-008, UC2-FV-001, UC2-FV-002, UC2-MF-001
(T-COUNTERPARTIES-API/TASK.md).
"""
import re
import uuid

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, ValidationFailedError
from app.models.counterparty import Counterparty
from app.repositories import counterparties as counterparties_repo
from app.schemas.counterparty import (
    CounterpartyResponse,
    CounterpartySearchResponse,
    CreateCounterpartyRequest,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_DUPLICATE_GST_MESSAGE = "A counterparty with this Tax ID already exists"


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _to_response(counterparty: Counterparty) -> CounterpartyResponse:
    return CounterpartyResponse(
        id=counterparty.id,
        name=counterparty.name,
        email=counterparty.email,
        company=counterparty.company,
        address=counterparty.address,
        gstTaxId=counterparty.gst_tax_id,
    )


def search_counterparties(
    db: Session, tenant_id: uuid.UUID, search: str | None
) -> CounterpartySearchResponse:
    rows = counterparties_repo.search_by_tenant(db, tenant_id, search)
    items = [_to_response(row) for row in rows]

    # UC2-AF-008: a search string that exactly matches an existing counterparty's GST/Tax ID
    # surfaces the duplicate-warning message alongside the matching record(s) for selection.
    duplicate_warning = None
    if not _is_blank(search) and counterparties_repo.find_by_gst_tax_id(db, tenant_id, search) is not None:
        duplicate_warning = _DUPLICATE_GST_MESSAGE

    return CounterpartySearchResponse(items=items, duplicateWarning=duplicate_warning)


def _validate_payload(payload: CreateCounterpartyRequest) -> None:
    # UC2-FV-002: Name, Email and Company are mandatory; Address and GST/Tax ID stay optional.
    missing = []
    if _is_blank(payload.name):
        missing.append("Counterparty Name is required.")
    if _is_blank(payload.email):
        missing.append("Counterparty Email is required.")
    if _is_blank(payload.company):
        missing.append("Counterparty Company is required.")
    if missing:
        raise ValidationFailedError("Please fill all mandatory fields", details=missing)

    if not _EMAIL_RE.match(payload.email):
        raise ValidationFailedError(
            "Counterparty Email must be a valid email address.",
            details=["Counterparty Email must be a valid email address."],
        )


def create_counterparty(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: CreateCounterpartyRequest
) -> CounterpartyResponse:
    _validate_payload(payload)

    # UC2-AF-008: block creating a duplicate -- a GST/Tax ID that already matches an existing
    # counterparty in this tenant is a conflict, not a new record.
    if not _is_blank(payload.gstTaxId):
        existing = counterparties_repo.find_by_gst_tax_id(db, tenant_id, payload.gstTaxId)
        if existing is not None:
            raise ConflictError(_DUPLICATE_GST_MESSAGE, details=[_DUPLICATE_GST_MESSAGE])

    user_uuid = uuid.UUID(user.user_id)
    counterparty = Counterparty(
        tenant_id=tenant_id,
        name=payload.name,
        email=payload.email,
        company=payload.company,
        address=payload.address,
        gst_tax_id=payload.gstTaxId,
        created_by=user_uuid,
        updated_by=user_uuid,
    )
    counterparties_repo.insert_counterparty(db, counterparty)
    db.commit()
    db.refresh(counterparty)
    return _to_response(counterparty)
