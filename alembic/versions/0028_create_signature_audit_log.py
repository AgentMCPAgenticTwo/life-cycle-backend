"""CreateSignatureAuditLog

Revision ID: CreateSignatureAuditLog
Revises: CreateSigners
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateSignatureAuditLog"
down_revision: Union[str, None] = "CreateSigners"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "signature_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "signer_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("signers.id"),
            nullable=False,
        ),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("ip_address", sa.String(64), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_signature_audit_log_signer", "signature_audit_log", ["signer_id"])
    op.create_index("idx_signature_audit_log_contract", "signature_audit_log", ["contract_id"])


def downgrade() -> None:
    op.drop_index("idx_signature_audit_log_contract", table_name="signature_audit_log")
    op.drop_index("idx_signature_audit_log_signer", table_name="signature_audit_log")
    op.drop_table("signature_audit_log")
