"""The one contract status flow, shared by every module that moves `contracts.status`:

    Draft -> In Negotiation -> Pending Approval -> Pending Signature -> Executed

with Rejected (an approver rejects) and Signature Declined (a signer declines) as the other
outcomes. "Ready For Signature" and "Sent" are no longer contract statuses -- Sent, Viewed,
Signed and Declined are per-signer states only (see migration 0053, which rewrites rows still
holding the old values).

`transition` is the single place a workflow step changes the status, so every change lands in
the contract's Activity Log.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_lifecycle import ActivityLogEntry
from app.repositories import contract_lifecycle as lifecycle_repo

DRAFT = "Draft"
IN_NEGOTIATION = "In Negotiation"
PENDING_APPROVAL = "Pending Approval"
PENDING_SIGNATURE = "Pending Signature"
EXECUTED = "Executed"
REJECTED = "Rejected"
SIGNATURE_DECLINED = "Signature Declined"

# Values written before the flow was unified. Read paths still recognise them so a row the
# migration has not reached yet behaves like its replacement.
LEGACY_PENDING_SIGNATURE = {"Ready For Signature", "Sent"}
LEGACY_SIGNATURE_DECLINED = "SignatureDeclined"

ACTIVITY_ACTION_STATUS_CHANGE = "STATUS_CHANGE"

# Negotiation (routing) statuses the approval flow reads or writes.
NEGOTIATION_AGREED = "Agreed"
# Set when an approver sends the contract back: the negotiation is open again and may be
# re-submitted for review or marked Agreed once more.
NEGOTIATION_SENT_BACK = "Sent Back"


def is_pending_signature(status: str) -> bool:
    return status == PENDING_SIGNATURE or status in LEGACY_PENDING_SIGNATURE


def is_signature_declined(status: str) -> bool:
    return status in (SIGNATURE_DECLINED, LEGACY_SIGNATURE_DECLINED)


def transition(
    db: Session, contract: Contract, new_status: str, actor_id: uuid.UUID, reason: str | None = None
) -> None:
    """Set the contract's status and append the change to its Activity Log. Does not commit --
    the caller's own unit of work decides whether the change sticks."""
    old_status = contract.status
    now = datetime.now(timezone.utc)
    contract.status = new_status
    contract.updated_by = actor_id
    contract.updated_at = now
    if old_status == new_status:
        return
    details = f"Status changed from {old_status} to {new_status}"
    if reason:
        details = f"{details}: {reason}"
    lifecycle_repo.insert_activity_log(
        db,
        ActivityLogEntry(
            id=uuid.uuid4(),
            contract_id=contract.id,
            action_type=ACTIVITY_ACTION_STATUS_CHANGE,
            performed_by=actor_id,
            performed_at=now,
            details=details,
            created_by=actor_id,
        ),
    )
