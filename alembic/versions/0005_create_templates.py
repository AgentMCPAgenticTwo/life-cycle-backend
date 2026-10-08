"""CreateTemplates

Revision ID: CreateTemplates
Revises: CreateUploadedFiles
Create Date: 2026-10-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateTemplates"
down_revision: Union[str, None] = "CreateUploadedFiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("template_name", sa.String(150), nullable=False),
        sa.Column("template_category", sa.String(100), nullable=False),
        sa.Column("document_format", sa.String(10), nullable=False),
        sa.Column("template_body", sa.Text(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_by", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_index(
        "idx_templates_tenant_type_industry_status",
        "templates",
        ["tenant_id", "template_category", "status"],
    )


def downgrade() -> None:
    op.drop_index("idx_templates_tenant_type_industry_status", table_name="templates")
    op.drop_table("templates")
