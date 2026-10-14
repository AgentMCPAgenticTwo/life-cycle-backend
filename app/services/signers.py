"""Business rules for the `contracts/{contractId}/signers` and
`contracts/{contractId}/audit-certificate` endpoints this task owns -- see CLAUDE.md's
UC6-UC7-combined module section and this task's stories (T-CONTRACTS-API/TASK.md).

This task owns `signers` and the read side of `audit_certificates`, both tables created by the
foundation task for the whole UC6-UC7-combined module. The signing session itself (OTP verify,
Signature Pad, decline) and the esignature-settings screen belong to sibling tasks
(T-SIGNING-SESSIONS-API, T-ESIGNATURE-SETTINGS-API) and are out of this task's scope -- this
service only adds signers, edits/removes them pre-lock, and performs the initial
Send for Signature transition that hands the first signer(s) their link.
"""
import hashlib
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from app.models.contract import Contract
from app.models.esignature import AuditCertificate, EsignatureSettings, Signer
from app.repositories import signers as signers_repo
from app.services import contract_status
from app.services import notifications
from app.schemas.signer import (
    AddSignerRequest,
    AuditCertificateResponse,
    AuditCertificateSignerEntry,
    SendForSignatureRequest,
    SendForSignatureResponse,
    SignerListResponse,
    SignerResponse,
    UpdateSignerRequest,
)

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

# REQ-3: Send for Signature is allowed only while the contract is Pending Signature, and
# sending does not change the contract status -- Sent/Viewed/Signed/Declined are per-signer.
_SEND_PRECONDITION_MESSAGE = "Send for Signature is only available while the contract is Pending Signature."
_ALREADY_SENT_MESSAGE = "This contract has already been sent for signature."


def _already_sent(signer_rows: list[Signer]) -> bool:
    return any(s.signer_status != "Pending" for s in signer_rows)

_DOCUMENT_LOCKED_MESSAGE = (
    "This contract's document is locked and cannot be sent for signature again."
)
_LIST_LOCKED_MESSAGE = "Signer List is locked once the first signature has been collected."
_ORDER_LOCKED_MESSAGE = "Signing order cannot be changed once signing has started."
_CONNECTION_FAILED_MESSAGE = (
    "Unable to connect to the selected e-signature provider. "
    "Please try again or choose the in-built e-signature option."
)

_LINK_VALIDITY = timedelta(days=7)


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _validate_email(email: str) -> None:
    if not _EMAIL_RE.match(email):
        raise ValidationFailedError(
            "Signer Email must be a valid email address.",
            details=["Signer Email must be a valid email address."],
        )


def _load_contract_or_404(db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID) -> Contract:
    contract = signers_repo.get_contract(db, tenant_id, contract_id)
    if contract is None:
        raise NotFoundError("contract not found")
    return contract


def _assert_view_access(user: CurrentUser, contract: Contract) -> None:
    if user.role == "CONTRACT_OWNER" and str(contract.contract_owner_id) != user.user_id:
        raise ForbiddenError("You do not have access to this contract")


def _assert_owner_access(user: CurrentUser, contract: Contract) -> None:
    # Role membership (CONTRACT_OWNER) is enforced by `require_roles` at the router layer;
    # this is the per-resource ownership check CLAUDE.md's Authentication section requires
    # ("Owner/assignment checks use X-User-Id, not the role alone").
    if str(contract.contract_owner_id) != user.user_id:
        raise ForbiddenError("You do not have access to this contract")


def _is_locked(signer_rows: list[Signer]) -> bool:
    # UC7-BR-004/AF-004: the Signer List (and Signing Order specifically) locks once any
    # signer's status has reached 'Signed'.
    return any(s.signer_status == "Signed" for s in signer_rows)


def _assert_not_executed(contract: Contract) -> None:
    # UC7-BR-009: an Executed contract's signer list/document can no longer be edited or resent.
    if contract.status == "Executed":
        raise ForbiddenError(_DOCUMENT_LOCKED_MESSAGE)


