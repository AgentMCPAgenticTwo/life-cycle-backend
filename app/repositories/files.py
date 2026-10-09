"""Data access for `uploaded_files`. Owns the insert only -- validation lives in
`app.services.files`.
"""
from sqlalchemy.orm import Session

from app.models.uploaded_file import UploadedFile


def insert_uploaded_file(db: Session, uploaded_file: UploadedFile) -> UploadedFile:
    db.add(uploaded_file)
    db.flush()
    return uploaded_file
