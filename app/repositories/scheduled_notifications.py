"""Data access for the time-driven notification sweeps in
`app.services.scheduled_notifications` (UC5 reviewer reminders, UC7 signature reminders,
UC9 renewal alerts).

These queries are deliberately tenant-wide: a sweep has no request and therefore no caller
tenant, so it walks every tenant's rows and the service tenant-scopes each notification from
the row it found. Owns queries only -- the cadence and once-only rules live in the service.
"""
import uuid

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_lifecycle import RenewalAlert
from app.models.esignature import Signer
from app.models.user import User

# A signer still waiting on us; anything else (Signed, Declined, Expired) is terminal for
# reminder purposes.
OPEN_SIGNER_STATUSES = ("Sent", "Viewed")


def get_contract_by_id(db: Session, contract_id: uuid.UUID) -> Contract | None:
    return (
        db.query(Contract)
        .filter(Contract.id == contract_id, Contract.deleted_at.is_(None))
        .first()
    )


def list_open_signers(db: Session) -> list[Signer]:
    return (
        db.query(Signer)
        .filter(Signer.signer_status.in_(OPEN_SIGNER_STATUSES))
        .order_by(Signer.contract_id, Signer.signing_order)
        .all()
    )


def list_renewal_candidates(db: Session, statuses: tuple[str, ...]) -> list[Contract]:
    return (
        db.query(Contract)
        .filter(
            Contract.deleted_at.is_(None),
            Contract.end_date.isnot(None),
            Contract.status.in_(statuses),
        )
        .all()
    )


def get_renewal_alert(
    db: Session, contract_id: uuid.UUID, threshold_days: int, alert_basis: str
) -> RenewalAlert | None:
    return (
        db.query(RenewalAlert)
        .filter(
            RenewalAlert.contract_id == contract_id,
            RenewalAlert.threshold_days == threshold_days,
            RenewalAlert.alert_basis == alert_basis,
        )
        .first()
    )


def insert_renewal_alert(db: Session, alert: RenewalAlert) -> RenewalAlert:
    db.add(alert)
    db.flush()
    return alert


def list_role_emails(db: Session, tenant_id: uuid.UUID, role: str) -> list[str]:
    rows = (
        db.query(User.email)
        .filter(
            User.tenant_id == tenant_id,
            User.role == role,
            User.is_active.is_(True),
            User.deleted_at.is_(None),
        )
        .all()
    )
    return [row[0] for row in rows]


def get_user_email(db: Session, user_id: uuid.UUID | None) -> str | None:
    if user_id is None:
        return None
    row = db.query(User).filter(User.id == user_id, User.deleted_at.is_(None)).first()
    return row.email if row is not None else None
