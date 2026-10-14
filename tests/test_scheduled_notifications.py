"""The notifications that fire because a date passed, plus the auto-send that fires because
internal review finished:

* UC5 Auto Send to Counterparty -- the last/only reviewer submitting issues and emails the
  secure link and OTP by itself, and the OTP never appears on any response body.
* UC5 reviewer reminders -- one email a day to the overdue reviewer and the owner, stopping
  on submission or on Agreed.
* UC7 signature reminders -- every X days until the signer signs or declines.
* UC9 renewal alerts -- 90/60/30 days before the End Date and the Notice Period deadline,
  each sent exactly once.
"""
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest

from app.models.contract_lifecycle import RenewalAlert
from app.models.esignature import Signer
from app.models.lifecycle_negotiation import NegotiationExternalLink, NegotiationRouting
from app.services import lifecycle_negotiation as negotiation_service
from app.services import notifications, scheduled_notifications
from tests.test_lifecycle_negotiation import (
    CONTRACT_OWNER,
    FIXED_OTP,
    LEGAL_REVIEWER,
    TENANT_ADMIN,
    _headers,
    _route,
    _seed_contract,
    _seed_tenant,
    _seed_user,
    _setup_analyzed_contract,
)


@pytest.fixture(autouse=True)
def _fixed_otp(monkeypatch):
    monkeypatch.setattr(negotiation_service, "_generate_otp", lambda: FIXED_OTP)


@pytest.fixture()
def sent(monkeypatch):
    """Capture every email `notifications.dispatch` would hand to the relay."""
    captured: list[tuple[list[str], str]] = []
    monkeypatch.setattr(
        notifications, "_send_email", lambda to, subject, body: captured.append((to, subject))
    )
    return captured


def _submit_review(db_client, contract_id, reviewer_id):
    return db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, reviewer_id),
    )


# ---- UC5: Auto Send to Counterparty --------------------------------------------------------


def test_last_reviewer_submission_auto_issues_and_emails_the_secure_link(db_client, db_session, sent):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])

    resp = _submit_review(db_client, contract_id, legal_id)
    assert resp.status_code == 200
    assert resp.json()["negotiationStatus"] == "With Counterparty"

    routing = db_session.query(NegotiationRouting).filter_by(contract_id=contract_id).one()
    links = (
        db_session.query(NegotiationExternalLink)
        .filter_by(negotiation_routing_id=routing.id)
        .all()
    )
    assert len(links) == 1
    # The link and its OTP went to the external party's inbox, nowhere else.
    to, subject = sent[-1]
    assert to == ["jane@counterparty.test"]
    assert "review" in subject.lower()

    # ...and that auto-issued link really works.
    verified = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{links[0].link_token}/verify-otp",
        json={"otp": FIXED_OTP},
    )
    assert verified.status_code == 200
    assert verified.json()["verified"] is True


def test_parallel_routing_only_auto_sends_once_every_reviewer_has_submitted(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    second_reviewer = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    _route(db_client, contract_id, owner_id, [legal_id, second_reviewer], routingType="Parallel")

    first = _submit_review(db_client, contract_id, legal_id)
    assert first.json()["negotiationStatus"] == "With Internal"
    routing = db_session.query(NegotiationRouting).filter_by(contract_id=contract_id).one()
    assert db_session.query(NegotiationExternalLink).filter_by(negotiation_routing_id=routing.id).count() == 0

    second = _submit_review(db_client, contract_id, second_reviewer)
    assert second.json()["negotiationStatus"] == "With Counterparty"
    assert db_session.query(NegotiationExternalLink).filter_by(negotiation_routing_id=routing.id).count() == 1


def test_external_link_response_never_carries_the_otp(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    _submit_review(db_client, contract_id, legal_id)

    body = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/external-link",
        headers=_headers(CONTRACT_OWNER, owner_id),
    ).json()
    assert "otp" not in body
    assert set(body) == {"linkToken", "expiresAt", "status"}


# ---- UC5: automatic reviewer reminders -----------------------------------------------------


def test_overdue_review_reminds_reviewer_and_owner_once_a_day(db_client, db_session, sent):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])  # dueDate is in the past

    assert scheduled_notifications.run_reviewer_reminders(db_session) == 2
    recipients = {addr for to, _ in sent for addr in to}
    assert f"{legal_id}@acme.test" in recipients
    assert f"{owner_id}@acme.test" in recipients

    # Same day again: nothing more goes out.
    sent.clear()
    assert scheduled_notifications.run_reviewer_reminders(db_session) == 0
    assert sent == []

    # Tomorrow: one more round.
    tomorrow = date.today() + timedelta(days=1)
    assert scheduled_notifications.run_reviewer_reminders(db_session, today=tomorrow) == 2


