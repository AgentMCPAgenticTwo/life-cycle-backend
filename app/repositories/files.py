"""Data access for `uploaded_files`. Owns the insert and the by-id lookup -- validation
lives in `app.services.files` / `app.services.tracker_export`.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.uploaded_file import UploadedFile


def insert_uploaded_file(db: Session, uploaded_file: UploadedFile) -> UploadedFile:
    db.add(uploaded_file)
    db.flush()
    return uploaded_file


def get_uploaded_file(db: Session, tenant_id: uuid.UUID, file_id: uuid.UUID) -> UploadedFile | None:
    stmt = select(UploadedFile).where(
        UploadedFile.id == file_id,
        UploadedFile.tenant_id == tenant_id,
        UploadedFile.deleted_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()
