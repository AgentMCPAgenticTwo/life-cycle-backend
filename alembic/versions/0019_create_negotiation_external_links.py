"""CreateNegotiationExternalLinks

Revision ID: CreateNegotiationExternalLinks
Revises: CreateNegotiationComments
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateNegotiationExternalLinks"
down_revision: Union[str, None] = "CreateNegotiationComments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "negotiation_external_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "negotiation_routing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("negotiation_routings.id"),
            nullable=False,
        ),
        sa.Column("link_token", sa.String(100), nullable=False),
        sa.Column("otp_hash", sa.String(255), nullable=False),
        sa.Column("failed_attempts", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "uq_negotiation_external_links_token",
        "negotiation_external_links",
        ["link_token"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("uq_negotiation_external_links_token", table_name="negotiation_external_links")
    op.drop_table("negotiation_external_links")
