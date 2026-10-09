"""Business rules for the `templates` resource: field validation, Draft/Active/Inactive
lifecycle, versioning on save, the optimistic-concurrency check, and the deactivation
attachment guard -- see CLAUDE.md's uc123 module section and stories UC3-AF-001,
UC3-AF-004, UC3-AF-005, UC3-AF-006, UC3-BR-002, UC3-BR-003, UC3-BR-011, UC3-BR-012,
UC3-BR-013, UC3-BR-014.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, NotFoundError, ValidationFailedError
from app.models.template import Template
from app.models.user import User
from app.repositories import templates as templates_repo
from app.schemas.template import (
    CreateTemplateRequest,
    TemplateListResponse,
    TemplateResponse,
    UpdateTemplateRequest,
    VersionHistoryItemResponse,
    VersionHistoryResponse,
)

_EDITABLE_FIELDS = ("template_name", "template_category", "document_format", "template_body")

_FIELD_LABELS = {
    "template_name": "Template Name",
    "template_category": "Template Category",
    "document_format": "Document Format",
    "template_body": "Template Body",
}

_VALID_DOCUMENT_FORMATS = ("PDF", "DOCX")


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _validate_payload(payload: CreateTemplateRequest | UpdateTemplateRequest) -> None:
    """UC3-AF-001 / UC3-FV-001: a blank mandatory field blocks the save before anything is
    persisted. Template Name gets the exact message the story names.
    """
    if _is_blank(payload.templateName):
        raise ValidationFailedError(
            "Template Name is required.", details=["Template Name is required."]
        )
    if _is_blank(payload.templateCategory):
        raise ValidationFailedError(
            "Template Category is required.", details=["Template Category is required."]
        )
    if payload.documentFormat not in _VALID_DOCUMENT_FORMATS:
        # UC3-AF-005's exact message for a non-PDF/DOCX file format.
        raise ValidationFailedError(
            "Unsupported file format. Please upload a PDF or DOCX file.",
            details=["Unsupported file format. Please upload a PDF or DOCX file."],
        )
    if _is_blank(payload.templateBody):
        raise ValidationFailedError(
            "Template Body is required.", details=["Template Body is required."]
        )


def _is_complete(payload: CreateTemplateRequest | UpdateTemplateRequest) -> bool:
    """UC3-BR-011: Template Name, Template Category, Document Format and Template Body are
    all mandatory for a template to transition from Draft to Active.
    """
    return (
        not _is_blank(payload.templateName)
        and not _is_blank(payload.templateCategory)
        and payload.documentFormat in _VALID_DOCUMENT_FORMATS
        and not _is_blank(payload.templateBody)
    )


def _resolve_user_name(db: Session, user_id: uuid.UUID) -> str:
    row = db.query(User).filter(User.id == user_id).first()
    return row.name if row is not None else "Unknown"


def _to_response(db: Session, template: Template) -> TemplateResponse:
    return TemplateResponse(
        id=template.id,
        templateName=template.template_name,
        templateCategory=template.template_category,
        documentFormat=template.document_format,
        templateBody=template.template_body,
        status=template.status,
        lastModifiedBy=_resolve_user_name(db, template.updated_by),
        lastModifiedDate=template.updated_at,
    )


def _get_or_404(db: Session, tenant_id: uuid.UUID, template_id: uuid.UUID) -> Template:
    template = templates_repo.get_by_id(db, tenant_id, template_id)
    if template is None:
        raise NotFoundError("template not found")
    return template


def list_templates(
    db: Session,
    tenant_id: uuid.UUID,
    role: str,
    *,
    status: str | None,
    contract_type: str | None,
) -> TemplateListResponse:
    # UC3-BR-009: Contract Owner only ever sees Active templates in read-only form; Tenant
    # Admin / Legal Reviewer manage the full library across every status, optionally
    # narrowed by the `status` query filter.
    if role == "CONTRACT_OWNER":
        statuses = ["Active"]
    elif status:
        statuses = [status]
    else:
        statuses = None
    rows = templates_repo.list_by_tenant(db, tenant_id, statuses, contract_type)
    return TemplateListResponse(items=[_to_response(db, row) for row in rows])


def create_template(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: CreateTemplateRequest
) -> TemplateResponse:
    _validate_payload(payload)
    now = datetime.now(timezone.utc)
    user_uuid = uuid.UUID(user.user_id)
    status = "Active" if _is_complete(payload) else "Draft"

    template = Template(
        tenant_id=tenant_id,
        template_name=payload.templateName,
        template_category=payload.templateCategory,
        document_format=payload.documentFormat,
        template_body=payload.templateBody,
        status=status,
        current_version=1,
        created_by=user_uuid,
        updated_by=user_uuid,
    )
    templates_repo.insert_template(db, template)
    templates_repo.snapshot_version(db, template, changed_by=user_uuid, now=now, change_summary=None)
    db.commit()
    db.refresh(template)
    return _to_response(db, template)


def update_template(
    db: Session,
    tenant_id: uuid.UUID,
    template_id: uuid.UUID,
    user: CurrentUser,
    payload: UpdateTemplateRequest,
) -> TemplateResponse:
    template = _get_or_404(db, tenant_id, template_id)
    _validate_payload(payload)

    # UC3-AF-006: optimistic concurrency. `expectedVersion` is an addition to
    # UpdateTemplateRequest beyond context.json -- see this task's `blockers`.
    if payload.expectedVersion is not None and payload.expectedVersion != template.current_version:
        raise ConflictError(
            "This template was updated by another user. Please refresh and re-apply your changes.",
            details=[
                "This template was updated by another user. Please refresh and re-apply your changes."
            ],
        )

    new_values = {
        "template_name": payload.templateName,
        "template_category": payload.templateCategory,
        "document_format": payload.documentFormat,
        "template_body": payload.templateBody,
    }
    changed_fields = [f for f in _EDITABLE_FIELDS if getattr(template, f) != new_values[f]]

    # UC3-BR-014: saving without changing any field creates no new version.
    if not changed_fields:
        return _to_response(db, template)

    now = datetime.now(timezone.utc)
    user_uuid = uuid.UUID(user.user_id)
    for field in changed_fields:
        setattr(template, field, new_values[field])
    # UC3-BR-011: a still-Draft item becomes Active once it is complete; an already
    # Active/Inactive item keeps its lifecycle status -- editing is not a reactivation.
    if template.status == "Draft" and _is_complete(payload):
        template.status = "Active"
    template.current_version += 1
    template.updated_by = user_uuid
    template.updated_at = now

    change_summary = "Updated: " + ", ".join(_FIELD_LABELS[f] for f in changed_fields)
    templates_repo.snapshot_version(db, template, changed_by=user_uuid, now=now, change_summary=change_summary)
    db.commit()
    db.refresh(template)
    return _to_response(db, template)


def deactivate_template(
    db: Session, tenant_id: uuid.UUID, template_id: uuid.UUID, user: CurrentUser
) -> TemplateResponse:
    template = _get_or_404(db, tenant_id, template_id)
    if template.status != "Active":
        raise ConflictError("Only an Active template can be deactivated.")
    # UC3-AF-004 / UC3-BR-003 / UC3-BR-012: blocked while attached to any contract that has
    # not yet reached Executed status.
    if templates_repo.has_unexecuted_contract(db, template_id):
        message = "This template cannot be deactivated while it is in use by an active contract."
        raise ConflictError(message, details=[message])
    template.status = "Inactive"
    template.updated_by = uuid.UUID(user.user_id)
    template.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)
    return _to_response(db, template)


def reactivate_template(
    db: Session, tenant_id: uuid.UUID, template_id: uuid.UUID, user: CurrentUser
) -> TemplateResponse:
    template = _get_or_404(db, tenant_id, template_id)
    if template.status != "Inactive":
        raise ConflictError("Only an Inactive template can be reactivated.")
    # UC3-BR-013: reactivation is unrestricted -- no attachment check here.
    template.status = "Active"
    template.updated_by = uuid.UUID(user.user_id)
    template.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(template)
    return _to_response(db, template)


def get_versions(db: Session, tenant_id: uuid.UUID, template_id: uuid.UUID) -> VersionHistoryResponse:
    _get_or_404(db, tenant_id, template_id)
    versions = templates_repo.list_versions(db, template_id)
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
