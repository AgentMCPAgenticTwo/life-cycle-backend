"""The time-driven half of this application's notifications.

Three things in the use cases happen because a date passed, not because anyone called an
endpoint:

* **UC5 reviewer reminders** -- once a negotiation's Due Date has passed, the overdue
  reviewer and the Contract Owner each get one email per day. Stops as soon as the review is
  submitted or the negotiation is marked Agreed.
* **UC7 signature reminders** -- a signer who has been sent a link but has not signed is
  reminded every X days, where X is that signer's Reminder Frequency (falling back to the
  tenant's Settings > E-signature value, then 3). Stops when the signer signs or declines, or
  the contract is withdrawn/declined/executed.
* **UC9 renewal alerts** -- 90, 60 and 30 days before the Contract End Date, and separately
  before the Notice Period deadline, the Owner and every Tenant Admin are alerted. Each
  alert fires exactly once: the `renewal_alerts` row for (contract, threshold, basis) is the
  once-only guard, so a sweep that runs many times a day still sends one.

Everything goes out through `app.services.notifications.dispatch`, so each of these respects
the tenant's Settings > Notifications toggles and can never raise into the caller.

`run_all` is pure business logic over a `Session` -- it is called by the background sweep
started in `app.main` and is directly callable from a test or a one-off script. The sweep is
in-process on purpose: this repository declares no scheduler dependency and CLAUDE.md does
not permit adding one.
"""
import asyncio
import logging
import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import settings
from app.models.contract_lifecycle import RenewalAlert
from app.models.lifecycle_negotiation import NegotiationReminder
from app.repositories import esignature_settings as esignature_settings_repo
from app.repositories import lifecycle_negotiation as negotiation_repo
from app.repositories import scheduled_notifications as repo
from app.services import notifications
from app.services.contract_lifecycle import (
    EXECUTED_STATUSES,
    RENEWAL_THRESHOLDS_DAYS,
    _parse_notice_period_days,
)

logger = logging.getLogger(__name__)

# UC7: a contract in one of these states is finished with signatures -- no further reminders.
SIGNING_CLOSED_STATUSES = {"Executed", "SignatureDeclined", "Withdrawn", "Terminated", "Expired"}
DEFAULT_SIGNATURE_REMINDER_DAYS = 3

ALERT_BASIS_END_DATE = "Contract End Date"
ALERT_BASIS_NOTICE = "Notice Period deadline"

# The actor recorded against a notification nobody triggered. A fixed, derived UUID rather
# than a hard-coded literal -- CLAUDE.md forbids hard-coded ids.
SYSTEM_ACTOR_ID = uuid.uuid5(uuid.NAMESPACE_DNS, "scheduled-notifications.system")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_naive_utc(value: datetime) -> datetime:
    """SQLite (the tests' stand-in for Postgres) does not round-trip tz-aware columns, so a
    value read back may be naive. Compare everything on naive UTC wall-clock."""
    return value.replace(tzinfo=None) if value.tzinfo is None else value.astimezone(timezone.utc).replace(tzinfo=None)


# ------------------------------------------------------- UC5: reviewer reminders (daily) ---


