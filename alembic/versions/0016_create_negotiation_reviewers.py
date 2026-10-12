"""CreateNegotiationReviewers

Revision ID: CreateNegotiationReviewers
Revises: CreateNegotiationRoutings
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateNegotiationReviewers"
down_revision: Union[str, None] = "CreateNegotiationRoutings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "negotiation_reviewers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "negotiation_routing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("negotiation_routings.id"),
            nullable=False,
        ),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reviewer_name", sa.String(200), nullable=False),
        sa.Column("role", sa.String(50), nullable=True),
        sa.Column("is_mandatory", sa.Boolean(), nullable=False),
        sa.Column("review_status", sa.String(20), nullable=False),
        sa.Column("sequence_order", sa.Integer(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "idx_negotiation_reviewers_routing", "negotiation_reviewers", ["negotiation_routing_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_negotiation_reviewers_routing", table_name="negotiation_reviewers")
    op.drop_table("negotiation_reviewers")
