"""The one service that sends every email and in-app alert (UC6, UC7, UC11).

Every notification in this application -- approve, reject, send back, ready for signature,
signing link, decline, executed, new user invite -- goes through `dispatch` here. Two rules
hold for all of them:

* a channel only fires when that event's toggle is ON in Settings > Notifications
  (`tenant_notification_settings`, defaulting to On for an event a tenant has never saved);
* a delivery failure never fails the action that triggered it -- the exception is swallowed
  and recorded, so an unreachable mail server cannot roll back an approval or a signature.

Callers invoke `dispatch` *after* their own `db.commit()`: the business write is already
durable, and the notification's own bookkeeping commits separately.

The in-app channel is recorded in `tenant_audit_log` (`log_action = "Notification"`). There
is no `in_app_notifications` table in any module contract and migrations may not be added
for one here, so the tenant-scoped append-only log is where an in-app alert lands.
"""
import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.message import EmailMessage

from sqlalchemy.orm import Session

from app.config import settings
from app.models.tracker import TenantAuditLog, TenantNotificationSetting
from app.repositories import settings_audit_log as audit_log_repo
from app.repositories import settings_notifications as notifications_repo

logger = logging.getLogger(__name__)

# Event names are the Settings > Notifications rows the toggles belong to -- they must match
# `app.repositories.settings_notifications.EVENT_NAMES` exactly or the toggle lookup silently
# falls through to the default.
EVENT_APPROVED = "Contract Approved"
EVENT_REJECTED = "Contract Rejected"
EVENT_SENT_BACK = "Contract Sent Back"
EVENT_READY_FOR_SIGNATURE = "Contract Ready for Signature"
EVENT_SENT_FOR_SIGNATURE = "Contract Sent for Signature"
EVENT_SIGNATURE_DECLINED = "Contract Signature Declined"
EVENT_EXECUTED = "Contract Signed"
EVENT_USER_INVITED = "New User Invited"
# UC5/UC7/UC9 time-driven and automatic notifications (see app.services.scheduled_notifications).
EVENT_SENT_TO_COUNTERPARTY = "Contract Sent to Counterparty"
EVENT_REVIEW_REMINDER = "Review Reminder"
EVENT_SIGNATURE_REMINDER = "Signature Reminder"
EVENT_EXPIRING_SOON = "Contract Expiring Soon"


def _toggles(db: Session, tenant_id: uuid.UUID, event_name: str) -> tuple[bool, bool]:
    """(email, in-app) for this tenant's event. An event the tenant has never saved is On on
    both channels (UC11-BR-007), the same default `ensure_seeded` writes."""
    row: TenantNotificationSetting | None = notifications_repo.get_by_name(db, tenant_id, event_name)
    if row is None:
        return True, True
    return bool(row.email_toggle), bool(row.in_app_toggle)


def _send_email(recipients: list[str], subject: str, body: str) -> None:
    """Hands the message to the configured SMTP relay. With no `SMTP_HOST` configured (the
    default in development and in tests) the message is logged instead of sent -- there is no
    mail provider dependency in this repository."""
    if not settings.smtp_host:
        logger.info("notification email (no SMTP_HOST configured) to=%s subject=%s", recipients, subject)
        return

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=settings.smtp_timeout_seconds) as client:
        if settings.smtp_use_tls:
            client.starttls()
        if settings.smtp_username:
            client.login(settings.smtp_username, settings.smtp_password)
        client.send_message(message)


def _append(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    action: str,
    entity: str,
    details: str,
    actor_id: uuid.UUID,
) -> None:
    audit_log_repo.append(
        db,
        TenantAuditLog(
            tenant_id=tenant_id,
            log_date_time=datetime.now(timezone.utc),
            log_user=str(actor_id),
            log_action=action,
            log_entity=entity,
            details=details,
            created_by=actor_id,
            updated_by=actor_id,
        ),
    )


def dispatch(
    db: Session,
    tenant_id: uuid.UUID | None,
    event_name: str,
    *,
    recipients: list[str | None] | None,
    subject: str,
    body: str,
    entity: str,
    actor_id: uuid.UUID,
) -> None:
    """Send one event on whichever channels the tenant has enabled. Never raises."""
    if tenant_id is None:
        return
    actor = actor_id
    to = sorted({r.strip() for r in (recipients or []) if r and r.strip()})

    try:
        email_on, in_app_on = _toggles(db, tenant_id, event_name)
    except Exception:  # pragma: no cover - a toggle read failure must not fail the action
        logger.exception("could not read notification toggles for %s", event_name)
        return

    if email_on and to:
        try:
            _send_email(to, subject, body)
        except Exception:
            # The triggering action has already committed; record the failure and carry on.
            logger.exception("notification email failed for %s", event_name)
            try:
                db.rollback()
                _append(
                    db,
                    tenant_id,
                    action="NotificationFailed",
                    entity=entity,
                    details=f"{event_name}: email delivery failed to {', '.join(to)}",
                    actor_id=actor,
                )
                db.commit()
            except Exception:  # pragma: no cover - logging the failure must not fail either
                logger.exception("could not record notification failure for %s", event_name)
                db.rollback()

    if in_app_on:
        try:
            _append(
                db,
                tenant_id,
                action="Notification",
                entity=entity,
                details=f"{event_name}: {subject}",
                actor_id=actor,
            )
            db.commit()
        except Exception:
            logger.exception("in-app notification failed for %s", event_name)
            db.rollback()
