"""CreateApprovalMatrixRules

Revision ID: CreateApprovalMatrixRules
Revises: CreateTenantUsers
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateApprovalMatrixRules"
down_revision: Union[str, None] = "CreateTenantUsers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "approval_matrix_rules",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("contract_type", sa.String(50), nullable=False),
        sa.Column("value_threshold", sa.Numeric(18, 2), nullable=False),
        sa.Column("approver_role", sa.String(50), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "uq_rule_type_threshold",
        "approval_matrix_rules",
        ["tenant_id", "contract_type", "value_threshold"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_rule_type_threshold", table_name="approval_matrix_rules")
    op.drop_table("approval_matrix_rules")
