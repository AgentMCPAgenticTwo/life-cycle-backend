"""DTOs for `/api/v1/settings/integrations` -- see CLAUDE.md's lifecycle-uc10-uc11 module
section and TASK.md (T-SETTINGS-INTEGRATIONS-API) for the exact fields and enums.
"""
from typing import Any, Literal

from pydantic import BaseModel

IntegrationName = Literal[
    "Salesforce", "HubSpot", "ERP", "Google Drive", "SharePoint", "DocuSign", "Adobe Sign"
]
ConnectionStatus = Literal["Connected", "Disconnected", "Disconnected - reconnect required"]


class IntegrationResponse(BaseModel):
    integrationName: IntegrationName
    connectionStatus: ConnectionStatus
    maskedCredential: str | None = None


class ConnectIntegrationRequest(BaseModel):
    credentials: dict[str, Any]
