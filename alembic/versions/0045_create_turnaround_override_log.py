"""CreateTurnaroundOverrideLog

Revision ID: CreateTurnaroundOverrideLog
Revises: CreateContractTurnaroundMetrics
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateTurnaroundOverrideLog"
down_revision: Union[str, None] = "CreateContractTurnaroundMetrics"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "turnaround_override_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("original_ai_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("new_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("override_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("override_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("turnaround_override_log")
