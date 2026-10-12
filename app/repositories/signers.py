"""Data access for `signers` and the audit certificate tables this task reads/writes
(`audit_certificates`). Owns queries only -- business rules (lock checks, send-for-signature
eligibility, role/ownership checks) live in `app.services.signers`.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.esignature import AuditCertificate, Signer


def get_contract(db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID) -> Contract | None:
    return (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.tenant_id == tenant_id, Contract.deleted_at.is_(None))
        .first()
    )


def list_by_contract(db: Session, contract_id: uuid.UUID) -> list[Signer]:
    return (
        db.query(Signer)
        .filter(Signer.contract_id == contract_id)
        .order_by(Signer.signing_order.asc())
        .all()
    )


def get_by_id(db: Session, contract_id: uuid.UUID, signer_id: uuid.UUID) -> Signer | None:
    return (
        db.query(Signer)
        .filter(Signer.id == signer_id, Signer.contract_id == contract_id)
        .first()
    )


def insert_signer(db: Session, signer: Signer) -> Signer:
    db.add(signer)
    db.flush()
    return signer


def delete_signer(db: Session, signer: Signer) -> None:
    db.delete(signer)
    db.flush()


def get_audit_certificate(db: Session, contract_id: uuid.UUID) -> AuditCertificate | None:
    return (
        db.query(AuditCertificate)
        .filter(AuditCertificate.contract_id == contract_id)
        .order_by(AuditCertificate.generated_at.desc())
        .first()
    )


def insert_audit_certificate(db: Session, certificate: AuditCertificate) -> AuditCertificate:
    db.add(certificate)
    db.flush()
    return certificate
