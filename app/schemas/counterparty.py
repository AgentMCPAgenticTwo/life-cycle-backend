"""Wire-format request/response types for the `counterparties` resource (see CLAUDE.md's
uc123 module section). Field names are camelCase and match the contract's
`CounterpartyResponse`, `CounterpartySearchResponse` and `CreateCounterpartyRequest` DTOs
exactly.
"""
import uuid

from pydantic import BaseModel


class CounterpartyResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    company: str
    address: str | None = None
    gstTaxId: str | None = None


class CounterpartySearchResponse(BaseModel):
    items: list[CounterpartyResponse]
    duplicateWarning: str | None = None


class CreateCounterpartyRequest(BaseModel):
    name: str
    email: str
    company: str
    address: str | None = None
    gstTaxId: str | None = None
