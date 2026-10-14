"""ArchiveApprovalMatrixConfigs

Saving the approval matrix replaces the tenant's configs. A config an approval still
references (`approvals.config_id`) is now archived instead of deleted, so the save no longer
fails on that foreign key.

Revision ID: ArchiveApprovalMatrixConfigs
Revises: UnifyContractStatusFlow
Create Date: 2026-10-14

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "ArchiveApprovalMatrixConfigs"
down_revision: Union[str, None] = "UnifyContractStatusFlow"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("approval_matrix_configs", sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("approval_matrix_configs", "archived_at")
