"""CreateNegotiationVersions

Revision ID: CreateNegotiationVersions
Revises: CreateNegotiationReviewers
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateNegotiationVersions"
down_revision: Union[str, None] = "CreateNegotiationReviewers"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "negotiation_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column(
            "negotiation_routing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("negotiation_routings.id"),
            nullable=False,
        ),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(10), nullable=False),
        sa.Column("document_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "uq_negotiation_versions_contract_version",
        "negotiation_versions",
        ["contract_id", "version_number"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_negotiation_versions_contract_version", table_name="negotiation_versions")
    op.drop_table("negotiation_versions")
