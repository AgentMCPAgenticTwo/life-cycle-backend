import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin


class Signer(Base, TimestampMixin):
    __tablename__ = "signers"
    __table_args__ = (
        Index("idx_signers_contract_order", "contract_id", "signing_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    signer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    signer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    signer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    signing_order: Mapped[int] = mapped_column(Integer, nullable=False)
    signature_method: Mapped[str] = mapped_column(String(40), nullable=False)
    reminder_frequency_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    signer_status: Mapped[str] = mapped_column(String(20), nullable=False)
    otp_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    otp_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    otp_locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    otp_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    signature_pad_data: Mapped[str | None] = mapped_column(Text, nullable=True)
    signed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decline_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    link_token: Mapped[str | None] = mapped_column(String(255), nullable=True)
    link_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reminder_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SignatureAuditLog(Base, TimestampMixin):
    __tablename__ = "signature_audit_log"
    __table_args__ = (
        Index("idx_signature_audit_log_signer", "signer_id"),
        Index("idx_signature_audit_log_contract", "contract_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    signer_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("signers.id"), nullable=False
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)
    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditCertificate(Base, TimestampMixin):
    __tablename__ = "audit_certificates"
    __table_args__ = (
        Index("idx_audit_certificates_contract", "contract_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    file_url: Mapped[str] = mapped_column(String(500), nullable=False)
    data_snapshot: Mapped[Any] = mapped_column(JSONB, nullable=False)


class EsignatureSettings(Base, TimestampMixin):
    __tablename__ = "esignature_settings"
    __table_args__ = (
        Index("idx_esignature_settings_tenant", "tenant_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    reminder_frequency_days: Mapped[int] = mapped_column(Integer, nullable=False)
    default_signature_provider: Mapped[str] = mapped_column(String(40), nullable=False)
