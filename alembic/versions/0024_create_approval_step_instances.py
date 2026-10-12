"""CreateApprovalStepInstances

Revision ID: CreateApprovalStepInstances
Revises: CreateApprovals
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateApprovalStepInstances"
down_revision: Union[str, None] = "CreateApprovals"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_step_instances",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "approval_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approvals.id"),
            nullable=False,
        ),
        sa.Column("step_number", sa.Integer(), nullable=False),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("acted_by", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acted_as_delegate_for", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "idx_approval_step_instances_approval_step",
        "approval_step_instances",
        ["approval_id", "step_number"],
    )


def downgrade() -> None:
    op.drop_index("idx_approval_step_instances_approval_step", table_name="approval_step_instances")
    op.drop_table("approval_step_instances")
