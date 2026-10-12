"""CreateEsignatureSettings

Revision ID: CreateEsignatureSettings
Revises: CreateAuditCertificates
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateEsignatureSettings"
down_revision: Union[str, None] = "CreateAuditCertificates"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "esignature_settings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reminder_frequency_days", sa.Integer(), nullable=False),
        sa.Column("default_signature_provider", sa.String(40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_esignature_settings_tenant", "esignature_settings", ["tenant_id"])


def downgrade() -> None:
    op.drop_index("idx_esignature_settings_tenant", table_name="esignature_settings")
    op.drop_table("esignature_settings")