def run_reviewer_reminders(db: Session, today: date | None = None) -> int:
    """One email per day, per overdue reviewer, to the reviewer and to the Contract Owner.

    The once-a-day guard is the `negotiation_reminders` table itself: an automatic reminder
    already written since midnight UTC for the same (routing, reviewer) means today is done.
    The Owner's copy is recorded as the same routing with a null `reviewer_id`.
    """
    today = today or _now().date()
    midnight = datetime(today.year, today.month, today.day, tzinfo=timezone.utc)
    sent = 0

    for routing in negotiation_repo.list_overdue_routings(db, today):
        contract = repo.get_contract_by_id(db, routing.contract_id)
        if contract is None:
            continue
        pending = [r for r in negotiation_repo.list_reviewers(db, routing.id) if r.review_status == "Pending"]
        if not pending:
            continue

        already = negotiation_repo.list_reminders_since(db, routing.id, midnight)
        already_reviewer_ids = {r.reviewer_id for r in already if r.reminder_type == "Auto"}
        owner_done = any(r.reminder_type == "Auto" and r.reviewer_id is None for r in already)
        owner_email = repo.get_user_email(db, contract.contract_owner_id or contract.owner_id)
        now = _now()

        for reviewer in pending:
            if reviewer.reviewer_id in already_reviewer_ids:
                continue
            reviewer_email = repo.get_user_email(db, reviewer.reviewer_id)
            negotiation_repo.insert_reminder(
                db,
                NegotiationReminder(
                    negotiation_routing_id=routing.id,
                    reviewer_id=reviewer.reviewer_id,
                    sent_at=now,
                    reminder_type="Auto",
                    created_by=SYSTEM_ACTOR_ID,
                    updated_by=SYSTEM_ACTOR_ID,
                ),
            )
            db.commit()
            notifications.dispatch(
                db,
                contract.tenant_id,
                notifications.EVENT_REVIEW_REMINDER,
                recipients=[reviewer_email],
                subject=f"Reminder: your review of {contract.contract_name} is overdue",
                body=(
                    f"{reviewer.reviewer_name},\n\n"
                    f"Your review of {contract.contract_name} was due on "
                    f"{routing.due_date:%Y-%m-%d} and has not been submitted yet."
                ),
                entity="Negotiation",
                actor_id=SYSTEM_ACTOR_ID,
            )
            sent += 1

        if not owner_done:
            negotiation_repo.insert_reminder(
                db,
                NegotiationReminder(
                    negotiation_routing_id=routing.id,
                    reviewer_id=None,
                    sent_at=now,
                    reminder_type="Auto",
                    created_by=SYSTEM_ACTOR_ID,
                    updated_by=SYSTEM_ACTOR_ID,
                ),
            )
            db.commit()
            names = ", ".join(r.reviewer_name for r in pending)
            notifications.dispatch(
                db,
                contract.tenant_id,
                notifications.EVENT_REVIEW_REMINDER,
                recipients=[owner_email],
                subject=f"{contract.contract_name}: review overdue",
                body=(
                    f"The following reviewers have not submitted their review of "
                    f"{contract.contract_name}, which was due on {routing.due_date:%Y-%m-%d}: "
                    f"{names}."
                ),
                entity="Negotiation",
                actor_id=SYSTEM_ACTOR_ID,
            )
            sent += 1

    return sent


# ---------------------------------------------------- UC7: signature reminders (every X) ---


def _signature_reminder_days(db: Session, tenant_id: uuid.UUID, signer_days: int | None) -> int:
    if signer_days is not None and signer_days > 0:
        return signer_days
    tenant_settings = esignature_settings_repo.get_by_tenant(db, tenant_id)
    if tenant_settings is not None and tenant_settings.reminder_frequency_days > 0:
        return tenant_settings.reminder_frequency_days
    return DEFAULT_SIGNATURE_REMINDER_DAYS


def run_signature_reminders(db: Session, now: datetime | None = None) -> int:
    """Re-send the signing prompt every X days until the signer signs or declines, or the
    contract leaves the signing flow. `signers.last_reminder_sent_at` is both the cadence
    anchor and the idempotency guard -- before the first reminder the anchor is the moment
    the signer row was last written, i.e. when their link was sent."""
    now = now or _now()
    sent = 0

    for signer in repo.list_open_signers(db):
        contract = repo.get_contract_by_id(db, signer.contract_id)
        if contract is None or contract.status in SIGNING_CLOSED_STATUSES:
            continue
        frequency = _signature_reminder_days(db, contract.tenant_id, signer.reminder_frequency_days)
        anchor = signer.last_reminder_sent_at or signer.updated_at
        if anchor is None:
            continue
        if _as_naive_utc(anchor) + timedelta(days=frequency) > _as_naive_utc(now):
            continue

        signer.last_reminder_sent_at = now
        signer.updated_by = SYSTEM_ACTOR_ID
        db.commit()
        notifications.dispatch(
            db,
            contract.tenant_id,
            notifications.EVENT_SIGNATURE_REMINDER,
            recipients=[signer.signer_email],
            subject=f"Reminder: please sign {contract.contract_name}",
            body=(
                f"{signer.signer_name},\n\n"
                f"{contract.contract_name} is still waiting for your signature. Open your "
                "signing link and enter the one-time password sent to you to continue."
            ),
            entity="Signer",
            actor_id=SYSTEM_ACTOR_ID,
        )
        sent += 1

    return sent


