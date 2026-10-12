"""CreateNegotiationComments

Revision ID: CreateNegotiationComments
Revises: CreateNegotiationVersions
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateNegotiationComments"
down_revision: Union[str, None] = "CreateNegotiationVersions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "negotiation_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "negotiation_version_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("negotiation_versions.id"),
            nullable=False,
        ),
        sa.Column("clause_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("comment_text", sa.Text(), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_name", sa.String(200), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "idx_negotiation_comments_version", "negotiation_comments", ["negotiation_version_id"]
    )


def downgrade() -> None:
    op.drop_index("idx_negotiation_comments_version", table_name="negotiation_comments")
    op.drop_table("negotiation_comments")
