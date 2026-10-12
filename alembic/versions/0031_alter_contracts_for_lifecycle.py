"""CreateContractsLifecycleColumns

Revision ID: CreateContractsLifecycleColumns
Revises: CreateEsignatureSettings
Create Date: 2026-10-12

The life-cycle-uc8-uc9 module contract calls for a `contracts` table migration named
exactly `CreateContracts` -- but that name (and the table itself) already exists as of
0009_create_contracts.py, created for the uc123 module and depended on by every module
since (negotiation, approvals, signers). Per CLAUDE.md's "Adding a module without breaking
the last one" and this module's own skill ("If a change here would affect another module's
existing files, stop and extend shared code instead of rewriting it"), this migration
ADDS the uc8/uc9 columns to the existing table instead of re-creating it. See
T-00-FOUNDATION-API's blockers for the full list of naming/nullability deviations this
required.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "CreateContractsLifecycleColumns"
down_revision: Union[str, None] = "CreateEsignatureSettings"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # uc123 required these NOT NULL; the uc8/uc9 contract marks them nullable. Relaxing (not
    # tightening) a constraint is backward compatible -- uc123's own inserts always supply
    # both, so nothing about its behavior changes.
    op.alter_column("contracts", "start_date", nullable=True)
    op.alter_column("contracts", "end_date", nullable=True)
    op.add_column("contracts", sa.Column("counterparty", sa.String(255), nullable=False, server_default=""))
    op.add_column("contracts", sa.Column("value", sa.Numeric(18, 2), nullable=True))
    op.add_column("contracts", sa.Column("notice_period_text", sa.String(100), nullable=True))
    op.add_column(
        "contracts",
        sa.Column("owner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column("contracts", sa.Column("document_index_status", sa.String(20), nullable=True))
    op.add_column(
        "contracts",
        sa.Column(
            "linked_contract_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=True
        ),
    )
    op.add_column("contracts", sa.Column("linked_relation_type", sa.String(20), nullable=True))
    op.add_column(
        "contracts",
        sa.Column("renewal_action_in_progress", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index("idx_contracts_owner", "contracts", ["owner_id"])


def downgrade() -> None:
    op.drop_index("idx_contracts_owner", table_name="contracts")
    op.drop_column("contracts", "renewal_action_in_progress")
    op.drop_column("contracts", "linked_relation_type")
    op.drop_column("contracts", "linked_contract_id")
    op.drop_column("contracts", "document_index_status")
    op.drop_column("contracts", "owner_id")
    op.drop_column("contracts", "notice_period_text")
    op.drop_column("contracts", "value")
    op.drop_column("contracts", "counterparty")
    op.alter_column("contracts", "end_date", nullable=False)
    op.alter_column("contracts", "start_date", nullable=False)
