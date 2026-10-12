"""Wire-format request/response types for the `esignature-settings` resource (see
CLAUDE.md's UC6-UC7-combined module section). Field names are camelCase and match the
contract's `EsignatureSettingsResponse` / `UpdateEsignatureSettingsRequest` DTOs exactly.
"""
from pydantic import BaseModel


class EsignatureSettingsResponse(BaseModel):
    reminderFrequencyDays: int
    defaultSignatureProvider: str


class UpdateEsignatureSettingsRequest(BaseModel):
    reminderFrequencyDays: int | None = None
    defaultSignatureProvider: str | None = None
