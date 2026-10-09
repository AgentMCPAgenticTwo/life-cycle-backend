"""`/api/v1/templates` -- thin HTTP binding over `app.services.templates`. See CLAUDE.md's
uc123 module section for the exact paths, roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.template import (
    CreateTemplateRequest,
    TemplateListResponse,
    TemplateResponse,
    UpdateTemplateRequest,
    VersionHistoryResponse,
)
from app.services import templates as templates_service

router = APIRouter(prefix="/templates", tags=["templates"])

# Dependency declaration order matters here, not just for readability: the role check must
# resolve (and be able to raise 401/403) before `current_tenant_id` ever touches the
# database -- see app/routers/clauses.py for the same convention.


@router.get("", response_model=TemplateListResponse)
def list_templates(
    status: str | None = Query(None),
    contractType: str | None = Query(None),
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "LEGAL_REVIEWER", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> TemplateListResponse:
    return templates_service.list_templates(
        db, tenant_id, user.role, status=status, contract_type=contractType
    )


@router.post("", response_model=TemplateResponse, status_code=201)
def create_template(
    payload: CreateTemplateRequest,
    response: Response,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    result = templates_service.create_template(db, tenant_id, user, payload)
    response.headers["Location"] = f"/api/v1/templates/{result.id}"
    return result


@router.put("/{id}", response_model=TemplateResponse)
def update_template(
    id: uuid.UUID,
    payload: UpdateTemplateRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    return templates_service.update_template(db, tenant_id, id, user, payload)


@router.post("/{id}/deactivate", response_model=TemplateResponse)
def deactivate_template(
    id: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    return templates_service.deactivate_template(db, tenant_id, id, user)


@router.post("/{id}/reactivate", response_model=TemplateResponse)
def reactivate_template(
    id: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> TemplateResponse:
    return templates_service.reactivate_template(db, tenant_id, id, user)


@router.get("/{id}/versions", response_model=VersionHistoryResponse)
def get_template_versions(
    id: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "LEGAL_REVIEWER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> VersionHistoryResponse:
    return templates_service.get_versions(db, tenant_id, id)
