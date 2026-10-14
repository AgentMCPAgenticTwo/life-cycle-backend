"""`/api/v1/contracts/{contractId}/...` sub-resources (document, versions, activity-log,
folder-tags, obligations, renewal, renew, amend, terminate) and `/api/v1/folder-tags` -- thin
HTTP bindings over `app.services.contract_lifecycle`. See CLAUDE.md's "life cycle uc8 uc9"
module section for the exact paths, roles and DTOs these routers must match.

`GET /api/v1/contracts` and `GET /api/v1/contracts/{contractId}` are intentionally absent --
see this task's `blockers`.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.auth import (
    CurrentUser,
    current_tenant_id,
    file_access_tenant_id,
    file_access_user,
    require_roles,
)
from app.db import get_db
from app.schemas.contract_lifecycle import (
    ActivityLogListResponse,
    AssignFolderTagRequest,
    ContractDocumentResponse,
    ContractFolderTagResponse,
    ContractVersionListResponse,
    CreateObligationRequest,
    DocumentDownloadResponse,
    FolderTagOptionResponse,
    LinkedContractActionResponse,
    ObligationListResponse,
    ObligationResponse,
    RenewalPanelResponse,
    TerminateContractRequest,
    UpdateObligationRequest,
)
from app.schemas.pagination import PageParams
from app.services import contract_lifecycle as service

router = APIRouter(prefix="/contracts", tags=["contract-lifecycle"])
folder_tags_router = APIRouter(prefix="/folder-tags", tags=["contract-lifecycle"])

_ALL_ROLES = ("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER", "APPROVER")
_OWNER_ROLES = ("TENANT_ADMIN", "CONTRACT_OWNER")
_OBLIGATION_READ_ROLES = ("TENANT_ADMIN", "CONTRACT_OWNER", "LEGAL_REVIEWER")


@router.get("/{contractId}/document", response_model=ContractDocumentResponse)
def get_document(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ContractDocumentResponse:
    return service.get_document(db, tenant_id, user, contractId)


@router.get("/{contractId}/document/download", response_model=DocumentDownloadResponse)
def download_document(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> DocumentDownloadResponse:
    return service.download_document(db, tenant_id, user, contractId)


@router.get("/{contractId}/document/file")
def get_document_file(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(file_access_user),
    tenant_id: uuid.UUID = Depends(file_access_tenant_id),
    db: Session = Depends(get_db),
) -> Response:
    """The raw bytes a `DocumentDownloadResponse.fileUrl` points at -- the browser follows
    that URL directly, so this returns the file itself rather than a JSON body. Authenticated
    by the bearer token when one is sent, otherwise by the signed `token` in the fileUrl."""
    if user.role not in _ALL_ROLES:
        raise HTTPException(
            status_code=403, detail=f"role {user.role} is not permitted for this endpoint"
        )
    content, content_type, file_name = service.get_document_file(db, tenant_id, user, contractId)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get("/{contractId}/versions", response_model=ContractVersionListResponse)
def list_versions(
    contractId: uuid.UUID,
    page_params: PageParams = Depends(),
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ContractVersionListResponse:
    return service.list_versions(db, tenant_id, user, contractId, page_params)


@router.get("/{contractId}/activity-log", response_model=ActivityLogListResponse)
def list_activity_log(
    contractId: uuid.UUID,
    page_params: PageParams = Depends(),
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ActivityLogListResponse:
    return service.list_activity_log(db, tenant_id, user, contractId, page_params)


@router.post("/{contractId}/folder-tags", response_model=ContractFolderTagResponse)
def assign_folder_tags(
    contractId: uuid.UUID,
    payload: AssignFolderTagRequest,
    user: CurrentUser = Depends(require_roles(*_OWNER_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ContractFolderTagResponse:
    return service.assign_folder_tags(db, tenant_id, user, contractId, payload)


@router.get("/{contractId}/obligations", response_model=ObligationListResponse)
def list_obligations(
    contractId: uuid.UUID,
    page_params: PageParams = Depends(),
    user: CurrentUser = Depends(require_roles(*_OBLIGATION_READ_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ObligationListResponse:
    return service.list_obligations(db, tenant_id, user, contractId, page_params)


@router.post("/{contractId}/obligations", response_model=ObligationResponse, status_code=201)
def create_obligation(
    contractId: uuid.UUID,
    payload: CreateObligationRequest,
    user: CurrentUser = Depends(require_roles(*_OWNER_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ObligationResponse:
    return service.create_obligation(db, tenant_id, user, contractId, payload)


@router.patch("/{contractId}/obligations/{obligationId}", response_model=ObligationResponse)
def update_obligation(
    contractId: uuid.UUID,
    obligationId: uuid.UUID,
    payload: UpdateObligationRequest,
    user: CurrentUser = Depends(require_roles(*_OWNER_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ObligationResponse:
    return service.update_obligation(db, tenant_id, user, contractId, obligationId, payload)


@router.post("/{contractId}/obligations/{obligationId}/accept", response_model=ObligationResponse)
def accept_obligation(
    contractId: uuid.UUID,
    obligationId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_OWNER_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> ObligationResponse:
    return service.accept_obligation(db, tenant_id, user, contractId, obligationId)


@router.get("/{contractId}/renewal", response_model=RenewalPanelResponse)
def get_renewal(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_OBLIGATION_READ_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> RenewalPanelResponse:
    return service.get_renewal_panel(db, tenant_id, user, contractId)


@router.post("/{contractId}/renew", response_model=LinkedContractActionResponse)
def renew_contract(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_OWNER_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> LinkedContractActionResponse:
    return service.renew_contract(db, tenant_id, user, contractId)


@router.post("/{contractId}/amend", response_model=LinkedContractActionResponse)
def amend_contract(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_OWNER_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> LinkedContractActionResponse:
    return service.amend_contract(db, tenant_id, user, contractId)


@router.post("/{contractId}/terminate", response_model=LinkedContractActionResponse)
def terminate_contract(
    contractId: uuid.UUID,
    payload: TerminateContractRequest,
    user: CurrentUser = Depends(require_roles(*_OWNER_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> LinkedContractActionResponse:
    return service.terminate_contract(db, tenant_id, user, contractId, payload)


@folder_tags_router.get("", response_model=list[FolderTagOptionResponse])
def list_folder_tags(
    user: CurrentUser = Depends(require_roles(*_ALL_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> list[FolderTagOptionResponse]:
    return service.list_folder_tag_options(db, tenant_id)
