import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, ForeignKey, Index, Integer, Numeric, String
from sqlalchemy import false as sa_false
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Contract(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contracts"
    __table_args__ = (
        Index("idx_contracts_tenant_status", "tenant_id", "status"),
        Index("idx_contracts_tenant_enddate", "tenant_id", "end_date"),
        Index("idx_contracts_tenant_owner", "tenant_id", "contract_owner_id"),
        Index("idx_contracts_owner", "owner_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    contract_name: Mapped[str] = mapped_column(String(255), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(50), nullable=False)
    industry: Mapped[str] = mapped_column(String(20), nullable=False)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    template_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("templates.id"), nullable=True
    )
    third_party_paper_file_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("uploaded_files.id"), nullable=True
    )
    counterparty_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("counterparties.id"), nullable=False
    )
    contract_owner_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    contract_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    # Relaxed to nullable by 0031_alter_contracts_for_lifecycle.py for life-cycle-uc8-uc9,
    # which marks both nullable; uc123's own writes still always supply both.
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    renewal_type: Mapped[str] = mapped_column(String(10), nullable=False)
    notice_period: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # --- life-cycle-uc8-uc9 additions -----------------------------------------------
    # Added alongside the uc123 columns above rather than reusing/renaming them -- this
    # table is shared across modules (see 0031_alter_contracts_for_lifecycle.py and
    # T-00-FOUNDATION-API's blockers for the full rationale, including why `notice_period`
    # became `notice_period_text` and why `owner_id`/`counterparty` differ in nullability
    # from the module contract).
    counterparty: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    notice_period_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    document_index_status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    linked_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    linked_relation_type: Mapped[str | None] = mapped_column(String(20), nullable=True)
    renewal_action_in_progress: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=sa_false()
    )


class ContractTask(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contract_tasks"
    __table_args__ = (
        Index("idx_contract_tasks_assignee_current", "assignee_user_id", "is_current"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    assignee_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    assignment_role: Mapped[str] = mapped_column(String(20), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False)
