"""Business rules for the `settings/integrations` resource: credential validation and
masking (UC11-BR-009, UC11-BR-016), the Disconnected/Connected/"Disconnected - reconnect
required" transitions (UC11-AF-004, UC11-AF-007, UC11-BR-017, UC11-FV-003), and the audit
trail each transition leaves behind -- see CLAUDE.md's lifecycle-uc10-uc11 module section
and TASK.md (T-SETTINGS-INTEGRATIONS-API).
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import NotFoundError, ValidationFailedError
from app.models.tracker import TenantAuditLog, TenantIntegration
from app.repositories import settings_audit_log as audit_log_repo
from app.repositories import settings_integrations as integrations_repo
from app.repositories.settings_integrations import INTEGRATION_NAMES
from app.schemas.settings_integrations import ConnectIntegrationRequest, IntegrationResponse

CONNECTION_FAILED_MESSAGE = "Connection failed. Please check your credentials and try again"
UNKNOWN_INTEGRATION_MESSAGE = "unknown integration"

# Tokens are modeled as expiring after this window so UC11-AF-007's automatic
# Connected -> "Disconnected - reconnect required" transition has something to trigger on.
TOKEN_LIFETIME = timedelta(hours=24)


def _mask(credentials: dict[str, Any]) -> str:
    # UC11-BR-009: the plaintext value is never stored or re-derivable -- only a masked
    # display string survives past this function.
    value = next((str(v) for v in credentials.values() if str(v).strip()), "")
    if len(value) <= 4:
        return "••••"
    return "••••" + value[-4:]


def _validate_credentials(credentials: dict[str, Any]) -> None:
    if not credentials or any(not str(v).strip() for v in credentials.values()):
        raise ValidationFailedError(CONNECTION_FAILED_MESSAGE, details=[CONNECTION_FAILED_MESSAGE])


def _to_response(row: TenantIntegration) -> IntegrationResponse:
    return IntegrationResponse(
        integrationName=row.integration_name,
        connectionStatus=row.connection_status,
        maskedCredential=row.credential_masked_display,
    )


def _log(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    details: str,
    user_label: str | None = None,
) -> None:
    # settings_audit_log's AuditLogEntryResponse.logAction is one of Created/Updated/Deleted
    # (see app/schemas/settings_audit_log.py) -- an integration connect/disconnect/expiry is
    # always an update to the integration record, so logAction is always "Updated" and the
    # specific event (connected, disconnected, failed, expired) goes in `details`.
    now = datetime.now(timezone.utc)
    user_uuid = _safe_uuid(user.user_id)
    audit_log_repo.append(
        db,
        TenantAuditLog(
            tenant_id=tenant_id,
            log_date_time=now,
            log_user=user_label or user.role,
            log_action="Updated",
            log_entity="Integration",
            details=details,
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )


def _as_aware(value: datetime) -> datetime:
    # SQLite (used in tests) does not round-trip tzinfo on a DateTime(timezone=True) column --
    # treat a naive value read back from the database as UTC rather than letting the
    # naive/aware comparison below raise.
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def _safe_uuid(user_id: str) -> uuid.UUID:
    try:
        return uuid.UUID(user_id)
    except (ValueError, TypeError):
        return uuid.UUID(int=0)


def _require_known_name(integration_name: str) -> None:
    if integration_name not in INTEGRATION_NAMES:
        raise NotFoundError(UNKNOWN_INTEGRATION_MESSAGE)


def list_integrations(db: Session, tenant_id: uuid.UUID, user: CurrentUser) -> list[IntegrationResponse]:
    user_uuid = _safe_uuid(user.user_id)
    integrations_repo.ensure_seeded(db, tenant_id, user_uuid)

    now = datetime.now(timezone.utc)
    rows = integrations_repo.list_by_tenant(db, tenant_id)
    for row in rows:
        # UC11-AF-007: a token expiring is a system-driven transition, not a user action --
        # surfaced here because this is the read path the UI polls for the current status.
        if (
            row.connection_status == "Connected"
            and row.token_expires_at is not None
            and _as_aware(row.token_expires_at) <= now
        ):
            row.connection_status = "Disconnected - reconnect required"
            row.updated_at = now
            _log(db, tenant_id, user, f"{row.integration_name} token expired", user_label="system")
    # Commit unconditionally: ensure_seeded's inserts must survive past this request too, or
    # every GET would reseed (and re-401/403-check) against an empty table.
    db.commit()

    return [_to_response(row) for row in rows]


def connect_integration(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    integration_name: str,
    payload: ConnectIntegrationRequest,
) -> IntegrationResponse:
    _require_known_name(integration_name)
    user_uuid = _safe_uuid(user.user_id)
    row = integrations_repo.get_by_name(db, tenant_id, integration_name)
    if row is None:
        row = integrations_repo.insert(
            db,
            TenantIntegration(
                tenant_id=tenant_id,
                integration_name=integration_name,
                connection_status="Disconnected",
                created_by=user_uuid,
                updated_by=user_uuid,
            ),
        )

    try:
        _validate_credentials(payload.credentials)
    except ValidationFailedError:
        # UC11-AF-004: Connection Status stays Disconnected and the failure is still audited.
        _log(db, tenant_id, user, f"{integration_name} connection failed: invalid credentials")
        db.commit()
        raise

    now = datetime.now(timezone.utc)
    row.connection_status = "Connected"
    row.credential_masked_display = _mask(payload.credentials)
    row.credential_ciphertext = None
    row.token_expires_at = now + TOKEN_LIFETIME
    row.updated_at = now
    row.updated_by = user_uuid
    _log(db, tenant_id, user, f"{integration_name} connected")
    db.commit()
    return _to_response(row)


def disconnect_integration(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, integration_name: str
) -> IntegrationResponse:
    _require_known_name(integration_name)
    user_uuid = _safe_uuid(user.user_id)
    row = integrations_repo.get_by_name(db, tenant_id, integration_name)
    if row is None:
        row = integrations_repo.insert(
            db,
            TenantIntegration(
                tenant_id=tenant_id,
                integration_name=integration_name,
                connection_status="Disconnected",
                created_by=user_uuid,
                updated_by=user_uuid,
            ),
        )

    now = datetime.now(timezone.utc)
    row.connection_status = "Disconnected"
    row.token_expires_at = None
    row.updated_at = now
    row.updated_by = user_uuid
    _log(db, tenant_id, user, f"{integration_name} disconnected")
    db.commit()
    return _to_response(row)
