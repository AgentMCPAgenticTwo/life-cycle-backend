"""`/api/v1/contracts/{contractId}/signers` and `/api/v1/contracts/{contractId}/audit-certificate`
-- thin HTTP binding over `app.services.signers`. See CLAUDE.md's UC6-UC7-combined module
section for the exact paths, roles and DTOs this router must match.
"""
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth import CurrentUser, current_tenant_id, require_roles
from app.db import get_db
from app.schemas.signer import (
    AddSignerRequest,
    AuditCertificateResponse,
    SendForSignatureRequest,
    SendForSignatureResponse,
    SignerListResponse,
    SignerResponse,
    UpdateSignerRequest,
)
from app.services import signers as signers_service

router = APIRouter(prefix="/contracts", tags=["signers"])

_VIEW_ROLES = ("CONTRACT_OWNER", "LEGAL_REVIEWER", "TENANT_ADMIN")
_CERTIFICATE_VIEW_ROLES = ("CONTRACT_OWNER", "LEGAL_REVIEWER")


@router.get("/{contractId}/signers", response_model=SignerListResponse)
def list_signers(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_VIEW_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> SignerListResponse:
    return signers_service.list_signers(db, tenant_id, user, contractId)


@router.post("/{contractId}/signers", response_model=SignerResponse, status_code=201)
def add_signer(
    contractId: uuid.UUID,
    payload: AddSignerRequest,
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> SignerResponse:
    return signers_service.add_signer(db, tenant_id, user, contractId, payload)


@router.put("/{contractId}/signers/{signerId}", response_model=SignerResponse)
def update_signer(
    contractId: uuid.UUID,
    signerId: uuid.UUID,
    payload: UpdateSignerRequest,
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> SignerResponse:
    return signers_service.update_signer(db, tenant_id, user, contractId, signerId, payload)


@router.delete("/{contractId}/signers/{signerId}", response_model=SignerResponse)
def delete_signer(
    contractId: uuid.UUID,
    signerId: uuid.UUID,
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> SignerResponse:
    return signers_service.delete_signer(db, tenant_id, user, contractId, signerId)


@router.post("/{contractId}/signers/send", response_model=SendForSignatureResponse)
def send_for_signature(
    contractId: uuid.UUID,
    payload: SendForSignatureRequest = SendForSignatureRequest(),
    user: CurrentUser = Depends(require_roles("CONTRACT_OWNER")),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> SendForSignatureResponse:
    return signers_service.send_for_signature(db, tenant_id, user, contractId, payload)


@router.get("/{contractId}/audit-certificate", response_model=AuditCertificateResponse)
def get_audit_certificate(
    contractId: uuid.UUID,
    user: CurrentUser = Depends(require_roles(*_CERTIFICATE_VIEW_ROLES)),
    tenant_id: uuid.UUID = Depends(current_tenant_id),
    db: Session = Depends(get_db),
) -> AuditCertificateResponse:
    return signers_service.get_audit_certificate(db, tenant_id, user, contractId)
