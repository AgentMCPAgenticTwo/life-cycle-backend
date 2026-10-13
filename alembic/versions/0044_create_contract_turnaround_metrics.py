"""CreateContractTurnaroundMetrics

Revision ID: CreateContractTurnaroundMetrics
Revises: CreateContractOwners
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateContractTurnaroundMetrics"
down_revision: Union[str, None] = "CreateContractOwners"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_turnaround_metrics",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("estimated_turnaround_days", sa.Numeric(18, 2), nullable=True),
        sa.Column("estimated_turnaround_source", sa.String(20), nullable=True),
        sa.Column("actual_turnaround_days", sa.Numeric(18, 2), nullable=True),
        sa.Column("excluded_from_averages", sa.Boolean(), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("idx_turnaround_contract", "contract_turnaround_metrics", ["contract_id"])


def downgrade() -> None:
    op.drop_index("idx_turnaround_contract", table_name="contract_turnaround_metrics")
    op.drop_table("contract_turnaround_metrics")
