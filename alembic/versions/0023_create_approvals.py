"""CreateApprovals

Revision ID: CreateApprovals
Revises: CreateApprovalMatrixSteps
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateApprovals"
down_revision: Union[str, None] = "CreateApprovalMatrixSteps"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approvals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_owner_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approval_matrix_configs.id"),
            nullable=True,
        ),
        sa.Column("current_step_number", sa.Integer(), nullable=False),
        sa.Column("total_steps", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("ai_risk_score", sa.Integer(), nullable=True),
        sa.Column("key_terms_summary", sa.Text(), nullable=True),
        sa.Column("deviations_from_standard", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_approvals_contract", "approvals", ["contract_id"])
    op.create_index("idx_approvals_status", "approvals", ["status"])


def downgrade() -> None:
    op.drop_index("idx_approvals_status", table_name="approvals")
    op.drop_index("idx_approvals_contract", table_name="approvals")
    op.drop_table("approvals")
