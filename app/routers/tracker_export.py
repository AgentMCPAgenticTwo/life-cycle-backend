"""`/api/v1/tracker/export` -- thin HTTP binding over `app.services.tracker_export`.
See CLAUDE.md's lifecycle-uc10-uc11 module section and TASK.md (T-TRACKER-EXPORT-API)
for the exact path, roles and DTOs.
"""
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.tracker_export import TrackerExportRequest, TrackerExportResponse
from app.services import tracker_export as export_service

router = APIRouter(prefix="/tracker", tags=["tracker"])


@router.post("/export", response_model=TrackerExportResponse)
def export_tracker_tab(
    payload: TrackerExportRequest,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> TrackerExportResponse:
    return export_service.export_tracker_tab(db, tenant_id, user, payload)


@router.get("/exports/{fileId}")
def download_export_file(
    fileId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> Response:
    """Serves the bytes behind a `TrackerExportResponse.fileUrl`. Not a tab DTO, so it
    returns the file itself rather than a JSON body."""
    content, content_type, file_name = export_service.get_export_file(db, tenant_id, fileId)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
