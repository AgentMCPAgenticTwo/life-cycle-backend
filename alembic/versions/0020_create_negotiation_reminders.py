"""CreateNegotiationReminders

Revision ID: CreateNegotiationReminders
Revises: CreateNegotiationExternalLinks
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateNegotiationReminders"
down_revision: Union[str, None] = "CreateNegotiationExternalLinks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "negotiation_reminders",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "negotiation_routing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("negotiation_routings.id"),
            nullable=False,
        ),
        sa.Column("reviewer_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reminder_type", sa.String(10), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "idx_negotiation_reminders_routing_sent",
        "negotiation_reminders",
        ["negotiation_routing_id", "sent_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_negotiation_reminders_routing_sent", table_name="negotiation_reminders")
    op.drop_table("negotiation_reminders")
