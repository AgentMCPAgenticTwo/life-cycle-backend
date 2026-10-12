"""CreateObligationAuditLog

Revision ID: CreateObligationAuditLog
Revises: CreateContractLifecycleActions
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateObligationAuditLog"
down_revision: Union[str, None] = "CreateContractLifecycleActions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "obligation_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column(
            "obligation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("obligations.id"), nullable=True
        ),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("field_name", sa.String(100), nullable=True),
        sa.Column("before_value", sa.Text(), nullable=True),
        sa.Column("after_value", sa.Text(), nullable=True),
        sa.Column("performed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("performed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_obligation_audit_contract", "obligation_audit_log", ["contract_id"])
    op.create_index("idx_obligation_audit_obligation", "obligation_audit_log", ["obligation_id"])


def downgrade() -> None:
    op.drop_index("idx_obligation_audit_obligation", table_name="obligation_audit_log")
    op.drop_index("idx_obligation_audit_contract", table_name="obligation_audit_log")
    op.drop_table("obligation_audit_log")
