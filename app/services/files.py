"""Business rules for the `contracts-third-party-paper` resource: validates and persists a
third party paper upload. See CLAUDE.md's uc123 module section and this task's stories
UC2-AF-005, UC2-AF-006, UC2-BR-008, UC2-MF-001 (T-CONTRACTS-THIRD-PARTY-PAPER-API/TASK.md).
"""
import base64
import binascii
import uuid

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ValidationFailedError
from app.models.uploaded_file import UploadedFile
from app.repositories import files as files_repo
from app.schemas.file_upload import FileUploadResponse, UploadThirdPartyPaperRequest

ALLOWED_FORMATS = {"PDF", "DOCX"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # UC2-AF-006: 25 MB limit


def _validate_format(payload: UploadThirdPartyPaperRequest) -> None:
    # UC2-AF-005: a format other than PDF/DOCX is rejected with this exact message.
    if payload.fileFormat.upper() not in ALLOWED_FORMATS:
        message = "Unsupported file format. Please upload PDF or DOCX only."
        raise ValidationFailedError(message, details=[message])


def _validate_size(payload: UploadThirdPartyPaperRequest) -> None:
    # UC2-AF-006: a file larger than 25 MB is rejected with this exact message.
    if payload.fileSize > MAX_FILE_SIZE_BYTES:
        message = "File size exceeds the 25 MB limit. Please upload a smaller file."
        raise ValidationFailedError(message, details=[message])


def _validate_content(payload: UploadThirdPartyPaperRequest) -> None:
    try:
        base64.b64decode(payload.fileContentBase64, validate=True)
    except (binascii.Error, ValueError) as exc:
        message = "File content must be valid base64."
        raise ValidationFailedError(message, details=[message]) from exc


def upload_third_party_paper(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: UploadThirdPartyPaperRequest
) -> FileUploadResponse:
    _validate_format(payload)
    _validate_size(payload)
    _validate_content(payload)

    user_uuid = uuid.UUID(user.user_id)
    file_id = uuid.uuid4()
    file_format = payload.fileFormat.upper()
    uploaded_file = UploadedFile(
        id=file_id,
        tenant_id=tenant_id,
        file_name=payload.fileName,
        file_size=payload.fileSize,
        file_format=file_format,
        # No object-storage dependency is configured in this repo (see CLAUDE.md's
        # "Dependencies" -- only already-declared packages may be used), so there is nowhere
        # to actually persist the uploaded bytes. storageUrl is a deterministic reference by
        # id the file could later be fetched through; this is a judgement call -- see blockers.
        storage_url=f"/files/{file_id}",
        created_by=user_uuid,
        updated_by=user_uuid,
    )
    files_repo.insert_uploaded_file(db, uploaded_file)
    db.commit()
    db.refresh(uploaded_file)

    return FileUploadResponse(
        fileId=uploaded_file.id,
        fileName=uploaded_file.file_name,
        fileSize=uploaded_file.file_size,
        fileFormat=uploaded_file.file_format,
        storageUrl=uploaded_file.storage_url,
    )
