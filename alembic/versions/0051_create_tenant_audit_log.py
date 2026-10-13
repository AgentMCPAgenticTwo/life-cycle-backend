"""CreateTenantAuditLog

Revision ID: CreateTenantAuditLog
Revises: CreateTenantNotificationSettings
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateTenantAuditLog"
down_revision: Union[str, None] = "CreateTenantNotificationSettings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_audit_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("log_date_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("log_user", sa.String(255), nullable=False),
        sa.Column("log_action", sa.String(100), nullable=False),
        sa.Column("log_entity", sa.String(100), nullable=False),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_audit_log_date", "tenant_audit_log", ["tenant_id", "log_date_time"])


def downgrade() -> None:
    op.drop_index("idx_audit_log_date", table_name="tenant_audit_log")
    op.drop_table("tenant_audit_log")
