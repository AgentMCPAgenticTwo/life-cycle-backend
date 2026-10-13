"""CreateTenantBottleneckThresholds

Revision ID: CreateTenantBottleneckThresholds
Revises: CreateTurnaroundOverrideLog
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateTenantBottleneckThresholds"
down_revision: Union[str, None] = "CreateTurnaroundOverrideLog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_bottleneck_thresholds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("threshold_days", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_threshold_tenant_stage", "tenant_bottleneck_thresholds", ["tenant_id", "stage"])


def downgrade() -> None:
    op.drop_index("idx_threshold_tenant_stage", table_name="tenant_bottleneck_thresholds")
    op.drop_table("tenant_bottleneck_thresholds")
