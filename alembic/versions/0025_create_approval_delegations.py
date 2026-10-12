"""CreateApprovalDelegations

Revision ID: CreateApprovalDelegations
Revises: CreateApprovalStepInstances
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateApprovalDelegations"
down_revision: Union[str, None] = "CreateApprovalStepInstances"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_delegations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "approval_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("approvals.id"),
            nullable=False,
        ),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("delegate_to_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_approval_delegations_approval", "approval_delegations", ["approval_id"])
    op.create_index(
        "idx_approval_delegations_delegate", "approval_delegations", ["delegate_to_user_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_approval_delegations_delegate", table_name="approval_delegations")
    op.drop_index("idx_approval_delegations_approval", table_name="approval_delegations")
    op.drop_table("approval_delegations")
