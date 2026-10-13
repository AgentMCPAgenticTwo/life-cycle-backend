"""ORM entities for the lifecycle-uc10-uc11 module's own tables.

`Contract` and `User` are shared infrastructure defined elsewhere (`app/models/contract.py`,
`app/models/user.py`). Every table below is new, so each maps 1:1 onto its context.json
definition with no naming or nullability deviations.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class ContractLifecycleStageHistory(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contract_lifecycle_stage_history"
    __table_args__ = (Index("idx_stage_history_contract", "contract_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    stage_start_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    stage_end_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    contracts_owned_snapshot: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)


class ContractOwner(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contract_owners"
    __table_args__ = (Index("idx_contract_owners_user", "user_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)


class ContractTurnaroundMetrics(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contract_turnaround_metrics"
    __table_args__ = (Index("idx_turnaround_contract", "contract_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    estimated_turnaround_days: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    estimated_turnaround_source: Mapped[str | None] = mapped_column(String(20), nullable=True)
    actual_turnaround_days: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    excluded_from_averages: Mapped[bool] = mapped_column(Boolean, nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)


class TurnaroundOverrideLog(Base, TimestampMixin):
    """No `deleted_at`/`deleted_by` (see context.json) -- not soft-deletable."""

    __tablename__ = "turnaround_override_log"

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    original_ai_value: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    new_value: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    override_user_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    override_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    decision: Mapped[str] = mapped_column(String(20), nullable=False)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)


class TenantBottleneckThreshold(Base, TimestampMixin):
    """No soft delete (see context.json) -- tenant configuration only."""

    __tablename__ = "tenant_bottleneck_thresholds"
    __table_args__ = (Index("idx_threshold_tenant_stage", "tenant_id", "stage"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    stage: Mapped[str] = mapped_column(String(30), nullable=False)
    threshold_days: Mapped[int] = mapped_column(Integer, nullable=False)


class TenantUser(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "tenant_users"
    __table_args__ = (Index("uq_tenant_user_email", "tenant_id", "email", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ApprovalMatrixRule(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "approval_matrix_rules"
    __table_args__ = (
        Index("uq_rule_type_threshold", "tenant_id", "contract_type", "value_threshold", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    contract_type: Mapped[str] = mapped_column(String(50), nullable=False)
    value_threshold: Mapped[float] = mapped_column(Numeric(18, 2), nullable=False)
    approver_role: Mapped[str] = mapped_column(String(50), nullable=False)


class TenantIntegration(Base, TimestampMixin):
    """No soft delete (see context.json) -- tenant configuration only."""

    __tablename__ = "tenant_integrations"
    __table_args__ = (Index("uq_tenant_integration_name", "tenant_id", "integration_name", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    integration_name: Mapped[str] = mapped_column(String(50), nullable=False)
    connection_status: Mapped[str] = mapped_column(String(20), nullable=False)
    credential_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True)
    credential_masked_display: Mapped[str | None] = mapped_column(String(100), nullable=True)
    token_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class TenantNotificationSetting(Base, TimestampMixin):
    """No soft delete (see context.json) -- tenant configuration only."""

    __tablename__ = "tenant_notification_settings"
    __table_args__ = (Index("uq_tenant_event_name", "tenant_id", "event_name", unique=True),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    event_name: Mapped[str] = mapped_column(String(50), nullable=False)
    email_toggle: Mapped[bool] = mapped_column(Boolean, nullable=False)
    in_app_toggle: Mapped[bool] = mapped_column(Boolean, nullable=False)


class TenantAuditLog(Base, TimestampMixin):
    """No soft delete (see context.json) -- append-only audit trail."""

    __tablename__ = "tenant_audit_log"
    __table_args__ = (Index("idx_audit_log_date", "tenant_id", "log_date_time"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    log_date_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    log_user: Mapped[str] = mapped_column(String(255), nullable=False)
    log_action: Mapped[str] = mapped_column(String(100), nullable=False)
    log_entity: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
