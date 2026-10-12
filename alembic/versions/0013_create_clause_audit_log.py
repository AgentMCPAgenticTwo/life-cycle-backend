"""CreateClauseAuditLog

Revision ID: CreateClauseAuditLog
Revises: CreateContractMetadata
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateClauseAuditLog"
down_revision: Union[str, None] = "CreateContractMetadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clause_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column(
            "clause_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contract_clauses.id"), nullable=True
        ),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action_type", sa.String(30), nullable=False),
        sa.Column("field_name", sa.String(50), nullable=True),
        sa.Column("before_text", sa.Text(), nullable=True),
        sa.Column("after_text", sa.Text(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "idx_clause_audit_log_contract_occurred", "clause_audit_log", ["contract_id", "occurred_at"]
    )


def downgrade() -> None:
    op.drop_index("idx_clause_audit_log_contract_occurred", table_name="clause_audit_log")
    op.drop_table("clause_audit_log")
