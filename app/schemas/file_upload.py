"""Wire-format request/response types for the `contracts-third-party-paper` resource (see
CLAUDE.md's uc123 module section). Field names are camelCase and match the contract's
`UploadThirdPartyPaperRequest`/`FileUploadResponse` DTOs exactly.

`fileFormat` is typed `str` rather than `Literal["PDF", "DOCX"]` on purpose: context.json
marks it an enum, but UC2-AF-005 names an exact user-facing message for an unsupported
format ('Unsupported file format. Please upload PDF or DOCX only.'). A Pydantic `Literal`
would reject the field during request parsing and surface the shared generic
`{"error": "validation failed", ...}` body instead of that literal copy. Validating it as a
business rule in `app.services.files` (see there) reproduces the story's exact message, the
same precedent `app/services/contracts.py` already set for this task group.
"""
import uuid

from pydantic import BaseModel


class UploadThirdPartyPaperRequest(BaseModel):
    fileName: str
    fileContentBase64: str
    fileSize: int
    fileFormat: str


class FileUploadResponse(BaseModel):
    fileId: uuid.UUID
    fileName: str
    fileSize: int
    fileFormat: str
    storageUrl: str
