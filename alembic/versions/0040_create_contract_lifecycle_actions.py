"""CreateContractLifecycleActions

Revision ID: CreateContractLifecycleActions
Revises: CreateRenewalAlerts
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateContractLifecycleActions"
down_revision: Union[str, None] = "CreateRenewalAlerts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_lifecycle_actions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "original_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False
        ),
        sa.Column(
            "linked_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=True
        ),
        sa.Column("action_type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("termination_reason", sa.Text(), nullable=True),
        sa.Column("effective_termination_date", sa.Date(), nullable=True),
        sa.Column("contract_end_date_snapshot", sa.Date(), nullable=True),
        sa.Column("notice_period_snapshot", sa.String(100), nullable=True),
        sa.Column("renewal_alert_banner_snapshot", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_lifecycle_actions_original", "contract_lifecycle_actions", ["original_contract_id"])


def downgrade() -> None:
    op.drop_index("idx_lifecycle_actions_original", table_name="contract_lifecycle_actions")
    op.drop_table("contract_lifecycle_actions")
