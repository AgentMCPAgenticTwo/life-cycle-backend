"""CreateApprovalAuditLog

Revision ID: CreateApprovalAuditLog
Revises: CreateApprovalDelegations
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateApprovalAuditLog"
down_revision: Union[str, None] = "CreateApprovalDelegations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "approval_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approvals.id"),
            nullable=False,
        ),
        sa.Column("contract_title", sa.String(500), nullable=False),
        sa.Column("contract_type", sa.String(100), nullable=False),
        sa.Column("contract_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("counterparty_name", sa.String(300), nullable=False),
        sa.Column("key_terms_summary", sa.Text(), nullable=True),
        sa.Column("deviations_from_standard", sa.Text(), nullable=True),
        sa.Column("ai_risk_score", sa.Integer(), nullable=True),
        sa.Column("approval_matrix_step_label", sa.String(200), nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_role", sa.String(50), nullable=False),
        sa.Column("acting_as_delegate_for", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delegate_to_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("delegate_to_name", sa.String(200), nullable=True),
        sa.Column("prior_state", sa.String(30), nullable=False),
        sa.Column("new_state", sa.String(30), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("retention_expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_approval_audit_log_approval", "approval_audit_log", ["approval_id"])


def downgrade() -> None:
    op.drop_index("idx_approval_audit_log_approval", table_name="approval_audit_log")
    op.drop_table("approval_audit_log")
