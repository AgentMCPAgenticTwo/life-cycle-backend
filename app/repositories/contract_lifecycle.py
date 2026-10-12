"""Data access for the life-cycle-uc8-uc9 module's own tables (`contract_assignments`,
`contract_documents`, `contract_versions`, `folder_tags`, `contract_folder_tags`,
`activity_log_entries`, `obligations`, `renewal_alerts`, `contract_lifecycle_actions`,
`obligation_audit_log`), plus the handful of `contracts` reads/writes this module needs.
Owns queries only -- business rules live in `app.services.contract_lifecycle`.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_lifecycle import (
    ActivityLogEntry,
    ContractAssignment,
    ContractDocument,
    ContractFolderTag,
    ContractLifecycleAction,
    ContractVersion,
    FolderTag,
    Obligation,
    ObligationAuditLog,
)


def get_contract(db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID) -> Contract | None:
    return (
        db.query(Contract)
        .filter(
            Contract.id == contract_id,
            Contract.tenant_id == tenant_id,
            Contract.deleted_at.is_(None),
        )
        .first()
    )


def get_assignment(
    db: Session, contract_id: uuid.UUID, user_id: uuid.UUID, role: str
) -> ContractAssignment | None:
    return (
        db.query(ContractAssignment)
        .filter(
            ContractAssignment.contract_id == contract_id,
            ContractAssignment.user_id == user_id,
            ContractAssignment.role == role,
        )
        .first()
    )


def insert_contract(db: Session, contract: Contract) -> Contract:
    db.add(contract)
    db.flush()
    return contract


def get_current_document(db: Session, contract_id: uuid.UUID) -> ContractDocument | None:
    return (
        db.query(ContractDocument)
        .filter(ContractDocument.contract_id == contract_id)
        .order_by(ContractDocument.created_at.desc())
        .first()
    )


def list_versions(
    db: Session, contract_id: uuid.UUID, *, offset: int, limit: int
) -> tuple[list[ContractVersion], int]:
    query = db.query(ContractVersion).filter(ContractVersion.contract_id == contract_id)
    total = query.count()
    rows = query.order_by(ContractVersion.version_number.desc()).offset(offset).limit(limit).all()
    return rows, total


def list_activity_log(
    db: Session, contract_id: uuid.UUID, *, offset: int, limit: int
) -> tuple[list[ActivityLogEntry], int]:
    query = db.query(ActivityLogEntry).filter(ActivityLogEntry.contract_id == contract_id)
    total = query.count()
    rows = query.order_by(ActivityLogEntry.performed_at.desc()).offset(offset).limit(limit).all()
    return rows, total


def insert_activity_log(db: Session, entry: ActivityLogEntry) -> ActivityLogEntry:
    db.add(entry)
    db.flush()
    return entry


def list_folder_tags_for_tenant(db: Session, tenant_id: uuid.UUID) -> list[FolderTag]:
    return (
        db.query(FolderTag)
        .filter(FolderTag.tenant_id == tenant_id)
        .order_by(FolderTag.name.asc())
        .all()
    )


def get_folder_tag(db: Session, tenant_id: uuid.UUID, folder_tag_id: uuid.UUID) -> FolderTag | None:
    return (
        db.query(FolderTag)
        .filter(FolderTag.id == folder_tag_id, FolderTag.tenant_id == tenant_id)
        .first()
    )


def list_contract_folder_tags(db: Session, contract_id: uuid.UUID) -> list[tuple[ContractFolderTag, FolderTag]]:
    return (
        db.query(ContractFolderTag, FolderTag)
        .join(FolderTag, FolderTag.id == ContractFolderTag.folder_tag_id)
        .filter(ContractFolderTag.contract_id == contract_id)
        .all()
    )


def get_contract_folder_tag(
    db: Session, contract_id: uuid.UUID, folder_tag_id: uuid.UUID
) -> ContractFolderTag | None:
    return (
        db.query(ContractFolderTag)
        .filter(
            ContractFolderTag.contract_id == contract_id,
            ContractFolderTag.folder_tag_id == folder_tag_id,
        )
        .first()
    )


def insert_contract_folder_tag(db: Session, row: ContractFolderTag) -> ContractFolderTag:
    db.add(row)
    db.flush()
    return row


def list_obligations(
    db: Session, contract_id: uuid.UUID, *, offset: int, limit: int
) -> tuple[list[Obligation], int]:
    query = db.query(Obligation).filter(Obligation.contract_id == contract_id)
    total = query.count()
    rows = query.order_by(Obligation.created_at.asc()).offset(offset).limit(limit).all()
    return rows, total


def get_obligation(db: Session, contract_id: uuid.UUID, obligation_id: uuid.UUID) -> Obligation | None:
    return (
        db.query(Obligation)
        .filter(Obligation.id == obligation_id, Obligation.contract_id == contract_id)
        .first()
    )


def insert_obligation(db: Session, obligation: Obligation) -> Obligation:
    db.add(obligation)
    db.flush()
    return obligation


def insert_obligation_audit(db: Session, entry: ObligationAuditLog) -> ObligationAuditLog:
    db.add(entry)
    db.flush()
    return entry


def insert_lifecycle_action(db: Session, action: ContractLifecycleAction) -> ContractLifecycleAction:
    db.add(action)
    db.flush()
    return action


def get_latest_lifecycle_action(
    db: Session, original_contract_id: uuid.UUID
) -> ContractLifecycleAction | None:
    return (
        db.query(ContractLifecycleAction)
        .filter(ContractLifecycleAction.original_contract_id == original_contract_id)
        .order_by(ContractLifecycleAction.created_at.desc())
        .first()
    )
