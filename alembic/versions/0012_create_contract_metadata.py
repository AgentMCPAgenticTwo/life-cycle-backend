"""CreateContractMetadata

Revision ID: CreateContractMetadata
Revises: CreateContractClauses
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateContractMetadata"
down_revision: Union[str, None] = "CreateContractClauses"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_metadata",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("parties", sa.Text(), nullable=True),
        sa.Column("parties_label", sa.String(20), nullable=False),
        sa.Column("contract_value", sa.Numeric(18, 2), nullable=True),
        sa.Column("contract_value_label", sa.String(20), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("start_date_label", sa.String(20), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("end_date_label", sa.String(20), nullable=False),
        sa.Column("renewal_terms", sa.Text(), nullable=True),
        sa.Column("renewal_terms_label", sa.String(20), nullable=False),
        sa.Column("payment_terms", sa.Text(), nullable=True),
        sa.Column("payment_terms_label", sa.String(20), nullable=False),
        sa.Column("key_obligations", sa.Text(), nullable=True),
        sa.Column("key_obligations_label", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "uq_contract_metadata_contract", "contract_metadata", ["contract_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_contract_metadata_contract", table_name="contract_metadata")
    op.drop_table("contract_metadata")
