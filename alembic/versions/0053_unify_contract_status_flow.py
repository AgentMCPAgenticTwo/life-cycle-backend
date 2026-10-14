"""UnifyContractStatusFlow

Data-only migration for the contract status flow fix (see app/services/contract_status.py):

* "Ready For Signature" and "Sent" are no longer contract statuses -> "Pending Signature".
* "SignatureDeclined" -> "Signature Declined".
* An approval whose last step was approved is "Approved" (was "ReadyForSignature").
* A Draft contract that was already routed for review is "In Negotiation".
* An approval left open by an old Send Back (its contract is back In Negotiation) is closed
  as "SentBack" and its negotiation re-opened, so the next Mark as Agreed starts a new request.

Revision ID: UnifyContractStatusFlow
Revises: AddUserCredentialsAndRefreshTokens
Create Date: 2026-10-14

"""
from typing import Sequence, Union

from alembic import op

revision: str = "UnifyContractStatusFlow"
down_revision: Union[str, None] = "AddUserCredentialsAndRefreshTokens"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "UPDATE contracts SET status = 'Pending Signature' "
        "WHERE status IN ('Ready For Signature', 'Sent')"
    )
    op.execute("UPDATE contracts SET status = 'Signature Declined' WHERE status = 'SignatureDeclined'")
    op.execute("UPDATE approvals SET status = 'Approved' WHERE status = 'ReadyForSignature'")
    op.execute(
        "UPDATE contracts SET status = 'In Negotiation' "
        "WHERE status = 'Draft' AND id IN (SELECT contract_id FROM negotiation_routings)"
    )
    op.execute(
        "UPDATE negotiation_routings SET negotiation_status = 'Sent Back' "
        "WHERE negotiation_status = 'Agreed' AND contract_id IN ("
        "  SELECT a.contract_id FROM approvals a JOIN contracts c ON c.id = a.contract_id "
        "  WHERE a.status = 'PendingApproval' AND c.status = 'In Negotiation')"
    )
    op.execute(
        "UPDATE approvals SET status = 'SentBack' "
        "WHERE status = 'PendingApproval' AND contract_id IN ("
        "  SELECT id FROM contracts WHERE status = 'In Negotiation')"
    )


def downgrade() -> None:
    # Data-only and lossy in the forward direction (two old values fold into one); the old
    # values are still readable by the application, so there is nothing to restore.
    pass
