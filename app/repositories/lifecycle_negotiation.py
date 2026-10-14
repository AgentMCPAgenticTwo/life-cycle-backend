"""Data access for `negotiation_routings`, `negotiation_reviewers`, `negotiation_versions`,
`negotiation_comments`, `negotiation_external_links` and `negotiation_reminders`. Owns
queries only -- the routing/versioning/status-transition rules live in
`app.services.lifecycle_negotiation`.
"""
import uuid
from datetime import date, datetime

from sqlalchemy.orm import Session

from app.models.lifecycle_negotiation import (
    NegotiationComment,
    NegotiationExternalLink,
    NegotiationReminder,
    NegotiationReviewer,
    NegotiationRouting,
    NegotiationVersion,
)


def get_routing_by_contract(db: Session, contract_id: uuid.UUID) -> NegotiationRouting | None:
    return db.query(NegotiationRouting).filter(NegotiationRouting.contract_id == contract_id).first()


def get_routing_by_id(db: Session, routing_id: uuid.UUID) -> NegotiationRouting | None:
    return db.query(NegotiationRouting).filter(NegotiationRouting.id == routing_id).first()


def insert_routing(db: Session, routing: NegotiationRouting) -> NegotiationRouting:
    db.add(routing)
    db.flush()
    return routing


def list_reviewers(db: Session, routing_id: uuid.UUID) -> list[NegotiationReviewer]:
    return (
        db.query(NegotiationReviewer)
        .filter(NegotiationReviewer.negotiation_routing_id == routing_id)
        .order_by(NegotiationReviewer.sequence_order.asc().nulls_last())
        .all()
    )


def get_reviewer(
    db: Session, routing_id: uuid.UUID, reviewer_id: uuid.UUID
) -> NegotiationReviewer | None:
    return (
        db.query(NegotiationReviewer)
        .filter(
            NegotiationReviewer.negotiation_routing_id == routing_id,
            NegotiationReviewer.reviewer_id == reviewer_id,
        )
        .first()
    )


def insert_reviewer(db: Session, reviewer: NegotiationReviewer) -> NegotiationReviewer:
    db.add(reviewer)
    db.flush()
    return reviewer


def list_versions(db: Session, contract_id: uuid.UUID) -> list[NegotiationVersion]:
    return (
        db.query(NegotiationVersion)
        .filter(NegotiationVersion.contract_id == contract_id)
        .order_by(NegotiationVersion.version_number.asc())
        .all()
    )


def get_version(
    db: Session, contract_id: uuid.UUID, version_number: int
) -> NegotiationVersion | None:
    return (
        db.query(NegotiationVersion)
        .filter(
            NegotiationVersion.contract_id == contract_id,
            NegotiationVersion.version_number == version_number,
        )
        .first()
    )


def insert_version(db: Session, version: NegotiationVersion) -> NegotiationVersion:
    db.add(version)
    db.flush()
    return version


def list_comments_for_versions(
    db: Session, version_ids: list[uuid.UUID]
) -> list[NegotiationComment]:
    if not version_ids:
        return []
    return (
        db.query(NegotiationComment)
        .filter(NegotiationComment.negotiation_version_id.in_(version_ids))
        .order_by(NegotiationComment.created_at.asc())
        .all()
    )


def insert_comment(db: Session, comment: NegotiationComment) -> NegotiationComment:
    db.add(comment)
    db.flush()
    return comment


def get_external_link_by_token(db: Session, link_token: str) -> NegotiationExternalLink | None:
    return (
        db.query(NegotiationExternalLink)
        .filter(NegotiationExternalLink.link_token == link_token)
        .first()
    )


def insert_external_link(db: Session, link: NegotiationExternalLink) -> NegotiationExternalLink:
    db.add(link)
    db.flush()
    return link


def insert_reminder(db: Session, reminder: NegotiationReminder) -> NegotiationReminder:
    db.add(reminder)
    db.flush()
    return reminder


def list_overdue_routings(db: Session, today: date) -> list[NegotiationRouting]:
    """Routings whose Due Date has passed and that are still open. 'Agreed' is excluded here
    rather than in the service so the automatic-reminder sweep never loads a closed
    negotiation at all (UC5: reminders stop when the contract is marked Agreed)."""
    return (
        db.query(NegotiationRouting)
        .filter(
            NegotiationRouting.due_date < today,
            NegotiationRouting.negotiation_status != "Agreed",
        )
        .all()
    )


def list_reminders_since(
    db: Session, routing_id: uuid.UUID, since: datetime
) -> list[NegotiationReminder]:
    return (
        db.query(NegotiationReminder)
        .filter(
            NegotiationReminder.negotiation_routing_id == routing_id,
            NegotiationReminder.sent_at >= since,
        )
        .all()
    )
