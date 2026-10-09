"""`POST /api/v1/contracts/third-party-paper` -- thin HTTP binding over
`app.services.files`. See CLAUDE.md's uc123 module section and TASK.md
(T-CONTRACTS-THIRD-PARTY-PAPER-API) for the exact path, roles and DTOs this router must match.

A separate router/file from `app/routers/contracts.py` on purpose: that file belongs to
T-CONTRACTS-API, a different task group in this module. Per CLAUDE.md's "Adding a module
without breaking the last one", this task adds its own handler alongside the existing ones
rather than editing code another task owns.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.file_upload import FileUploadResponse, UploadThirdPartyPaperRequest
from app.services import files as files_service

router = APIRouter(prefix="/contracts", tags=["contracts"])


@router.post("/third-party-paper", response_model=FileUploadResponse, status_code=201)
def upload_third_party_paper(
    payload: UploadThirdPartyPaperRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> FileUploadResponse:
    return files_service.upload_third_party_paper(db, tenant_id, user, payload)
