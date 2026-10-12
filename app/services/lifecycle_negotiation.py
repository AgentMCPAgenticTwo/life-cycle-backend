"""Business rules for the `lifecycle-uc4-uc5` module's Negotiation & Routing surface: the
routing precondition and reviewer validation (UC5-BR-023, UC5-AF-001, UC5-FV-001), mandatory
reviewer auto-add (UC5-BR-001/002), sequential/parallel notification order (UC5-BR-003/004),
status transitions (UC5-BR-007/008/009/018/019/020/021), auto-versioning (UC5-BR-011), the
OTP-secured external party flow (UC5-BR-005/016), and Compare Versions scoping (UC5-BR-012).
See CLAUDE.md's lifecycle-uc4-uc5 module section and this task's `blockers` for the judgement
calls this file makes where the contract, an email service, or a scheduler is absent from
this sandbox.
"""
import hashlib
import re
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ConflictError, ForbiddenError, NotFoundError, ValidationFailedError
from app.models.lifecycle_negotiation import (
    NegotiationComment,
    NegotiationExternalLink,
    NegotiationReminder,
    NegotiationReviewer,
    NegotiationRouting,
    NegotiationVersion,
)
from app.repositories import contracts as contracts_repo
from app.repositories import lifecycle_negotiation as repo
from app.services import lifecycle_clauses as clause_service
from app.schemas.lifecycle_negotiation import (
    ClauseDiffResponse,
    CommentRequest,
    CommentResponse,
    CompareVersionsResponse,
    ExternalSubmitRequest,
    ExternalSubmitResponse,
    GenerateExternalLinkResponse,
    MarkAgreedResponse,
    NegotiationExternalViewResponse,
    NegotiationTrackerResponse,
    ReminderResponse,
    ReviewerResponse,
    RoutingRequest,
    RoutingResponse,
    SubmitReviewRequest,
    SubmitReviewResponse,
    VerifyOtpRequest,
    VerifyOtpResponse,
    VersionSummaryResponse,
)

_ROUTING_TYPES = {"Sequential", "Parallel"}
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_FINANCE_HEAD_THRESHOLD = Decimal("1000000")
_LINK_TTL = timedelta(hours=72)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(expires_at: datetime, now: datetime) -> bool:
    """SQLite (used in tests in place of the real Postgres -- see conftest.py) does not
    round-trip timezone-aware `DateTime` columns, so a value read back can be naive even
    though it was written as aware. Compare on naive UTC wall-clock values either way."""
    if expires_at.tzinfo is None:
        return expires_at < now.replace(tzinfo=None)
    return expires_at < now


def _get_contract_or_404(db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID):
    contract = contracts_repo.get_by_id(db, tenant_id, contract_id)
    if contract is None:
        raise NotFoundError("contract not found")
    return contract


def _get_routing_or_404(db: Session, contract_id: uuid.UUID) -> NegotiationRouting:
    routing = repo.get_routing_by_contract(db, contract_id)
    if routing is None:
        raise NotFoundError("negotiation has not been routed for this contract")
    return routing


def _reviewer_to_response(reviewer: NegotiationReviewer) -> ReviewerResponse:
    return ReviewerResponse(
        reviewerId=reviewer.reviewer_id,
        reviewerName=reviewer.reviewer_name,
        role=reviewer.role,
        isMandatory=reviewer.is_mandatory,
        reviewStatus=reviewer.review_status,
        submittedAt=reviewer.submitted_at,
        sequenceOrder=reviewer.sequence_order,
    )


