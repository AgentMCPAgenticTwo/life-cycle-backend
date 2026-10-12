"""Data access for the `signing-sessions` endpoints. These endpoints read/write the `signers`
table (owned write-side by the sibling T-CONTRACTS-API/T-SIGNERS-API task) and read `contracts`
-- no new table belongs to this task. Queries are kept separate from that sibling task's
`app.repositories.signers` module (per CLAUDE.md's "Adding a module without breaking the last
one") and add only the lookups this task needs: by signer id alone, and by contract id alone
with no tenant scoping, since a Signer's session id is itself the only credential the SIGNER
role carries here -- see `app.services.signing_sessions` for why no tenant-scoped lookup is
used.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.esignature import Signer


def get_signer_by_id(db: Session, signer_id: uuid.UUID) -> Signer | None:
    return db.query(Signer).filter(Signer.id == signer_id).first()


def list_by_contract(db: Session, contract_id: uuid.UUID) -> list[Signer]:
    return (
        db.query(Signer)
        .filter(Signer.contract_id == contract_id)
        .order_by(Signer.signing_order.asc())
        .all()
    )


def get_contract_by_id(db: Session, contract_id: uuid.UUID) -> Contract | None:
    return (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.deleted_at.is_(None))
        .first()
    )
