import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin


class Clause(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "clauses"
    __table_args__ = (Index("idx_clauses_tenant_status", "tenant_id", "status"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    clause_name: Mapped[str] = mapped_column(String(150), nullable=False)
    clause_category: Mapped[str] = mapped_column(String(100), nullable=False)
    standard_text: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_text_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_text_2: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False)


# ClauseVersion deliberately does not use SoftDeleteMixin: version rows are immutable
# snapshots (see context.json), never soft-deleted independently of their parent clause.
class ClauseVersion(Base, TimestampMixin):
    __tablename__ = "clause_versions"
    __table_args__ = (Index("idx_clause_versions_clause", "clause_id", "version_number"),)

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    clause_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("clauses.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    date_changed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    clause_name: Mapped[str] = mapped_column(String(150), nullable=False)
    clause_category: Mapped[str] = mapped_column(String(100), nullable=False)
    standard_text: Mapped[str] = mapped_column(Text, nullable=False)
    fallback_text_1: Mapped[str | None] = mapped_column(Text, nullable=True)
    fallback_text_2: Mapped[str | None] = mapped_column(Text, nullable=True)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)
    mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
