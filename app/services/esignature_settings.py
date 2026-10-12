"""Business rules for the `esignature-settings` resource: defaulting and validation behind
`GET`/`PUT /api/v1/esignature-settings` -- see CLAUDE.md's UC6-UC7-combined module section
and stories UC7-BR-006, UC7-BR-013, UC7-FV-004.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ValidationFailedError
from app.models.esignature import EsignatureSettings
from app.repositories import esignature_settings as esignature_settings_repo
from app.schemas.esignature_settings import (
    EsignatureSettingsResponse,
    UpdateEsignatureSettingsRequest,
)

DEFAULT_REMINDER_FREQUENCY_DAYS = 3
DEFAULT_SIGNATURE_PROVIDER = "In-built E-signature"
SIGNATURE_PROVIDERS = {"In-built E-signature", "DocuSign", "Adobe Sign", "Aadhaar eSign"}


def _to_response(settings: EsignatureSettings) -> EsignatureSettingsResponse:
    return EsignatureSettingsResponse(
        reminderFrequencyDays=settings.reminder_frequency_days,
        defaultSignatureProvider=settings.default_signature_provider,
    )


def get_settings(db: Session, tenant_id: uuid.UUID) -> EsignatureSettingsResponse:
    settings = esignature_settings_repo.get_by_tenant(db, tenant_id)
    if settings is None:
        # UC7-FV-004: "When no value has been previously configured, Then the Reminder
        # Frequency (days) field defaults to 3." -- no row yet, so report the defaults
        # without persisting one; PUT is what creates the row.
        return EsignatureSettingsResponse(
            reminderFrequencyDays=DEFAULT_REMINDER_FREQUENCY_DAYS,
            defaultSignatureProvider=DEFAULT_SIGNATURE_PROVIDER,
        )
    return _to_response(settings)


def update_settings(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    payload: UpdateEsignatureSettingsRequest,
) -> EsignatureSettingsResponse:
    # UC7-FV-004: "When the value is not a whole number, Then the system rejects the entry."
    if payload.reminderFrequencyDays is not None and payload.reminderFrequencyDays < 1:
        message = "Reminder Frequency (days) must be a positive whole number."
        raise ValidationFailedError(message, details=[message])
    if (
        payload.defaultSignatureProvider is not None
        and payload.defaultSignatureProvider not in SIGNATURE_PROVIDERS
    ):
        message = (
            "Signature Method must be one of: "
            + ", ".join(sorted(SIGNATURE_PROVIDERS))
        )
        raise ValidationFailedError(message, details=[message])

    now = datetime.now(timezone.utc)
    user_uuid = uuid.UUID(user.user_id)
    settings = esignature_settings_repo.get_by_tenant(db, tenant_id)

    if settings is None:
        # UC7-FV-004: "the Tenant Admin leaves the Reminder Frequency (days) field blank,
        # When the settings are saved, Then the save succeeds because the field is
        # optional" -- fall back to the defaults for whichever field was omitted.
        settings = EsignatureSettings(
            tenant_id=tenant_id,
            reminder_frequency_days=payload.reminderFrequencyDays or DEFAULT_REMINDER_FREQUENCY_DAYS,
            default_signature_provider=payload.defaultSignatureProvider or DEFAULT_SIGNATURE_PROVIDER,
            created_by=user_uuid,
            updated_by=user_uuid,
            created_at=now,
            updated_at=now,
        )
        esignature_settings_repo.insert(db, settings)
    else:
        if payload.reminderFrequencyDays is not None:
            settings.reminder_frequency_days = payload.reminderFrequencyDays
        if payload.defaultSignatureProvider is not None:
            settings.default_signature_provider = payload.defaultSignatureProvider
        settings.updated_by = user_uuid
        settings.updated_at = now

    db.commit()
    return _to_response(settings)
