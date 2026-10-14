"""The one notification service (UC6, UC7, UC11): toggles gate each channel, an in-app
alert is recorded, and a failing email never fails the action that triggered it.
"""
import uuid

from app.models.tracker import TenantAuditLog, TenantNotificationSetting
from app.services import notifications


def _dispatch(db_session, tenant_id: uuid.UUID, event: str = notifications.EVENT_APPROVED) -> None:
    notifications.dispatch(
        db_session,
        tenant_id,
        event,
        recipients=["signer@acme.test"],
        subject="Subject line",
        body="Body",
        entity="Contract",
        actor_id=uuid.uuid4(),
    )


def _entries(db_session, tenant_id: uuid.UUID, action: str) -> list[TenantAuditLog]:
    return (
        db_session.query(TenantAuditLog)
        .filter(TenantAuditLog.tenant_id == tenant_id, TenantAuditLog.log_action == action)
        .all()
    )


def test_unsaved_event_defaults_to_on_and_records_in_app_alert(db_session):
    tenant_id = uuid.uuid4()

    _dispatch(db_session, tenant_id)

    entries = _entries(db_session, tenant_id, "Notification")
    assert len(entries) == 1
    assert notifications.EVENT_APPROVED in entries[0].details


def test_in_app_toggle_off_records_nothing(db_session):
    tenant_id = uuid.uuid4()
    db_session.add(
        TenantNotificationSetting(
            tenant_id=tenant_id,
            event_name=notifications.EVENT_APPROVED,
            email_toggle=False,
            in_app_toggle=False,
            created_by=uuid.uuid4(),
            updated_by=uuid.uuid4(),
        )
    )
    db_session.commit()

    _dispatch(db_session, tenant_id)

    assert _entries(db_session, tenant_id, "Notification") == []


def test_email_failure_is_logged_and_never_raises(db_session, monkeypatch):
    tenant_id = uuid.uuid4()

    def boom(recipients, subject, body):
        raise RuntimeError("smtp down")

    monkeypatch.setattr(notifications, "_send_email", boom)

    _dispatch(db_session, tenant_id)

    failures = _entries(db_session, tenant_id, "NotificationFailed")
    assert len(failures) == 1
    assert "email delivery failed" in failures[0].details
    # The in-app channel still fires -- one channel failing does not suppress the other.
    assert len(_entries(db_session, tenant_id, "Notification")) == 1
