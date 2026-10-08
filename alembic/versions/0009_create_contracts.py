"""CreateContracts

Revision ID: CreateContracts
Revises: CreateClauseVersions
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateContracts"
down_revision: Union[str, None] = "CreateClauseVersions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contracts",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("contract_name", sa.String(255), nullable=False),
        sa.Column("contract_type", sa.String(50), nullable=False),
        sa.Column("industry", sa.String(20), nullable=False),
        sa.Column("department", sa.String(100), nullable=True),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("templates.id"), nullable=True),
        sa.Column(
            "third_party_paper_file_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("uploaded_files.id"),
            nullable=True,
        ),
        sa.Column(
            "counterparty_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("counterparties.id"), nullable=False
        ),
        sa.Column("contract_owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("contract_value", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(10), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("renewal_type", sa.String(10), nullable=False),
        sa.Column("notice_period", sa.Integer(), nullable=True),
        sa.Column("assigned_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("idx_contracts_tenant_status", "contracts", ["tenant_id", "status"])
    op.create_index("idx_contracts_tenant_enddate", "contracts", ["tenant_id", "end_date"])
    op.create_index("idx_contracts_tenant_owner", "contracts", ["tenant_id", "contract_owner_id"])


def downgrade() -> None:
    op.drop_index("idx_contracts_tenant_owner", table_name="contracts")
    op.drop_index("idx_contracts_tenant_enddate", table_name="contracts")
    op.drop_index("idx_contracts_tenant_status", table_name="contracts")
    op.drop_table("contracts")
