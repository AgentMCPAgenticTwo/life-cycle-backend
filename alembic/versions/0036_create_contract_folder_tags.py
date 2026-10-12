"""CreateContractFolderTags

Revision ID: CreateContractFolderTags
Revises: CreateFolderTags
Create Date: 2026-10-12

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateContractFolderTags"
down_revision: Union[str, None] = "CreateFolderTags"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "contract_folder_tags",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column(
            "folder_tag_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("folder_tags.id"), nullable=False
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_by", postgresql.UUID(as_uuid=True), nullable=False),
    )
    op.create_index("idx_contract_folder_tags_contract", "contract_folder_tags", ["contract_id"])
    op.create_index("idx_contract_folder_tags_folder_tag", "contract_folder_tags", ["folder_tag_id"])


def downgrade() -> None:
    op.drop_index("idx_contract_folder_tags_folder_tag", table_name="contract_folder_tags")
    op.drop_index("idx_contract_folder_tags_contract", table_name="contract_folder_tags")
    op.drop_table("contract_folder_tags")
