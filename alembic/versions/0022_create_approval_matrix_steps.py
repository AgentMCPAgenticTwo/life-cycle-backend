"""CreateApprovalMatrixSteps

Revision ID: CreateApprovalMatrixSteps
Revises: CreateApprovalMatrixConfigs
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateApprovalMatrixSteps"
down_revision: Union[str, None] = "CreateApprovalMatrixConfigs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_matrix_steps",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "config_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approval_matrix_configs.id"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("step_name", sa.String(200), nullable=False),
        sa.Column("approver_role", sa.String(100), nullable=True),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "idx_approval_matrix_steps_config_step",
        "approval_matrix_steps",
        ["config_id", "step_number"],
    )


def downgrade() -> None:
    op.drop_index("idx_approval_matrix_steps_config_step", table_name="approval_matrix_steps")
    op.drop_table("approval_matrix_steps")