def test_reviewer_reminders_stop_once_the_review_is_submitted(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    _submit_review(db_client, contract_id, legal_id)

    assert scheduled_notifications.run_reviewer_reminders(db_session) == 0


def test_reviewer_reminders_stop_once_the_contract_is_marked_agreed(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    second_reviewer = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    _route(db_client, contract_id, owner_id, [legal_id, second_reviewer], routingType="Parallel")
    _submit_review(db_client, contract_id, legal_id)  # one still Pending -> would be reminded

    marked = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/mark-agreed",
        headers=_headers(LEGAL_REVIEWER, second_reviewer),
    )
    assert marked.status_code == 200
    assert scheduled_notifications.run_reviewer_reminders(db_session) == 0


# ---- UC7: signature reminders --------------------------------------------------------------


def _seed_signer(db_session, tenant_id, contract_id, actor_id, *, status="Sent", last_sent=None, frequency=3):
    signer = Signer(
        contract_id=contract_id,
        signer_name="Sam Signer",
        signer_email="sam@acme.test",
        signer_type="Internal",
        signing_order=1,
        signature_method="In-built E-signature",
        reminder_frequency_days=frequency,
        signer_status=status,
        otp_attempts=0,
        last_reminder_sent_at=last_sent,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(signer)
    db_session.commit()
    return signer


def test_signature_reminder_fires_every_configured_number_of_days(db_client, db_session, sent):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, admin_id, owner_id, status="Sent")
    now = datetime.now(timezone.utc)
    signer = _seed_signer(
        db_session, tenant_id, contract_id, admin_id, last_sent=now - timedelta(days=4), frequency=3
    )

    assert scheduled_notifications.run_signature_reminders(db_session, now=now) == 1
    assert sent[-1][0] == ["sam@acme.test"]

    # Not due again until the next interval elapses.
    assert scheduled_notifications.run_signature_reminders(db_session, now=now) == 0
    assert scheduled_notifications.run_signature_reminders(db_session, now=now + timedelta(days=3)) == 1


def test_signature_reminder_stops_once_the_signer_has_signed(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, admin_id, owner_id, status="Sent")
    now = datetime.now(timezone.utc)
    _seed_signer(
        db_session, tenant_id, contract_id, admin_id,
        status="Signed", last_sent=now - timedelta(days=30),
    )

    assert scheduled_notifications.run_signature_reminders(db_session, now=now) == 0


def test_signature_reminder_stops_once_the_contract_is_withdrawn(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, admin_id, owner_id, status="Withdrawn")
    now = datetime.now(timezone.utc)
    _seed_signer(db_session, tenant_id, contract_id, admin_id, last_sent=now - timedelta(days=30))

    assert scheduled_notifications.run_signature_reminders(db_session, now=now) == 0


# ---- UC9: renewal alerts -------------------------------------------------------------------


def test_renewal_alert_fires_at_each_threshold_and_only_once(db_client, db_session, sent):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    today = date(2026, 6, 1)
    contract_id = _seed_contract(
        db_session, tenant_id, admin_id, owner_id,
        status="Active", end_date=today + timedelta(days=90),
    )

    assert scheduled_notifications.run_renewal_alerts(db_session, today=today) == 1
    recipients = {addr for to, _ in sent for addr in to}
    assert f"{owner_id}@acme.test" in recipients  # Owner
    assert f"{admin_id}@acme.test" in recipients  # Tenant Admin

    # Re-running the same day, and any later day inside the same window, sends nothing more.
    assert scheduled_notifications.run_renewal_alerts(db_session, today=today) == 0
    assert scheduled_notifications.run_renewal_alerts(db_session, today=today + timedelta(days=5)) == 0

    # The next window is its own, single alert.
    assert scheduled_notifications.run_renewal_alerts(db_session, today=today + timedelta(days=30)) == 1
    rows = db_session.query(RenewalAlert).filter_by(contract_id=contract_id).all()
    assert sorted(r.threshold_days for r in rows) == [60, 90]


def test_renewal_alert_also_tracks_the_notice_period_deadline(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    today = date(2026, 6, 1)
    _seed_contract(
        db_session, tenant_id, admin_id, owner_id,
        status="Active", end_date=today + timedelta(days=120), notice_period_text="30 days",
    )

    # End Date is 120 days out (no window yet); the Notice Period deadline is 90 days out.
    assert scheduled_notifications.run_renewal_alerts(db_session, today=today) == 1
    bases = {row.alert_basis for row in db_session.query(RenewalAlert).all()}
    assert bases == {"Notice Period deadline"}


def test_renewal_alerts_ignore_contracts_that_are_not_live(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    today = date(2026, 6, 1)
    _seed_contract(
        db_session, tenant_id, admin_id, owner_id,
        status="Draft", end_date=today + timedelta(days=30),
    )

    assert scheduled_notifications.run_renewal_alerts(db_session, today=today) == 0


# ---- the sweep ------------------------------------------------------------------------------


def test_run_all_reports_each_sweep(db_client, db_session):
    assert scheduled_notifications.run_all(db_session) == {
        "reviewerReminders": 0,
        "signatureReminders": 0,
        "renewalAlerts": 0,
    }
