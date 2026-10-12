"""`/api/v1/esignature-settings` -- thin HTTP binding over
`app.services.esignature_settings`. See CLAUDE.md's UC6-UC7-combined module section for the
exact path, roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.esignature_settings import (
    EsignatureSettingsResponse,
    UpdateEsignatureSettingsRequest,
)
from app.services import esignature_settings as esignature_settings_service

router = APIRouter(prefix="/esignature-settings", tags=["esignature-settings"])


@router.get("", response_model=EsignatureSettingsResponse)
def get_esignature_settings(
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> EsignatureSettingsResponse:
    return esignature_settings_service.get_settings(db, tenant_id)


@router.put("", response_model=EsignatureSettingsResponse)
def update_esignature_settings(
    payload: UpdateEsignatureSettingsRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> EsignatureSettingsResponse:
    return esignature_settings_service.update_settings(db, tenant_id, user, payload)
