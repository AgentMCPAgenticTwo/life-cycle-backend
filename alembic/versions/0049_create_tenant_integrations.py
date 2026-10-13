"""CreateTenantIntegrations

Revision ID: CreateTenantIntegrations
Revises: CreateApprovalMatrixRules
Create Date: 2026-10-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateTenantIntegrations"
down_revision: Union[str, None] = "CreateApprovalMatrixRules"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenant_integrations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("integration_name", sa.String(50), nullable=False),
        sa.Column("connection_status", sa.String(20), nullable=False),
        sa.Column("credential_ciphertext", sa.Text(), nullable=True),
        sa.Column("credential_masked_display", sa.String(100), nullable=True),
        sa.Column("token_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index(
        "uq_tenant_integration_name", "tenant_integrations", ["tenant_id", "integration_name"], unique=True
    )


def downgrade() -> None:
    op.drop_index("uq_tenant_integration_name", table_name="tenant_integrations")
    op.drop_table("tenant_integrations")
