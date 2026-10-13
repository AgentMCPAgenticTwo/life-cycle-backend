"""`/api/v1/settings/integrations` -- thin HTTP binding over
`app.services.settings_integrations`. See CLAUDE.md's lifecycle-uc10-uc11 module section
and TASK.md (T-SETTINGS-INTEGRATIONS-API) for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.settings_integrations import ConnectIntegrationRequest, IntegrationResponse
from app.services import settings_integrations as integrations_service

router = APIRouter(prefix="/settings/integrations", tags=["settings-integrations"])


@router.get("", response_model=list[IntegrationResponse])
def list_integrations(
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> list[IntegrationResponse]:
    return integrations_service.list_integrations(db, tenant_id, user)


@router.post("/{integrationName}/connect", response_model=IntegrationResponse)
def connect_integration(
    integrationName: str,
    payload: ConnectIntegrationRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> IntegrationResponse:
    return integrations_service.connect_integration(db, tenant_id, user, integrationName, payload)


@router.post("/{integrationName}/disconnect", response_model=IntegrationResponse)
def disconnect_integration(
    integrationName: str,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> IntegrationResponse:
    return integrations_service.disconnect_integration(db, tenant_id, user, integrationName)
