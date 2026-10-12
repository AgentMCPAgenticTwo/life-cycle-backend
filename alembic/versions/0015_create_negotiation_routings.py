"""CreateNegotiationRoutings

Revision ID: CreateNegotiationRoutings
Revises: CreateAskAiInteractions
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateNegotiationRoutings"
down_revision: Union[str, None] = "CreateAskAiInteractions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "negotiation_routings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("routing_type", sa.String(20), nullable=False),
        sa.Column("external_party_name", sa.String(200), nullable=False),
        sa.Column("external_party_email", sa.String(200), nullable=False),
        sa.Column("assigned_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("negotiation_status", sa.String(20), nullable=False),
        sa.Column("current_version_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "uq_negotiation_routings_contract", "negotiation_routings", ["contract_id"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_negotiation_routings_contract", table_name="negotiation_routings")
    op.drop_table("negotiation_routings")
