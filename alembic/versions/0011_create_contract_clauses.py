"""CreateContractClauses

Revision ID: CreateContractClauses
Revises: CreateContractTasks
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateContractClauses"
down_revision: Union[str, None] = "CreateContractTasks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_clauses",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("clause_category", sa.String(50), nullable=True),
        sa.Column("library_match_status", sa.String(20), nullable=False),
        sa.Column("risk_score", sa.String(10), nullable=False),
        sa.Column("ai_explanation", sa.Text(), nullable=True),
        sa.Column("suggested_text", sa.Text(), nullable=True),
        sa.Column("clause_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("mandatory_flag_cleared", sa.Boolean(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index("idx_contract_clauses_contract", "contract_clauses", ["contract_id"])
    op.create_index(
        "idx_contract_clauses_contract_status", "contract_clauses", ["contract_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("idx_contract_clauses_contract_status", table_name="contract_clauses")
    op.drop_index("idx_contract_clauses_contract", table_name="contract_clauses")
    op.drop_table("contract_clauses")
