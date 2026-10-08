"""Data access for `templates` / `template_versions`. Owns queries only -- the business rules
(completeness, versioning, lifecycle transitions) live in `app.services.templates`.
"""
import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.template import Template, TemplateVersion


def get_by_id(db: Session, tenant_id: uuid.UUID, template_id: uuid.UUID) -> Template | None:
    return (
        db.query(Template)
        .filter(Template.id == template_id, Template.tenant_id == tenant_id, Template.deleted_at.is_(None))
        .first()
    )


def list_by_tenant(
    db: Session,
    tenant_id: uuid.UUID,
    statuses: list[str] | None = None,
    contract_type: str | None = None,
) -> list[Template]:
    query = db.query(Template).filter(Template.tenant_id == tenant_id, Template.deleted_at.is_(None))
    if statuses:
        query = query.filter(Template.status.in_(statuses))
    if contract_type:
        query = query.filter(Template.template_category == contract_type)
    return query.order_by(Template.template_name.asc()).all()


def list_versions(db: Session, template_id: uuid.UUID) -> list[TemplateVersion]:
    return (
        db.query(TemplateVersion)
        .filter(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version_number.asc())
        .all()
    )


def insert_template(db: Session, template: Template) -> Template:
    db.add(template)
    db.flush()
    return template


def insert_version(db: Session, version: TemplateVersion) -> TemplateVersion:
    db.add(version)
    db.flush()
    return version


def snapshot_version(
    db: Session, template: Template, *, changed_by: uuid.UUID, now: datetime, change_summary: str | None
) -> TemplateVersion:
    """Copies the template's current field values into an immutable `template_versions` row."""
    version = TemplateVersion(
        template_id=template.id,
        version_number=template.current_version,
        changed_by=changed_by,
        date_changed=now,
        change_summary=change_summary,
        template_name=template.template_name,
        template_category=template.template_category,
        document_format=template.document_format,
        template_body=template.template_body,
        status=template.status,
        created_by=changed_by,
        updated_by=changed_by,
    )
    return insert_version(db, version)


def has_unexecuted_contract(db: Session, template_id: uuid.UUID) -> bool:
    """UC3-AF-004 / UC3-BR-003 / UC3-BR-012: a template cannot be deactivated while it is
    attached to a contract that has not yet reached Executed status.
    """
    return (
        db.query(Contract.id)
        .filter(
            Contract.template_id == template_id,
            Contract.deleted_at.is_(None),
            Contract.status != "Executed",
        )
        .first()
        is not None
    )