def _to_response(signer: Signer) -> SignerResponse:
    return SignerResponse(
        id=signer.id,
        contractId=signer.contract_id,
        signerName=signer.signer_name,
        signerEmail=signer.signer_email,
        signerType=signer.signer_type,
        signingOrder=signer.signing_order,
        signatureMethod=signer.signature_method,
        reminderFrequencyDays=signer.reminder_frequency_days,
        signerStatus=signer.signer_status,
        otpVerifiedAt=signer.otp_verified_at,
        signaturePadCompleted=signer.signature_pad_data is not None,
        ipAddress=signer.ip_address,
        signedAt=signer.signed_at,
        declineReason=signer.decline_reason,
        linkExpiresAt=signer.link_expires_at,
    )


def _tenant_reminder_default(db: Session, tenant_id: uuid.UUID) -> int:
    # UC7-BR-013/FV-001: default Reminder Frequency is 3 days unless the Tenant Admin has
    # configured a tenant-wide value in `esignature_settings`.
    settings = db.query(EsignatureSettings).filter(EsignatureSettings.tenant_id == tenant_id).first()
    return settings.reminder_frequency_days if settings is not None else 3


def list_signers(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> SignerListResponse:
    contract = _load_contract_or_404(db, tenant_id, contract_id)
    _assert_view_access(user, contract)
    rows = signers_repo.list_by_contract(db, contract.id)
    return SignerListResponse(
        contractId=contract.id,
        signers=[_to_response(s) for s in rows],
        sendForSignatureEnabled=(
            contract_status.is_pending_signature(contract.status) and len(rows) > 0 and not _already_sent(rows)
        ),
        signingOrderLocked=_is_locked(rows),
    )


def add_signer(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, payload: AddSignerRequest
) -> SignerResponse:
    contract = _load_contract_or_404(db, tenant_id, contract_id)
    _assert_owner_access(user, contract)
    _assert_not_executed(contract)

    rows = signers_repo.list_by_contract(db, contract.id)
    if _is_locked(rows):
        raise ForbiddenError(_LIST_LOCKED_MESSAGE)

    _validate_email(payload.signerEmail)

    if payload.signingOrder < 1:
        raise ValidationFailedError(
            "Signing Order must be a whole number starting at 1.",
            details=["Signing Order must be a whole number starting at 1."],
        )
    if any(s.signing_order == payload.signingOrder for s in rows):
        raise ValidationFailedError(
            "Signing Order must be unique within the Signer List.",
            details=["Signing Order must be unique within the Signer List."],
        )

    actor_id = uuid.UUID(user.user_id)
    signer = Signer(
        contract_id=contract.id,
        signer_name=payload.signerName,
        signer_email=payload.signerEmail,
        signer_type=payload.signerType,
        signing_order=payload.signingOrder,
        signature_method=payload.signatureMethod,
        reminder_frequency_days=_tenant_reminder_default(db, tenant_id),
        # UC7-BR-015: signers start at a default pre-send status distinct from the four
        # post-send states (Sent/Viewed/Signed/Declined) this contract's own DTOs enumerate --
        # added as this task's one additional enum value, recorded in `blockers`.
        signer_status="Pending",
        otp_attempts=0,
        created_by=actor_id,
        updated_by=actor_id,
    )
    signers_repo.insert_signer(db, signer)
    db.commit()
    db.refresh(signer)
    return _to_response(signer)


def _load_signer_or_404(db: Session, contract: Contract, signer_id: uuid.UUID) -> Signer:
    signer = signers_repo.get_by_id(db, contract.id, signer_id)
    if signer is None:
        raise NotFoundError("signer not found")
    return signer


def update_signer(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    signer_id: uuid.UUID,
    payload: UpdateSignerRequest,
) -> SignerResponse:
    contract = _load_contract_or_404(db, tenant_id, contract_id)
    _assert_owner_access(user, contract)
    _assert_not_executed(contract)

    rows = signers_repo.list_by_contract(db, contract.id)
    signer = next((s for s in rows if s.id == signer_id), None)
    if signer is None:
        raise NotFoundError("signer not found")

    locked = _is_locked(rows)
    if locked:
        if payload.signingOrder is not None and payload.signingOrder != signer.signing_order:
            raise ForbiddenError(_ORDER_LOCKED_MESSAGE)
        other_changes = any(
            getattr(payload, field) is not None
            for field in ("signerName", "signerEmail", "signerType", "signatureMethod")
        )
        if other_changes:
            raise ForbiddenError(_LIST_LOCKED_MESSAGE)

    if payload.signerEmail is not None:
        _validate_email(payload.signerEmail)
        signer.signer_email = payload.signerEmail
    if payload.signerName is not None:
        signer.signer_name = payload.signerName
    if payload.signerType is not None:
        signer.signer_type = payload.signerType
    if payload.signatureMethod is not None:
        signer.signature_method = payload.signatureMethod
    if payload.signingOrder is not None and payload.signingOrder != signer.signing_order:
        if payload.signingOrder < 1:
            raise ValidationFailedError(
                "Signing Order must be a whole number starting at 1.",
                details=["Signing Order must be a whole number starting at 1."],
            )
        if any(s.id != signer.id and s.signing_order == payload.signingOrder for s in rows):
            raise ValidationFailedError(
                "Signing Order must be unique within the Signer List.",
                details=["Signing Order must be unique within the Signer List."],
            )
        signer.signing_order = payload.signingOrder

    signer.updated_by = uuid.UUID(user.user_id)
    db.commit()
    db.refresh(signer)
    return _to_response(signer)


def delete_signer(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, signer_id: uuid.UUID
) -> SignerResponse:
    contract = _load_contract_or_404(db, tenant_id, contract_id)
    _assert_owner_access(user, contract)
    _assert_not_executed(contract)

    rows = signers_repo.list_by_contract(db, contract.id)
    signer = next((s for s in rows if s.id == signer_id), None)
    if signer is None:
        raise NotFoundError("signer not found")

    if _is_locked(rows):
        raise ForbiddenError(_LIST_LOCKED_MESSAGE)

    response = _to_response(signer)
    signers_repo.delete_signer(db, signer)
    db.commit()
    return response


def send_for_signature(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, payload: SendForSignatureRequest
) -> SendForSignatureResponse:
    contract = _load_contract_or_404(db, tenant_id, contract_id)
    _assert_owner_access(user, contract)
    _assert_not_executed(contract)

    rows = signers_repo.list_by_contract(db, contract.id)
    if not rows:
        # UC7-BR-002/BR-015: Send for Signature stays disabled/blocked with an empty list.
        raise ValidationFailedError(
            "At least one signer is required before sending for signature.",
            details=["At least one signer is required before sending for signature."],
        )

    if not contract_status.is_pending_signature(contract.status):
        raise ConflictError(_SEND_PRECONDITION_MESSAGE, details=[_SEND_PRECONDITION_MESSAGE])
    if _already_sent(rows):
        raise ConflictError(_ALREADY_SENT_MESSAGE, details=[_ALREADY_SENT_MESSAGE])

    actor_id = uuid.UUID(user.user_id)

    # UC7-AF-005: the Contract Owner may override the Signature Method at send time (e.g. to
    # retry via the in-built option after a connection failure) without re-entering the rest
    # of each signer's data.
    if payload.signatureMethod is not None:
        for s in rows:
            s.signature_method = payload.signatureMethod
            s.updated_by = actor_id

    # No real DocuSign/Adobe Sign/Aadhaar eSign integration exists in this repo (CLAUDE.md
    # permits only already-declared dependencies) -- selecting any integrated provider always
    # fails to connect, while 'In-built E-signature' is this backend's own OTP + Signature Pad
    # flow and always succeeds. Recorded in this task's `blockers`.
    if any(s.signature_method != "In-built E-signature" for s in rows):
        db.commit()
        for s in rows:
            db.refresh(s)
        return SendForSignatureResponse(
            contractId=contract.id,
            contractStatus="SignatureConnectionFailed",
            signers=[_to_response(s) for s in rows],
            errorMessage=_CONNECTION_FAILED_MESSAGE,
        )

    first_order = min(s.signing_order for s in rows)
    now = datetime.now(timezone.utc)
    for s in rows:
        if s.signing_order == first_order:
            otp_code = f"{secrets.randbelow(1_000_000):06d}"
            s.otp_hash = hashlib.sha256(otp_code.encode("utf-8")).hexdigest()
            s.otp_attempts = 0
            s.otp_locked_until = None
            s.link_token = secrets.token_urlsafe(32)
            s.link_expires_at = now + _LINK_VALIDITY
            s.signer_status = "Sent"
        s.updated_by = actor_id

    # Normalises a row still on a legacy value; a Pending Signature contract stays as it is.
    contract.status = contract_status.PENDING_SIGNATURE
    contract.updated_by = actor_id
    db.commit()
    for s in rows:
        db.refresh(s)

    # UC7: the first signer in the order is the one holding a live link right now -- the
    # shared notification service mails it to them, gated on Settings > Notifications.
    notifications.dispatch(
        db,
        tenant_id,
        notifications.EVENT_SENT_FOR_SIGNATURE,
        recipients=[s.signer_email for s in rows if s.signing_order == first_order],
        subject=f"Please sign {contract.contract_name}",
        body=(
            f"You have been asked to sign {contract.contract_name}. Open your signing link "
            "and enter the one-time password sent to you to continue."
        ),
        entity="Signer",
        actor_id=actor_id,
    )

    return SendForSignatureResponse(
        contractId=contract.id,
        contractStatus=contract.status,
        signers=[_to_response(s) for s in rows],
        errorMessage=None,
    )


def get_audit_certificate(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> AuditCertificateResponse:
    contract = _load_contract_or_404(db, tenant_id, contract_id)
    _assert_view_access(user, contract)

    if contract.status != "Executed":
        # UC7-BR-005/FV-005: the certificate does not exist/is not released until Executed.
        raise NotFoundError("audit certificate is only available once the contract is Executed")

    certificate = signers_repo.get_audit_certificate(db, contract.id)
    rows = signers_repo.list_by_contract(db, contract.id)
    entries = [
        AuditCertificateSignerEntry(
            signerName=s.signer_name,
            signerEmail=s.signer_email,
            signerType=s.signer_type,
            signingOrder=s.signing_order,
            signatureMethod=s.signature_method,
            reminderFrequencyDays=s.reminder_frequency_days,
            signerStatus=s.signer_status,
            ipAddress=s.ip_address,
            signedAt=s.signed_at,
            otpVerifiedAt=s.otp_verified_at,
            signaturePadCompleted=s.signature_pad_data is not None,
        )
        for s in rows
    ]

    if certificate is None:
        # UC7-BR-005/MF-001: the certificate is generated once every signer has signed; no
        # other task in this module's current scope creates this row (the signing-session
        # endpoints that finalize signing belong to a sibling task), so it is lazily
        # materialized here on first read. Recorded in this task's `blockers`.
        actor_id = uuid.UUID(user.user_id)
        now = datetime.now(timezone.utc)
        certificate = AuditCertificate(
            contract_id=contract.id,
            generated_at=now,
            file_url=f"/files/audit-certificates/{contract.id}",
            data_snapshot={"signers": [e.model_dump(mode="json") for e in entries]},
            created_by=actor_id,
            updated_by=actor_id,
        )
        signers_repo.insert_audit_certificate(db, certificate)
        db.commit()
        db.refresh(certificate)

    return AuditCertificateResponse(
        contractId=contract.id,
        generatedAt=certificate.generated_at,
        downloadUrl=certificate.file_url,
        signers=entries,
    )
