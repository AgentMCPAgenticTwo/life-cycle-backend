"""ORM entities for the life-cycle-uc8-uc9 module's own tables.

`Contract` itself is shared infrastructure and lives in `app/models/contract.py` (extended
there, not here) -- see 0031_alter_contracts_for_lifecycle.py. Every table below is new, so
each maps 1:1 onto its context.json definition with no naming or nullability deviations.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin


class ContractAssignment(Base, TimestampMixin):
    __tablename__ = "contract_assignments"
    __table_args__ = (Index("idx_contract_assignments_user", "user_id", "role"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    role: Mapped[str] = mapped_column(String(30), nullable=False)


class ContractDocument(Base, TimestampMixin):
    __tablename__ = "contract_documents"
    __table_args__ = (Index("idx_contract_documents_contract", "contract_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False)
    storage_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    is_corrupted_or_missing: Mapped[bool] = mapped_column(Boolean, nullable=False)


class ContractVersion(Base, TimestampMixin):
    __tablename__ = "contract_versions"
    __table_args__ = (Index("idx_contract_versions_contract", "contract_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)


class FolderTag(Base, TimestampMixin):
    __tablename__ = "folder_tags"
    __table_args__ = (Index("idx_folder_tags_tenant", "tenant_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    kind: Mapped[str] = mapped_column(String(10), nullable=False)


class ContractFolderTag(Base, TimestampMixin):
    __tablename__ = "contract_folder_tags"
    __table_args__ = (
        Index("idx_contract_folder_tags_contract", "contract_id"),
        Index("idx_contract_folder_tags_folder_tag", "folder_tag_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    folder_tag_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("folder_tags.id"), nullable=False
    )


class ActivityLogEntry(Base):
    """Immutable, append-only -- no `updated_at`/`updated_by` (see context.json), so this
    does not use TimestampMixin."""

    __tablename__ = "activity_log_entries"
    __table_args__ = (Index("idx_activity_log_contract", "contract_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    performed_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)


class Obligation(Base, TimestampMixin):
    __tablename__ = "obligations"
    __table_args__ = (
        Index("idx_obligations_contract", "contract_id"),
        Index("idx_obligations_status_due", "status", "due_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    obligation_description: Mapped[str] = mapped_column(Text, nullable=False)
    obligation_type: Mapped[str] = mapped_column(String(30), nullable=False)
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    confirmation_label: Mapped[str] = mapped_column(String(20), nullable=False)
    evidence_reference: Mapped[str | None] = mapped_column(String(500), nullable=True)


class RenewalAlert(Base, TimestampMixin):
    __tablename__ = "renewal_alerts"
    __table_args__ = (Index("idx_renewal_alerts_contract", "contract_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    threshold_days: Mapped[int] = mapped_column(Integer, nullable=False)
    alert_basis: Mapped[str] = mapped_column(String(20), nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ContractLifecycleAction(Base, TimestampMixin):
    __tablename__ = "contract_lifecycle_actions"
    __table_args__ = (Index("idx_lifecycle_actions_original", "original_contract_id"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    original_contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    linked_contract_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    termination_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    effective_termination_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    contract_end_date_snapshot: Mapped[date | None] = mapped_column(Date, nullable=True)
    notice_period_snapshot: Mapped[str | None] = mapped_column(String(100), nullable=True)
    renewal_alert_banner_snapshot: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ObligationAuditLog(Base):
    """Immutable audit log -- no `updated_at`/`updated_by` (see context.json), so this does
    not use TimestampMixin."""

    __tablename__ = "obligation_audit_log"
    __table_args__ = (
        Index("idx_obligation_audit_contract", "contract_id"),
        Index("idx_obligation_audit_obligation", "obligation_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    obligation_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("obligations.id"), nullable=True
    )
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    before_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    performed_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    performed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    created_by: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
