"""CreateTenantNotificationSettings

Revision ID: CreateTenantNotificationSettings
Revises: CreateTenantIntegrations
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateTenantNotificationSettings"
down_revision: Union[str, None] = "CreateTenantIntegrations"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_notification_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("event_name", sa.String(50), nullable=False),
        sa.Column("email_toggle", sa.Boolean(), nullable=False),
        sa.Column("in_app_toggle", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "uq_tenant_event_name", "tenant_notification_settings", ["tenant_id", "event_name"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_tenant_event_name", table_name="tenant_notification_settings")
    op.drop_table("tenant_notification_settings")
