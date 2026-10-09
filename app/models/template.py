import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.models.mixins import SoftDeleteMixin, TimestampMixin

# TemplateVersion deliberately does not use SoftDeleteMixin: version rows are immutable
# snapshots (see context.json), never soft-deleted independently of their parent template.


class Template(Base, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "templates"
    __table_args__ = (
        Index(
            "idx_templates_tenant_type_industry_status",
            "tenant_id",
            "template_category",
            "status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False
    )
    template_name: Mapped[str] = mapped_column(String(150), nullable=False)
    template_category: Mapped[str] = mapped_column(String(100), nullable=False)
    document_format: Mapped[str] = mapped_column(String(10), nullable=False)
    template_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    current_version: Mapped[int] = mapped_column(Integer, nullable=False)


class TemplateVersion(Base, TimestampMixin):
    __tablename__ = "template_versions"
    __table_args__ = (
        Index("idx_template_versions_template", "template_id", "version_number"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("templates.id"), nullable=False
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)
    changed_by: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    date_changed: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    change_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    template_name: Mapped[str] = mapped_column(String(150), nullable=False)
    template_category: Mapped[str] = mapped_column(String(100), nullable=False)
    document_format: Mapped[str] = mapped_column(String(10), nullable=False)
    template_body: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
