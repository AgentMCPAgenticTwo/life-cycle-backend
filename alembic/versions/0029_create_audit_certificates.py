"""CreateAuditCertificates

Revision ID: CreateAuditCertificates
Revises: CreateSignatureAuditLog
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateAuditCertificates"
down_revision: Union[str, None] = "CreateSignatureAuditLog"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_certificates",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("file_url", sa.String(500), nullable=False),
        sa.Column("data_snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_audit_certificates_contract", "audit_certificates", ["contract_id"])


def downgrade() -> None:
    op.drop_index("idx_audit_certificates_contract", table_name="audit_certificates")
    op.drop_table("audit_certificates")
