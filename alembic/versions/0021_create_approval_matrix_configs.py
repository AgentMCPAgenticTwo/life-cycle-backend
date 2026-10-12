"""CreateApprovalMatrixConfigs

Revision ID: CreateApprovalMatrixConfigs
Revises: CreateNegotiationReminders
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateApprovalMatrixConfigs"
down_revision: Union[str, None] = "CreateNegotiationReminders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_matrix_configs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("contract_type", sa.String(100), nullable=False),
        sa.Column("value_min", sa.Numeric(18, 2), nullable=True),
        sa.Column("value_max", sa.Numeric(18, 2), nullable=True),
        sa.Column("risk_band_min", sa.Integer(), nullable=True),
        sa.Column("risk_band_max", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "idx_approval_matrix_configs_tenant_type",
        "approval_matrix_configs",
        ["tenant_id", "contract_type"],
    )


def downgrade() -> None:
    op.drop_index("idx_approval_matrix_configs_tenant_type", table_name="approval_matrix_configs")
    op.drop_table("approval_matrix_configs")