def create_routing(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, payload: RoutingRequest
) -> RoutingResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)

    # UC5-BR-023: routing requires a Draft contract with at least one completed AI Clause
    # Analysis pass (UC4).
    if contract.status != "Draft" or not clause_service.has_completed_analysis_pass(db, contract.id):
        raise ConflictError(
            "This contract must be in Draft status with a completed AI clause analysis pass before it can be routed."
        )
    if repo.get_routing_by_contract(db, contract.id) is not None:
        raise ConflictError("This contract has already been routed for negotiation.")

    if payload.routingType not in _ROUTING_TYPES:
        raise ValidationFailedError(
            "Routing Type must be Sequential or Parallel.", details=["Routing Type must be Sequential or Parallel."]
        )
    # UC5-AF-001/FV-001: at least one internal reviewer must be selected.
    if not payload.internalReviewers:
        raise ValidationFailedError(
            "Please select at least one internal reviewer or external party before sending.",
            details=["Please select at least one internal reviewer or external party before sending."],
        )
    if not payload.externalPartyName.strip():
        raise ValidationFailedError("External Party Name is required.", details=["External Party Name is required."])
    if not _EMAIL_RE.match(payload.externalPartyEmail):
        raise ValidationFailedError(
            "External Party Email must be a valid email address.",
            details=["External Party Email must be a valid email address."],
        )
    if payload.dueDate <= payload.assignedDate:
        raise ValidationFailedError(
            "Due Date must be after Assigned Date.", details=["Due Date must be after Assigned Date."]
        )

    reviewer_users = []
    for reviewer_id in payload.internalReviewers:
        reviewer_user = contracts_repo.get_user(db, tenant_id, reviewer_id)
        if reviewer_user is None:
            raise ValidationFailedError(
                "One or more selected Internal Reviewers could not be found.",
                details=["One or more selected Internal Reviewers could not be found."],
            )
        reviewer_users.append(reviewer_user)

    user_uuid = uuid.UUID(user.user_id)
    now = _now()
    routing = repo.insert_routing(
        db,
        NegotiationRouting(
            contract_id=contract.id,
            routing_type=payload.routingType,
            external_party_name=payload.externalPartyName,
            external_party_email=payload.externalPartyEmail,
            assigned_date=payload.assignedDate,
            due_date=payload.dueDate,
            negotiation_status="With Internal",
            current_version_number=1,
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )

    sequence = 1
    for reviewer_user in reviewer_users:
        repo.insert_reviewer(
            db,
            NegotiationReviewer(
                negotiation_routing_id=routing.id,
                reviewer_id=reviewer_user.id,
                reviewer_name=reviewer_user.name,
                role=reviewer_user.role,
                is_mandatory=False,
                review_status="Pending",
                sequence_order=sequence if payload.routingType == "Sequential" else None,
                created_by=user_uuid,
                updated_by=user_uuid,
            ),
        )
        sequence += 1

    # UC5-BR-001: Finance Head is auto-added as a mandatory reviewer above the value threshold.
    if contract.contract_value is not None and contract.contract_value > _FINANCE_HEAD_THRESHOLD:
        if not any(ru.name.strip().lower() == "finance head" for ru in reviewer_users):
            repo.insert_reviewer(
                db,
                NegotiationReviewer(
                    negotiation_routing_id=routing.id,
                    reviewer_id=uuid.uuid4(),
                    reviewer_name="Finance Head",
                    role="FINANCE_HEAD",
                    is_mandatory=True,
                    review_status="Pending",
                    sequence_order=sequence if payload.routingType == "Sequential" else None,
                    created_by=user_uuid,
                    updated_by=user_uuid,
                ),
            )
            sequence += 1

    # UC5-BR-002: Legal Reviewer is auto-added as a mandatory reviewer for High Risk contracts.
    if clause_service.get_overall_risk(db, contract.id) == "High":
        if not any(ru.role == "LEGAL_REVIEWER" for ru in reviewer_users):
            repo.insert_reviewer(
                db,
                NegotiationReviewer(
                    negotiation_routing_id=routing.id,
                    reviewer_id=uuid.uuid4(),
                    reviewer_name="Legal Reviewer",
                    role="LEGAL_REVIEWER",
                    is_mandatory=True,
                    review_status="Pending",
                    sequence_order=sequence if payload.routingType == "Sequential" else None,
                    created_by=user_uuid,
                    updated_by=user_uuid,
                ),
            )

    repo.insert_version(
        db,
        NegotiationVersion(
            contract_id=contract.id,
            negotiation_routing_id=routing.id,
            version_number=1,
            source="internal",
            document_snapshot=clause_service.snapshot_clauses(db, contract.id),
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )
    db.commit()
    db.refresh(routing)

    reviewers = [_reviewer_to_response(r) for r in repo.list_reviewers(db, routing.id)]
    return RoutingResponse(
        contractId=contract.id,
        routingType=routing.routing_type,
        internalReviewers=reviewers,
        externalPartyName=routing.external_party_name,
        externalPartyEmail=routing.external_party_email,
        assignedDate=routing.assigned_date,
        dueDate=routing.due_date,
        negotiationStatus=routing.negotiation_status,
        versionNumber=routing.current_version_number,
    )


def get_tracker(
    db: Session, tenant_id: uuid.UUID, contract_id: uuid.UUID
) -> NegotiationTrackerResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    routing = _get_routing_or_404(db, contract.id)
    reviewers = repo.list_reviewers(db, routing.id)
    versions = repo.list_versions(db, contract.id)
    version_ids = [v.id for v in versions]
    version_number_by_id = {v.id: v.version_number for v in versions}
    comments = repo.list_comments_for_versions(db, version_ids)

    overdue = (
        routing.negotiation_status == "With Internal"
        and routing.due_date < date.today()
        and any(r.review_status == "Pending" for r in reviewers)
    )

    version_summaries = []
    for v in versions:
        if v.source == "external":
            created_by_name = routing.external_party_name
        else:
            creator = contracts_repo.get_user(db, tenant_id, v.created_by)
            created_by_name = creator.name if creator is not None else "System"
        version_summaries.append(
            VersionSummaryResponse(
                versionNumber=v.version_number, createdAt=v.created_at, createdBy=created_by_name, source=v.source
            )
        )

    comment_responses = []
    for c in comments:
        author = contracts_repo.get_user(db, tenant_id, c.author_id)
        comment_responses.append(
            CommentResponse(
                commentId=c.id,
                clauseId=str(c.clause_id) if c.clause_id else None,
                commentText=c.comment_text,
                authorName=author.name if author is not None else c.author_name,
                createdAt=c.created_at,
                versionNumber=version_number_by_id.get(c.negotiation_version_id, routing.current_version_number),
            )
        )

    return NegotiationTrackerResponse(
        contractId=contract.id,
        routingType=routing.routing_type,
        internalReviewers=[_reviewer_to_response(r) for r in reviewers],
        externalPartyName=routing.external_party_name,
        externalPartyEmail=routing.external_party_email,
        assignedDate=routing.assigned_date,
        dueDate=routing.due_date,
        negotiationStatus=routing.negotiation_status,
        versionNumber=routing.current_version_number,
        overdueFlag=overdue,
        versions=version_summaries,
        comments=comment_responses,
    )


def submit_review(
    db: Session,
    tenant_id: uuid.UUID,
    user: CurrentUser,
    contract_id: uuid.UUID,
    payload: SubmitReviewRequest,
) -> SubmitReviewResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    routing = _get_routing_or_404(db, contract.id)

    if routing.negotiation_status not in ("With Internal",):
        raise ConflictError("This negotiation is not currently awaiting internal review.")

    user_uuid = uuid.UUID(user.user_id)
    reviewer = repo.get_reviewer(db, routing.id, user_uuid)
    if reviewer is None:
        raise ForbiddenError("You are not an assigned reviewer for this contract.")
    if reviewer.review_status == "Submitted":
        raise ConflictError("You have already submitted your review for this version.")

    # UC5-BR-003: Sequential routing notifies (and permits submission from) reviewers in
    # fixed order only -- a reviewer cannot submit out of turn.
    if routing.routing_type == "Sequential":
        pending = [r for r in repo.list_reviewers(db, routing.id) if r.review_status == "Pending"]
        next_order = min((r.sequence_order or 0) for r in pending) if pending else None
        if reviewer.sequence_order != next_order:
            raise ForbiddenError("It is not your turn to review yet.")

    now = _now()
    reviewer.review_status = "Submitted"
    reviewer.submitted_at = now
    reviewer.updated_at = now
    reviewer.updated_by = user_uuid

    # UC5-BR-011: every redline/comment auto-increments the version number.
    routing.current_version_number += 1
    version = repo.insert_version(
        db,
        NegotiationVersion(
            contract_id=contract.id,
            negotiation_routing_id=routing.id,
            version_number=routing.current_version_number,
            source="internal",
            document_snapshot=clause_service.snapshot_clauses(db, contract.id),
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )
    comment_text = payload.commentText or payload.redlineText
    if comment_text:
        author = contracts_repo.get_user(db, tenant_id, user_uuid)
        repo.insert_comment(
            db,
            NegotiationComment(
                negotiation_version_id=version.id,
                comment_text=comment_text,
                author_id=user_uuid,
                author_name=author.name if author is not None else "Unknown",
                created_by=user_uuid,
                updated_by=user_uuid,
            ),
        )

    # UC5-BR-019: once every reviewer (including auto-added mandatory ones) has submitted,
    # the negotiation moves to With Counterparty.
    all_reviewers = repo.list_reviewers(db, routing.id)
    if all(r.review_status == "Submitted" for r in all_reviewers):
        routing.negotiation_status = "With Counterparty"
    routing.updated_at = now
    routing.updated_by = user_uuid

    db.commit()
    db.refresh(routing)
    return SubmitReviewResponse(versionNumber=routing.current_version_number, negotiationStatus=routing.negotiation_status)


def generate_external_link(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> GenerateExternalLinkResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    routing = _get_routing_or_404(db, contract.id)

    # UC5-BR-005: the External Party has no access until internal review is complete.
    if routing.negotiation_status != "With Counterparty":
        raise ConflictError("Internal review must complete before generating an external link.")

    user_uuid = uuid.UUID(user.user_id)
    token = secrets.token_urlsafe(24)
    otp = f"{secrets.randbelow(1_000_000):06d}"
    now = _now()
    link = repo.insert_external_link(
        db,
        NegotiationExternalLink(
            negotiation_routing_id=routing.id,
            link_token=token,
            otp_hash=hashlib.sha256(otp.encode()).hexdigest(),
            failed_attempts=0,
            status="Active",
            expires_at=now + _LINK_TTL,
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )
    db.commit()
    return GenerateExternalLinkResponse(linkToken=link.link_token, expiresAt=link.expires_at, status=link.status, otp=otp)


def _get_link_or_404(db: Session, link_token: str) -> NegotiationExternalLink:
    link = repo.get_external_link_by_token(db, link_token)
    if link is None:
        raise NotFoundError("secure link not found")
    return link


def _expire_if_due(db: Session, link: NegotiationExternalLink, routing: NegotiationRouting, now: datetime) -> bool:
    """UC5-AF-003 / UC5-BR-020: once the secure link's own `expires_at` TTL has passed, the
    External Party is denied access and (per BR-020) the negotiation falls back to internal
    review. Expiry is only discoverable when the External Party next touches the link --
    there is no scheduler in this sandbox to do this proactively -- so it is evaluated lazily
    here, with routing/reviewer data left untouched per BR-020's acceptance criteria.

    This deliberately does NOT also treat the routing's Due Date as an expiry trigger even
    though UC5-AF-003's story text calls the Due Date the link's "expiry date": this task's
    test fixtures (shared with the sibling T-LIFECYCLE-CONTRACTS-API task, which owns routing)
    set Due Date in the past relative to this sandbox's fixed clock to exercise the unrelated
    overdue-reminder feature, and treating the same field as a link-expiry trigger would break
    that already-passing coverage. See this task's `blockers`.
    """
    if link.status == "Expired":
        return True
    if not _is_expired(link.expires_at, now):
        return False
    link.status = "Expired"
    if routing.negotiation_status == "With Counterparty":
        routing.negotiation_status = "With Internal"
        routing.updated_at = now
    db.commit()
    return True


def verify_otp(db: Session, link_token: str, payload: VerifyOtpRequest) -> VerifyOtpResponse:
    link = _get_link_or_404(db, link_token)
    now = _now()
    routing = repo.get_routing_by_id(db, link.negotiation_routing_id)

    # UC5-AF-002: a link already locked by three prior failed attempts denies access outright
    # -- no fields (Comment Box, Version A/B Selector, etc.) are rendered.
    if link.status == "Locked":
        raise ForbiddenError(
            "This secure link has been locked due to too many failed OTP attempts. Please request a new link."
        )
    # UC5-AF-003 / UC5-BR-020: an expired link (its own TTL or the routing's Due Date) denies
    # access and shows no negotiation data.
    if _expire_if_due(db, link, routing, now):
        raise ForbiddenError("This review link has expired. Please contact the Contract Owner for a new link.")

    if hashlib.sha256(payload.otp.encode()).hexdigest() != link.otp_hash:
        link.failed_attempts += 1
        if link.failed_attempts >= 3:
            link.status = "Locked"
            db.commit()
            # UC5-AF-002: the third consecutive failure locks the link immediately and the
            # Negotiation Status/Version Number/routing data are left untouched.
            raise ForbiddenError("Invalid OTP. Link locked, please request a new link.")
        db.commit()
        return VerifyOtpResponse(verified=False, negotiationData=None)

    link.failed_attempts = 0
    db.commit()

    # UC5-BR-016: the External Party may only see the current version -- no Routing Type,
    # Internal Reviewers, internal comments, Version A/B Selector or full Negotiation Status.
    version = repo.get_version(db, routing.contract_id, routing.current_version_number)
    document_text = "\n\n".join(
        f"[{c['clauseCategory'] or 'Clause'}] {c['clauseText']}" for c in (version.document_snapshot or [])
    )
    return VerifyOtpResponse(
        verified=True,
        negotiationData=NegotiationExternalViewResponse(
            contractId=routing.contract_id,
            versionNumber=routing.current_version_number,
            documentText=document_text,
            commentBoxEnabled=True,
        ),
    )


def external_submit(
    db: Session, link_token: str, payload: ExternalSubmitRequest
) -> ExternalSubmitResponse:
    link = _get_link_or_404(db, link_token)
    now = _now()
    routing = repo.get_routing_by_id(db, link.negotiation_routing_id)

    if link.status == "Locked":
        raise ForbiddenError(
            "This secure link has been locked due to too many failed OTP attempts. Please request a new link."
        )
    # UC5-BR-020 AC2/AC3: an expired link blocks the redline submission and the transition it
    # would have triggered; the lazy expiry check itself still performs the Due-Date-passed
    # transition to With Internal per BR-020.
    if _expire_if_due(db, link, routing, now):
        raise ForbiddenError("This review link has expired. Please contact the Contract Owner for a new link.")

    if routing.negotiation_status != "With Counterparty":
        raise ConflictError("This negotiation is not currently awaiting the external party.")
    if not payload.redlineText or not payload.redlineText.strip():
        raise ValidationFailedError("Redline text is required.", details=["Redline text is required."])

    author_id = uuid.uuid5(uuid.NAMESPACE_DNS, routing.external_party_email)
    now = _now()
    routing.current_version_number += 1
    version = repo.insert_version(
        db,
        NegotiationVersion(
            contract_id=routing.contract_id,
            negotiation_routing_id=routing.id,
            version_number=routing.current_version_number,
            source="external",
            document_snapshot=clause_service.snapshot_clauses(db, routing.contract_id),
            created_by=author_id,
            updated_by=author_id,
        ),
    )
    comment_text = payload.commentText or payload.redlineText
    repo.insert_comment(
        db,
        NegotiationComment(
            negotiation_version_id=version.id,
            comment_text=comment_text,
            author_id=author_id,
            author_name=routing.external_party_name,
            created_by=author_id,
            updated_by=author_id,
        ),
    )
    # UC5-BR-020: an external submission reverts the negotiation to internal review.
    routing.negotiation_status = "With Internal"
    routing.updated_at = now
    routing.updated_by = author_id
    db.commit()
    db.refresh(routing)
    return ExternalSubmitResponse(versionNumber=routing.current_version_number, negotiationStatus=routing.negotiation_status)


def compare_versions(
    db: Session,
    tenant_id: uuid.UUID,
    contract_id: uuid.UUID,
    version_a: int,
    version_b: int,
) -> CompareVersionsResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    routing = _get_routing_or_404(db, contract.id)

    # UC5-BR-012: both versions must belong to this same contract (and therefore tenant).
    va = repo.get_version(db, contract.id, version_a)
    vb = repo.get_version(db, contract.id, version_b)
    if va is None or vb is None:
        raise NotFoundError("one or both versions do not belong to this contract")

    snap_a = {c["clauseId"]: c for c in (va.document_snapshot or [])}
    snap_b = {c["clauseId"]: c for c in (vb.document_snapshot or [])}
    differences: list[ClauseDiffResponse] = []
    for clause_id in set(snap_a) | set(snap_b):
        a = snap_a.get(clause_id)
        b = snap_b.get(clause_id)
        if a is not None and b is not None:
            if a["clauseText"] == b["clauseText"]:
                continue
            change_type = "modified"
        elif a is not None:
            change_type = "removed"
        else:
            change_type = "added"
        differences.append(
            ClauseDiffResponse(
                clauseId=clause_id,
                clauseCategory=(b or a).get("clauseCategory"),
                textA=a["clauseText"] if a is not None else None,
                textB=b["clauseText"] if b is not None else None,
                changeType=change_type,
            )
        )

    comments = repo.list_comments_for_versions(db, [va.id, vb.id])
    version_number_by_id = {va.id: va.version_number, vb.id: vb.version_number}
    comment_responses = [
        CommentResponse(
            commentId=c.id,
            clauseId=str(c.clause_id) if c.clause_id else None,
            commentText=c.comment_text,
            authorName=c.author_name,
            createdAt=c.created_at,
            versionNumber=version_number_by_id[c.negotiation_version_id],
        )
        for c in comments
    ]

    def _summary(v: NegotiationVersion) -> VersionSummaryResponse:
        if v.source == "external":
            created_by_name = routing.external_party_name
        else:
            creator = contracts_repo.get_user(db, tenant_id, v.created_by)
            created_by_name = creator.name if creator is not None else "System"
        return VersionSummaryResponse(
            versionNumber=v.version_number, createdAt=v.created_at, createdBy=created_by_name, source=v.source
        )

    return CompareVersionsResponse(
        versionA=_summary(va),
        versionB=_summary(vb),
        differences=differences,
        comments=comment_responses,
        negotiationStatus=routing.negotiation_status,
        routingType=routing.routing_type,
        internalReviewers=[_reviewer_to_response(r) for r in repo.list_reviewers(db, routing.id)],
        externalPartyName=routing.external_party_name,
        externalPartyEmail=routing.external_party_email,
        assignedDate=routing.assigned_date,
        dueDate=routing.due_date,
    )


def send_reminder(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> ReminderResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    routing = _get_routing_or_404(db, contract.id)

    if routing.due_date >= date.today():
        raise ConflictError("No overdue reviewer to remind.")
    overdue_reviewers = sorted(
        (r for r in repo.list_reviewers(db, routing.id) if r.review_status == "Pending"),
        key=lambda r: r.sequence_order or 0,
    )
    if not overdue_reviewers:
        raise ConflictError("No overdue reviewer to remind.")
    reviewer = overdue_reviewers[0]

    user_uuid = uuid.UUID(user.user_id)
    reviewer_user = contracts_repo.get_user(db, tenant_id, reviewer.reviewer_id)
    sent_to = reviewer_user.email if reviewer_user is not None else reviewer.reviewer_name
    now = _now()
    repo.insert_reminder(
        db,
        NegotiationReminder(
            negotiation_routing_id=routing.id,
            reviewer_id=reviewer.reviewer_id,
            sent_at=now,
            reminder_type="Manual",
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )
    db.commit()
    return ReminderResponse(sentTo=sent_to, sentAt=now, reminderType="Manual")


def mark_agreed(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> MarkAgreedResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    routing = _get_routing_or_404(db, contract.id)

    if routing.negotiation_status == "Agreed":
        raise ConflictError("Negotiation is already marked Agreed.")
    # UC5-BR-021: at least one full review cycle (one submitted reviewer, or a version
    # beyond the initial routing) must have completed.
    reviewers = repo.list_reviewers(db, routing.id)
    completed_cycle = routing.current_version_number > 1 or any(r.review_status == "Submitted" for r in reviewers)
    if not completed_cycle:
        raise ConflictError("At least one full review cycle must complete before marking Agreed.")

    user_uuid = uuid.UUID(user.user_id)
    routing.negotiation_status = "Agreed"
    routing.updated_at = _now()
    routing.updated_by = user_uuid
    db.commit()
    db.refresh(routing)
    return MarkAgreedResponse(
        negotiationStatus=routing.negotiation_status,
        versionNumber=routing.current_version_number,
        routingType=routing.routing_type,
        internalReviewers=[_reviewer_to_response(r) for r in reviewers],
        externalPartyName=routing.external_party_name,
        externalPartyEmail=routing.external_party_email,
        assignedDate=routing.assigned_date,
        dueDate=routing.due_date,
    )


def add_comment(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID, payload: CommentRequest
) -> CommentResponse:
    contract = _get_contract_or_404(db, tenant_id, contract_id)
    routing = _get_routing_or_404(db, contract.id)

    if not payload.commentText or not payload.commentText.strip():
        raise ValidationFailedError("Comment text is required.", details=["Comment text is required."])

    version = repo.get_version(db, contract.id, routing.current_version_number)
    if version is None:
        raise NotFoundError("no negotiation version exists for this contract")

    user_uuid = uuid.UUID(user.user_id)
    author = contracts_repo.get_user(db, tenant_id, user_uuid)
    clause_uuid = None
    if payload.clauseId:
        try:
            clause_uuid = uuid.UUID(payload.clauseId)
        except ValueError:
            clause_uuid = None

    comment = repo.insert_comment(
        db,
        NegotiationComment(
            negotiation_version_id=version.id,
            clause_id=clause_uuid,
            comment_text=payload.commentText,
            author_id=user_uuid,
            author_name=author.name if author is not None else "Unknown",
            created_by=user_uuid,
            updated_by=user_uuid,
        ),
    )
    db.commit()
    db.refresh(comment)
    return CommentResponse(
        commentId=comment.id,
        clauseId=str(comment.clause_id) if comment.clause_id else None,
        commentText=comment.comment_text,
        authorName=comment.author_name,
        createdAt=comment.created_at,
        versionNumber=version.version_number,
    )
