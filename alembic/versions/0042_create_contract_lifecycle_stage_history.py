"""CreateContractLifecycleStageHistory

Revision ID: CreateContractLifecycleStageHistory
Revises: CreateObligationAuditLog
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateContractLifecycleStageHistory"
down_revision: Union[str, None] = "CreateObligationAuditLog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_lifecycle_stage_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("stage", sa.String(30), nullable=False),
        sa.Column("stage_start_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stage_end_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("contracts_owned_snapshot", sa.Integer(), nullable=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("idx_stage_history_contract", "contract_lifecycle_stage_history", ["contract_id"])


def downgrade() -> None:
    op.drop_index("idx_stage_history_contract", table_name="contract_lifecycle_stage_history")
    op.drop_table("contract_lifecycle_stage_history")