# ----------------------------------------------------------- UC9: renewal alerts (once) ---


def _renewal_windows(contract, today: date) -> list[tuple[int, str, date]]:
    """The (threshold, basis, deadline) alerts that are due for this contract today.

    For each basis only the *tightest* threshold whose window the deadline has entered is
    returned, so a contract first seen 45 days out gets the 60-day alert, not a burst of 90
    and 60 together, and gets the 30-day alert when it reaches 30.
    """
    windows: list[tuple[int, str, date]] = []
    deadlines: list[tuple[str, date]] = [(ALERT_BASIS_END_DATE, contract.end_date)]
    notice_days = _parse_notice_period_days(contract.notice_period_text)
    if notice_days is not None:
        deadlines.append((ALERT_BASIS_NOTICE, contract.end_date - timedelta(days=notice_days)))

    for basis, deadline in deadlines:
        days_remaining = (deadline - today).days
        if days_remaining < 0:
            continue
        applicable = [t for t in RENEWAL_THRESHOLDS_DAYS if days_remaining <= t]
        if applicable:
            windows.append((min(applicable), basis, deadline))
    return windows


def run_renewal_alerts(db: Session, today: date | None = None) -> int:
    today = today or _now().date()
    sent = 0

    for contract in repo.list_renewal_candidates(db, tuple(sorted(EXECUTED_STATUSES))):
        for threshold, basis, deadline in _renewal_windows(contract, today):
            # UC9: each alert is sent only once -- the row is the guard.
            if repo.get_renewal_alert(db, contract.id, threshold, basis) is not None:
                continue
            repo.insert_renewal_alert(
                db,
                RenewalAlert(
                    contract_id=contract.id,
                    threshold_days=threshold,
                    alert_basis=basis,
                    triggered_at=_now(),
                    created_by=SYSTEM_ACTOR_ID,
                    updated_by=SYSTEM_ACTOR_ID,
                ),
            )
            db.commit()
            recipients = [repo.get_user_email(db, contract.contract_owner_id or contract.owner_id)]
            recipients.extend(repo.list_role_emails(db, contract.tenant_id, "TENANT_ADMIN"))
            notifications.dispatch(
                db,
                contract.tenant_id,
                notifications.EVENT_EXPIRING_SOON,
                recipients=recipients,
                subject=f"{contract.contract_name}: {threshold} days to the {basis}",
                body=(
                    f"Renewal action required: {threshold} days remaining before the {basis} "
                    f"({deadline:%Y-%m-%d}) of {contract.contract_name}."
                ),
                entity="Contract",
                actor_id=SYSTEM_ACTOR_ID,
            )
            sent += 1

    return sent


# --------------------------------------------------------------------- the sweep itself ---


def run_all(db: Session) -> dict[str, int]:
    """Run every time-driven notification once. Each sweep is isolated: one failing sweep
    does not stop the others, exactly as a delivery failure never fails an action."""
    results: dict[str, int] = {}
    for name, fn in (
        ("reviewerReminders", run_reviewer_reminders),
        ("signatureReminders", run_signature_reminders),
        ("renewalAlerts", run_renewal_alerts),
    ):
        try:
            results[name] = fn(db)
        except Exception:
            logger.exception("scheduled notification sweep %s failed", name)
            db.rollback()
            results[name] = 0
    return results


async def sweep_loop() -> None:
    """Run `run_all` on its own session every `NOTIFICATION_SWEEP_INTERVAL_SECONDS`.

    The sweeps are idempotent per day/per cadence, so running more often than daily is safe --
    it only makes an alert land closer to the moment it became due.
    """
    from app.db import SessionLocal  # imported late: the engine may not exist at import time

    interval = settings.notification_sweep_interval_seconds
    while True:
        if SessionLocal is None:
            return
        try:
            await asyncio.to_thread(_run_all_in_new_session, SessionLocal)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover - the loop must outlive any single failure
            logger.exception("notification sweep iteration failed")
        await asyncio.sleep(interval)


def _run_all_in_new_session(session_factory) -> dict[str, int]:
    db = session_factory()
    try:
        return run_all(db)
    finally:
        db.close()
