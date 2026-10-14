import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin


class ApprovalMatrixConfig(Base, TimestampMixin):
    __tablename__ = "approval_matrix_configs"
    __table_args__ = (
        Index("idx_approval_matrix_configs_tenant_type", "tenant_id", "contract_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(100), nullable=False)
    value_min: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    value_max: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    risk_band_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_band_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # Set when a matrix save replaces a config that approvals still reference: it drops out of
    # the matrix and of rule matching but stays readable for those approvals' steps.
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalMatrixStep(Base, TimestampMixin):
    __tablename__ = "approval_matrix_steps"
    __table_args__ = (
        Index("idx_approval_matrix_steps_config_step", "config_id", "step_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    config_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("approval_matrix_configs.id"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    step_name: Mapped[str] = mapped_column(String(200), nullable=False)
    approver_role: Mapped[str | None] = mapped_column(String(100), nullable=True)
    approver_user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)


class Approval(Base, TimestampMixin):
    __tablename__ = "approvals"
    __table_args__ = (
        Index("idx_approvals_contract", "contract_id"),
        Index("idx_approvals_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    contract_owner_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    config_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("approval_matrix_configs.id"), nullable=True
    )
    current_step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    total_steps: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    ai_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    key_terms_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    deviations_from_standard: Mapped[str | None] = mapped_column(Text, nullable=True)


class ApprovalStepInstance(Base, TimestampMixin):
    __tablename__ = "approval_step_instances"
    __table_args__ = (
        Index("idx_approval_step_instances_approval_step", "approval_id", "step_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("approvals.id"), nullable=False
    )
    step_number: Mapped[int] = mapped_column(Integer, nullable=False)
    approver_user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    acted_by: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    acted_as_delegate_for: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    acted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalDelegation(Base, TimestampMixin):
    __tablename__ = "approval_delegations"
    __table_args__ = (
        Index("idx_approval_delegations_approval", "approval_id"),
        Index("idx_approval_delegations_delegate", "delegate_to_user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("approvals.id"), nullable=False
    )
    approver_user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    delegate_to_user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)


class ApprovalAuditLog(Base, TimestampMixin):
    __tablename__ = "approval_audit_log"
    __table_args__ = (
        Index("idx_approval_audit_log_approval", "approval_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    approval_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("approvals.id"), nullable=False
    )
    contract_title: Mapped[str] = mapped_column(String(500), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(100), nullable=False)
    contract_value: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
    counterparty_name: Mapped[str] = mapped_column(String(300), nullable=False)
    key_terms_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    deviations_from_standard: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    approval_matrix_step_label: Mapped[str] = mapped_column(String(200), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(50), nullable=False)
    acting_as_delegate_for: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    delegate_to_user_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    delegate_to_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    prior_state: Mapped[str] = mapped_column(String(30), nullable=False)
    new_state: Mapped[str] = mapped_column(String(30), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text, nullable=True)
    retention_expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    archived: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
