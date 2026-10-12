import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import TimestampMixin


class NegotiationRouting(Base, TimestampMixin):
    __tablename__ = "negotiation_routings"
    __table_args__ = (
        Index("uq_negotiation_routings_contract", "contract_id", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    routing_type: Mapped[str] = mapped_column(String(20), nullable=False)
    external_party_name: Mapped[str] = mapped_column(String(200), nullable=False)
    external_party_email: Mapped[str] = mapped_column(String(200), nullable=False)
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    negotiation_status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_version_number: Mapped[int] = mapped_column(Integer, nullable=False)


class NegotiationReviewer(Base, TimestampMixin):
    __tablename__ = "negotiation_reviewers"
    __table_args__ = (
        Index("idx_negotiation_reviewers_routing", "negotiation_routing_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    negotiation_routing_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("negotiation_routings.id"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(200), nullable=False)
    role: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    review_status: Mapped[str] = mapped_column(String(20), nullable=False)
    sequence_order: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class NegotiationVersion(Base, TimestampMixin):
    __tablename__ = "negotiation_versions"
    __table_args__ = (
        Index("uq_negotiation_versions_contract_version", "contract_id", "version_number", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("contracts.id"), nullable=False
    )
    negotiation_routing_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("negotiation_routings.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    source: Mapped[str] = mapped_column(String(10), nullable=False)
    document_snapshot: Mapped[Any | None] = mapped_column(JSONB, nullable=True)


class NegotiationComment(Base, TimestampMixin):
    __tablename__ = "negotiation_comments"
    __table_args__ = (
        Index("idx_negotiation_comments_version", "negotiation_version_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    negotiation_version_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("negotiation_versions.id"), nullable=False
    )
    clause_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    comment_text: Mapped[str] = mapped_column(Text, nullable=False)
    author_id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), nullable=False)
    author_name: Mapped[str] = mapped_column(String(200), nullable=False)


class NegotiationExternalLink(Base, TimestampMixin):
    __tablename__ = "negotiation_external_links"
    __table_args__ = (
        Index("uq_negotiation_external_links_token", "link_token", unique=True),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    negotiation_routing_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("negotiation_routings.id"), nullable=False
    )
    link_token: Mapped[str] = mapped_column(String(100), nullable=False)
    otp_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class NegotiationReminder(Base, TimestampMixin):
    __tablename__ = "negotiation_reminders"
    __table_args__ = (
        Index("idx_negotiation_reminders_routing_sent", "negotiation_routing_id", "sent_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    negotiation_routing_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("negotiation_routings.id"), nullable=False
    )
    reviewer_id: Mapped[uuid.UUID | None] = mapped_column(PGUUID(as_uuid=True), nullable=True)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reminder_type: Mapped[str] = mapped_column(String(10), nullable=False)
