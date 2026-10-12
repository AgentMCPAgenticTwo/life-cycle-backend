import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class ContractClause(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "contract_clauses"
    __table_args__ = (
        Index("idx_contract_clauses_contract", "contract_id"),
        Index("idx_contract_clauses_contract_status", "contract_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    clause_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    library_match_status: Mapped[str] = mapped_column(String(20), nullable=False)
    risk_score: Mapped[str] = mapped_column(String(10), nullable=False)
    ai_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    mandatory_flag_cleared: Mapped[bool] = mapped_column(Boolean, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)


class ContractMetadata(Base, TimestampMixin):
    __tablename__ = "contract_metadata"
    __table_args__ = (
        Index("uq_contract_metadata_contract", "contract_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    parties: Mapped[str | None] = mapped_column(Text, nullable=True)
    parties_label: Mapped[str] = mapped_column(String(20), nullable=False)
    contract_value: Mapped[Decimal | None] = mapped_column(Numeric(18, 2), nullable=True)
    contract_value_label: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[Any | None] = mapped_column(Date, nullable=True)
    start_date_label: Mapped[str] = mapped_column(String(20), nullable=False)
    end_date: Mapped[Any | None] = mapped_column(Date, nullable=True)
    end_date_label: Mapped[str] = mapped_column(String(20), nullable=False)
    renewal_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    renewal_terms_label: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_terms: Mapped[str | None] = mapped_column(Text, nullable=True)
    payment_terms_label: Mapped[str] = mapped_column(String(20), nullable=False)
    key_obligations: Mapped[str | None] = mapped_column(Text, nullable=True)
    key_obligations_label: Mapped[str] = mapped_column(String(20), nullable=False)


class ClauseAuditLog(Base, TimestampMixin):
    __tablename__ = "clause_audit_log"
    __table_args__ = (
        Index("idx_clause_audit_log_contract_occurred", "contract_id", "occurred_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    clause_id: Mapped[uuid.UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contract_clauses.id"), nullable=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    field_name: Mapped[str | None] = mapped_column(String(50), nullable=True)
    before_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AskAiInteraction(Base, TimestampMixin):
    __tablename__ = "ask_ai_interactions"
    __table_args__ = (
        Index("idx_ask_ai_interactions_contract", "contract_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    disclaimer: Mapped[str | None] = mapped_column(Text, nullable=True)
    related_clause_ids: Mapped[Any | None] = mapped_column(JSONB, nullable=True)
