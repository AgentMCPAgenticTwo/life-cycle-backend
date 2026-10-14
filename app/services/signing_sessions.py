"""Business rules for the `/api/v1/signing-sessions/{sessionId}` endpoints -- see CLAUDE.md's
UC6-UC7-combined module section and this task's stories (T-SIGNING-SESSIONS-API/TASK.md):
UC7-AF-001..003, UC7-BR-001/003/004/007/008/011/014/016..021, UC7-FV-002/003, UC7-MF-001.

There is no `signing_sessions` table in this contract (`context.json` names no table this task
owns). A signing session is one Signer row's lifecycle, and `sessionId` in the path is that
row's id -- the one opaque credential the SIGNER role is handed via the emailed link, playing
the same role a bearer token would. Because of that, these endpoints do not resolve the caller's
tenant via `current_tenant_id` (external signers added via email have no row in `users`):
access is scoped entirely by knowledge of `sessionId`, with the CONTRACT_OWNER-only resend path
additionally checking contract ownership. Recorded in this task's `blockers`.
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
from app.models.esignature import Signer
from app.models.user import User
from app.repositories import signing_sessions as repo
from app.services import notifications
from app.schemas.signing_session import (
    ApplySignatureRequest,
    ApplySignatureResponse,
    DeclineSignatureRequest,
    DeclineSignatureResponse,
    SigningSessionResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
)

_LINK_VALIDITY = timedelta(days=7)
_LOCKOUT_DURATION = timedelta(minutes=15)
_MAX_OTP_ATTEMPTS = 3

_EXPIRED_MESSAGE = "This signing link has expired. Please contact the contract owner."
_LOCKED_MESSAGE = (
    "This signing link has been locked due to too many invalid OTP attempts. Please try again later."
)
_DECLINED_MESSAGE = "Signing has been halted because a signer declined to sign this contract."
_WAIT_MESSAGE = "You must wait for prior signers to complete signing before you can act on this link."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _owner_email(db: Session, contract: Contract) -> str | None:
    owner = db.query(User).filter(User.id == contract.contract_owner_id).first()
    return owner.email if owner is not None else None


def _is_past(deadline: datetime, now: datetime) -> bool:
    """SQLite (used in tests in place of the real Postgres -- see conftest.py) does not
    round-trip timezone-aware `DateTime` columns, so a value read back can be naive even
    though it was written as aware. Compare on naive UTC wall-clock values either way."""
    if deadline.tzinfo is None:
        return deadline < now.replace(tzinfo=None)
    return deadline < now


def _actor_id(user: CurrentUser, fallback: uuid.UUID) -> uuid.UUID:
    # SIGNER callers are usually external parties with no row in `users` -- `created_by`/
    # `updated_by` are plain NOT NULL uuid columns (no FK, see app.models.mixins), so a
    # non-resolvable X-User-Id falls back to the signer's own id rather than failing the
    # write. Recorded in this task's `blockers`.
    try:
        return uuid.UUID(user.user_id)
    except (ValueError, AttributeError, TypeError):
        return fallback


def _get_signer_or_404(db: Session, session_id: uuid.UUID) -> Signer:
    signer = repo.get_signer_by_id(db, session_id)
    # A signer who has not yet been sent a link ("Pending") has no active session; the
    # response DTO's `signerStatus` enum also has no slot for it.
    if signer is None or signer.signer_status == "Pending":
        raise NotFoundError("signing session not found")
    return signer


def _get_contract_or_404(db: Session, signer: Signer) -> Contract:
    contract = repo.get_contract_by_id(db, signer.contract_id)
    if contract is None:
        raise NotFoundError("signing session not found")
    return contract


def _assert_owner_access(user: CurrentUser, contract: Contract) -> None:
    if str(contract.contract_owner_id) != user.user_id:
        raise ForbiddenError("You do not have access to this contract")


def _expire_if_due(db: Session, signer: Signer, now: datetime) -> None:
    # UC7-BR-020: Sent/Viewed signers whose link validity period has elapsed auto-transition
    # to Expired the next time the row is touched -- there is no scheduler in this sandbox to
    # do this proactively.
    if (
        signer.signer_status in ("Sent", "Viewed")
        and signer.link_expires_at is not None
        and _is_past(signer.link_expires_at, now)
    ):
        signer.signer_status = "Expired"
        db.commit()


def _prior_signers_all_signed(db: Session, signer: Signer) -> bool:
    # UC7-BR-001: eligibility is decided solely by Signing Order -- every signer whose order
    # is lower than this one must have reached Signed.
    rows = repo.list_by_contract(db, signer.contract_id)
    return all(s.signer_status == "Signed" for s in rows if s.signing_order < signer.signing_order)


def _document_url(contract: Contract) -> str:
    return f"/files/contracts/{contract.id}/document"


def _build_session_response(signer: Signer, contract: Contract, prior_signed: bool) -> SigningSessionResponse:
    otp_verified = signer.otp_verified_at is not None
    is_current_turn = prior_signed and signer.signer_status in ("Sent", "Viewed")

    blocked_message: str | None = None
    document_url: str | None = None
    signature_pad_available = False
    decline_available = False

    if signer.signer_status == "Expired":
        blocked_message = _EXPIRED_MESSAGE
    elif contract.status == "SignatureDeclined" and signer.signer_status != "Declined":
        blocked_message = _DECLINED_MESSAGE
    elif signer.signer_status == "Declined":
        blocked_message = None
    elif not prior_signed:
        blocked_message = _WAIT_MESSAGE
    elif signer.signer_status in ("Sent", "Viewed") and otp_verified:
        # UC7-BR-003/016: the document viewer and Signature Pad only reveal once OTP has
        # been verified (status has advanced from Sent to Viewed).
        document_url = _document_url(contract)
        signature_pad_available = signer.signer_status == "Viewed"
        decline_available = signer.signer_status == "Viewed"

    return SigningSessionResponse(
        sessionId=signer.id,
        contractId=contract.id,
        signerId=signer.id,
        signerName=signer.signer_name,
        signerEmail=signer.signer_email,
        signerStatus=signer.signer_status,
        isCurrentTurn=is_current_turn,
        otpVerified=otp_verified,
        documentUrl=document_url,
        signaturePadAvailable=signature_pad_available,
        declineAvailable=decline_available,
        reminderFrequencyDays=signer.reminder_frequency_days,
        linkExpired=signer.signer_status == "Expired",
        blockedMessage=blocked_message,
    )


def get_session(db: Session, user: CurrentUser, session_id: uuid.UUID) -> SigningSessionResponse:
    signer = _get_signer_or_404(db, session_id)
    contract = _get_contract_or_404(db, signer)
    now = _now()
    _expire_if_due(db, signer, now)
    prior_signed = _prior_signers_all_signed(db, signer)
    return _build_session_response(signer, contract, prior_signed)


def verify_otp(
    db: Session, user: CurrentUser, session_id: uuid.UUID, payload: VerifyOtpRequest
) -> VerifyOtpResponse:
    signer = _get_signer_or_404(db, session_id)
    contract = _get_contract_or_404(db, signer)
    now = _now()
    _expire_if_due(db, signer, now)

    if signer.signer_status == "Expired":
        raise ForbiddenError(_EXPIRED_MESSAGE)
    if contract.status == "SignatureDeclined" and signer.signer_status != "Declined":
        raise ForbiddenError(_DECLINED_MESSAGE)
    if signer.signer_status not in ("Sent", "Viewed"):
        raise ConflictError("OTP verification is not available for this signer's current status.")
    if not _prior_signers_all_signed(db, signer):
        raise ForbiddenError(_WAIT_MESSAGE)
    if signer.otp_locked_until is not None and not _is_past(signer.otp_locked_until, now):
        raise ForbiddenError(_LOCKED_MESSAGE)

    # UC7-FV-002: the OTP Field is mandatory and must be exactly 6 numeric digits.
    code = payload.otpCode or ""
    if not re.fullmatch(r"\d{6}", code):
        message = "OTP must be a 6-digit numeric code."
        raise ValidationFailedError(message, details=[message])

    if signer.otp_hash is None or hashlib.sha256(code.encode("utf-8")).hexdigest() != signer.otp_hash:
        signer.otp_attempts += 1
        locked_until = None
        error_message = "Invalid OTP. Please try again."
        attempts_remaining = max(0, _MAX_OTP_ATTEMPTS - signer.otp_attempts)
        if signer.otp_attempts >= _MAX_OTP_ATTEMPTS:
            # UC7-AF-001: the third consecutive invalid attempt locks the link for 15 minutes;
            # Signer Status remains unchanged (not advanced to Viewed).
            signer.otp_locked_until = now + _LOCKOUT_DURATION
            locked_until = signer.otp_locked_until
            attempts_remaining = 0
            error_message = "Invalid OTP. Please request a new code."
        signer.updated_by = _actor_id(user, signer.id)
        db.commit()
        return VerifyOtpResponse(
            signerStatus=signer.signer_status,
            documentUrl=None,
            signaturePadAvailable=False,
            attemptsRemaining=attempts_remaining,
            lockedUntil=locked_until,
            errorMessage=error_message,
        )

    signer.otp_verified_at = now
    signer.otp_attempts = 0
    signer.otp_locked_until = None
    if signer.signer_status == "Sent":
        signer.signer_status = "Viewed"
    signer.updated_by = _actor_id(user, signer.id)
    db.commit()
    db.refresh(signer)

    return VerifyOtpResponse(
        signerStatus=signer.signer_status,
        documentUrl=_document_url(contract),
        signaturePadAvailable=True,
        attemptsRemaining=None,
        lockedUntil=None,
        errorMessage=None,
    )


def resend_otp(db: Session, user: CurrentUser, session_id: uuid.UUID) -> SigningSessionResponse:
    signer = _get_signer_or_404(db, session_id)
    contract = _get_contract_or_404(db, signer)

    if user.role == "CONTRACT_OWNER":
        _assert_owner_access(user, contract)

    now = _now()
    _expire_if_due(db, signer, now)

    if signer.signer_status not in ("Sent", "Viewed", "Expired"):
        raise ConflictError(
            "A new signing link can only be sent while this signer's status is Sent, Viewed, or Expired."
        )

    # UC7-BR-020: re-sending generates a fresh link/OTP and reverts the Signer Status to Sent,
    # whether the prior one was locked (UC7-AF-001) or had auto-expired.
    otp_code = f"{secrets.randbelow(1_000_000):06d}"
    signer.otp_hash = hashlib.sha256(otp_code.encode("utf-8")).hexdigest()
    signer.otp_attempts = 0
    signer.otp_locked_until = None
    signer.otp_verified_at = None
    signer.link_token = secrets.token_urlsafe(32)
    signer.link_expires_at = now + _LINK_VALIDITY
    signer.signer_status = "Sent"
    signer.updated_by = _actor_id(user, signer.id)
    db.commit()
    db.refresh(signer)

    prior_signed = _prior_signers_all_signed(db, signer)
    return _build_session_response(signer, contract, prior_signed)


def apply_signature(
    db: Session,
    user: CurrentUser,
    session_id: uuid.UUID,
    payload: ApplySignatureRequest,
    ip_address: str | None,
) -> ApplySignatureResponse:
    signer = _get_signer_or_404(db, session_id)
    contract = _get_contract_or_404(db, signer)
    now = _now()
    _expire_if_due(db, signer, now)

    if signer.signer_status == "Expired":
        raise ForbiddenError(_EXPIRED_MESSAGE)
    if contract.status == "SignatureDeclined" and signer.signer_status != "Declined":
        raise ForbiddenError(_DECLINED_MESSAGE)
    # UC7-BR-003/017: a signature can only be applied once OTP has been verified (status
    # Viewed).
    if signer.signer_status != "Viewed" or signer.otp_verified_at is None:
        raise ConflictError("OTP verification must be completed before applying a signature.")
    if not _prior_signers_all_signed(db, signer):
        raise ForbiddenError(_WAIT_MESSAGE)
    # UC7-FV-003: the Signature Pad field is mandatory.
    if not payload.signatureData or not payload.signatureData.strip():
        message = "Signature Pad is mandatory."
        raise ValidationFailedError(message, details=[message])

    actor_id = _actor_id(user, signer.id)
    signer.signature_pad_data = payload.signatureData
    signer.signer_status = "Signed"
    signer.signed_at = now
    signer.ip_address = ip_address
    signer.updated_by = actor_id

    rows = repo.list_by_contract(db, contract.id)
    other_rows = [s for s in rows if s.id != signer.id]
    next_signer_id: uuid.UUID | None = None

    if all(s.signer_status == "Signed" for s in other_rows):
        # UC7-BR-007/019: Executed fires automatically on the last signature -- never on
        # manual action.
        contract.status = "Executed"
        contract.updated_by = actor_id
    else:
        remaining = sorted(
            (s for s in other_rows if s.signing_order > signer.signing_order),
            key=lambda s: s.signing_order,
        )
        if remaining:
            nxt = remaining[0]
            otp_code = f"{secrets.randbelow(1_000_000):06d}"
            nxt.otp_hash = hashlib.sha256(otp_code.encode("utf-8")).hexdigest()
            nxt.otp_attempts = 0
            nxt.otp_locked_until = None
            nxt.link_token = secrets.token_urlsafe(32)
            nxt.link_expires_at = now + _LINK_VALIDITY
            nxt.signer_status = "Sent"
            nxt.updated_by = actor_id
            next_signer_id = nxt.id

    db.commit()
    db.refresh(signer)
    db.refresh(contract)

    if contract.status == "Executed":
        # UC7-BR-007/019: everyone involved hears that the contract is executed.
        notifications.dispatch(
            db,
            contract.tenant_id,
            notifications.EVENT_EXECUTED,
            recipients=[s.signer_email for s in rows] + [_owner_email(db, contract)],
            subject=f"Contract {contract.contract_name} is executed",
            body=f"All signatures are complete. Contract {contract.contract_name} is executed.",
            entity="Contract",
            actor_id=actor_id,
        )
    elif next_signer_id is not None:
        nxt = next(s for s in rows if s.id == next_signer_id)
        notifications.dispatch(
            db,
            contract.tenant_id,
            notifications.EVENT_SENT_FOR_SIGNATURE,
            recipients=[nxt.signer_email],
            subject=f"Please sign {contract.contract_name}",
            body=(
                f"It is now your turn to sign {contract.contract_name}. Open your signing "
                "link and enter the one-time password sent to you to continue."
            ),
            entity="Signer",
            actor_id=actor_id,
        )

    return ApplySignatureResponse(
        signerId=signer.id,
        signerStatus="Signed",
        contractStatus=contract.status if contract.status == "Executed" else "Sent",
        nextSignerId=next_signer_id,
    )


def decline_signature(
    db: Session, user: CurrentUser, session_id: uuid.UUID, payload: DeclineSignatureRequest
) -> DeclineSignatureResponse:
    signer = _get_signer_or_404(db, session_id)
    contract = _get_contract_or_404(db, signer)
    now = _now()
    _expire_if_due(db, signer, now)

    if signer.signer_status == "Expired":
        raise ForbiddenError(_EXPIRED_MESSAGE)
    if contract.status == "SignatureDeclined" and signer.signer_status != "Declined":
        raise ForbiddenError(_DECLINED_MESSAGE)
    # UC7-BR-018: Decline to Sign is only available to the active signer in Viewed status.
    if signer.signer_status != "Viewed":
        raise ConflictError("Decline to Sign is only available while your status is Viewed.")
    if not payload.reason or not payload.reason.strip():
        message = "A reason is required to decline to sign."
        raise ValidationFailedError(message, details=[message])

    actor_id = _actor_id(user, signer.id)
    signer.signer_status = "Declined"
    signer.decline_reason = payload.reason
    signer.updated_by = actor_id

    # UC7-BR-008/018: halts routing to subsequent signers and the contract moves to a
    # terminal Signature Declined state -- no further reminders, no further signing.
    contract.status = "SignatureDeclined"
    contract.updated_by = actor_id

    db.commit()
    db.refresh(signer)

    # UC7-BR-008/018: the Contract Owner must learn immediately that signing has halted.
    notifications.dispatch(
        db,
        contract.tenant_id,
        notifications.EVENT_SIGNATURE_DECLINED,
        recipients=[_owner_email(db, contract)],
        subject=f"{signer.signer_name} declined to sign {contract.contract_name}",
        body=(
            f"{signer.signer_name} declined to sign {contract.contract_name}. "
            f"Reason: {signer.decline_reason}"
        ),
        entity="Contract",
        actor_id=actor_id,
    )

    return DeclineSignatureResponse(
        signerId=signer.id,
        signerStatus="Declined",
        contractStatus="SignatureDeclined",
        reason=signer.decline_reason,
    )
