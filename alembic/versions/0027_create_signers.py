"""CreateSigners

Revision ID: CreateSigners
Revises: CreateApprovalAuditLog
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateSigners"
down_revision: Union[str, None] = "CreateApprovalAuditLog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("signer_name", sa.String(200), nullable=False),
        sa.Column("signer_email", sa.String(320), nullable=False),
        sa.Column("signer_type", sa.String(20), nullable=False),
        sa.Column("signing_order", sa.Integer(), nullable=False),
        sa.Column("signature_method", sa.String(40), nullable=False),
        sa.Column("reminder_frequency_days", sa.Integer(), nullable=True),
        sa.Column("signer_status", sa.String(20), nullable=False),
        sa.Column("otp_hash", sa.String(255), nullable=True),
        sa.Column("otp_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("otp_locked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("otp_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("signature_pad_data", sa.Text(), nullable=True),
        sa.Column("signed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("decline_reason", sa.Text(), nullable=True),
        sa.Column("link_token", sa.String(255), nullable=True),
        sa.Column("link_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_signers_contract_order", "signers", ["contract_id", "signing_order"])


def downgrade() -> None:
    op.drop_index("idx_signers_contract_order", table_name="signers")
    op.drop_table("signers")
