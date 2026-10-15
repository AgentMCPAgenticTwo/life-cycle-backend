"""Exercises every endpoint this task owns under
`/api/v1/lifecycle/contracts/{id}/negotiation/...` and
`/api/v1/lifecycle/negotiation/external/{linkToken}/...`: the routing precondition
(UC5-BR-023), reviewer validation (UC5-AF-001/FV-001), status transitions
(UC5-BR-018/019/020/021), auto-versioning (UC5-BR-011), Compare Versions scoping
(UC5-BR-012), and the OTP-secured external party flow with lockout (UC5-BR-005/016).
"""
import uuid
from datetime import date, timedelta

import pytest

from app.models.approval import Approval, ApprovalMatrixConfig, ApprovalMatrixStep
from app.models.contract import Contract
from app.models.contract_lifecycle import ActivityLogEntry
from app.models.counterparty import Counterparty
from app.models.tracker import ApprovalMatrixRule
from app.models.tenant import Tenant
from app.models.template import Template
from app.models.user import User
from app.services import lifecycle_negotiation as negotiation_service
from tests.conftest import auth_headers

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
APPROVER = "APPROVER"
EXTERNAL_PARTY = "EXTERNAL_PARTY"

# The OTP never leaves the system on a response body (UC5-BR-016: it is emailed only), so a
# test that has to complete the external flow pins the generator instead of reading it back.
FIXED_OTP = "135790"


@pytest.fixture(autouse=True)
def _fixed_otp(monkeypatch):
    monkeypatch.setattr(negotiation_service, "_generate_otp", lambda: FIXED_OTP)


def _headers(role: str, user_id) -> dict:
    return auth_headers(role, user_id)


def _seed_tenant(db_session) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    seed_id = uuid.uuid4()
    db_session.add(Tenant(id=tenant_id, name="Acme Co", high_risk_threshold=70, created_by=seed_id, updated_by=seed_id))
    db_session.commit()
    return tenant_id


def _seed_user(db_session, tenant_id: uuid.UUID, role: str, *, name: str | None = None) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(
        User(
            id=user_id, tenant_id=tenant_id, name=name or f"{role.title()} User", email=f"{user_id}@acme.test",
            role=role, created_by=user_id, updated_by=user_id,
        )
    )
    db_session.commit()
    return user_id


def _seed_contract(db_session, tenant_id: uuid.UUID, admin_id: uuid.UUID, owner_id: uuid.UUID, **overrides) -> uuid.UUID:
    counterparty_id = uuid.uuid4()
    db_session.add(
        Counterparty(
            id=counterparty_id, tenant_id=tenant_id, name="Globex", email="c@globex.test", company="Globex",
            created_by=admin_id, updated_by=admin_id,
        )
    )
    template_id = uuid.uuid4()
    db_session.add(
        Template(
            id=template_id, tenant_id=tenant_id, template_name="NDA", template_category="NDA",
            document_format="DOCX", template_body="body", status="Active", current_version=1,
            created_by=admin_id, updated_by=admin_id,
        )
    )
    contract_id = uuid.uuid4()
    defaults = dict(
        id=contract_id, tenant_id=tenant_id, contract_name="NDA with Globex", contract_type="NDA",
        industry="Product", template_id=template_id, counterparty_id=counterparty_id, contract_owner_id=owner_id,
        contract_value=10000, currency="USD", start_date=date(2026, 1, 1), end_date=date(2027, 1, 1),
        renewal_type="None", assigned_date=date(2026, 1, 1), due_date=date(2026, 2, 1), status="Draft",
        created_by=admin_id, updated_by=admin_id,
    )
    defaults.update(overrides)
    db_session.add(Contract(**defaults))
    db_session.commit()
    return contract_id


def _routing_payload(reviewer_ids, **overrides) -> dict:
    payload = {
        "routingType": "Sequential",
        "internalReviewers": [str(r) for r in reviewer_ids],
        "externalPartyName": "Jane Counterparty",
        "externalPartyEmail": "jane@counterparty.test",
        "assignedDate": "2026-01-01",
        "dueDate": "2026-01-15",
    }
    payload.update(overrides)
    return payload


def _seed_approval_rule(db_session, tenant_id: uuid.UUID, *, contract_type: str = "NDA", steps: int = 1) -> list[uuid.UUID]:
    """An Approval Matrix config matching the default seeded contract (NDA, 10,000), one
    APPROVER per step. Returns the approvers in step order."""
    seed_id = uuid.uuid4()
    config = ApprovalMatrixConfig(
        tenant_id=tenant_id, contract_type=contract_type, value_min=0, value_max=1_000_000,
        created_by=seed_id, updated_by=seed_id,
    )
    db_session.add(config)
    db_session.flush()
    approver_ids = []
    for step_number in range(1, steps + 1):
        approver_id = _seed_user(db_session, tenant_id, APPROVER, name=f"Approver {step_number}")
        db_session.add(
            ApprovalMatrixStep(
                config_id=config.id, step_number=step_number, step_name=f"Level {step_number}",
                approver_user_id=approver_id, created_by=seed_id, updated_by=seed_id,
            )
        )
        approver_ids.append(approver_id)
    db_session.commit()
    return approver_ids


def _contract_status(db_session, contract_id) -> str:
    db_session.expire_all()
    return db_session.get(Contract, contract_id).status


def _status_log(db_session, contract_id) -> list[str]:
    rows = (
        db_session.query(ActivityLogEntry)
        .filter(ActivityLogEntry.contract_id == contract_id, ActivityLogEntry.action_type == "STATUS_CHANGE")
        .order_by(ActivityLogEntry.performed_at.asc())
        .all()
    )
    return [r.details for r in rows]


def _setup_analyzed_contract(db_client, db_session, **contract_overrides):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    legal_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    contract_id = _seed_contract(db_session, tenant_id, admin_id, owner_id, **contract_overrides)
    # UC5-BR-023 precondition: at least one completed AI clause analysis pass.
    db_client.get(f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id))
    return tenant_id, admin_id, owner_id, legal_id, contract_id


# ---- routing precondition + validation (UC5-BR-023, UC5-AF-001) ---------------------------


def test_routing_blocked_without_prior_clause_analysis(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    contract_id = _seed_contract(db_session, tenant_id, admin_id, owner_id)

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([owner_id]),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 409


def test_routing_blocked_without_any_reviewer(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([]),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 400
    assert "reviewer" in resp.json()["error"].lower()


def test_routing_disallowed_for_legal_reviewer(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([legal_id]),
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert resp.status_code == 403


def test_routing_happy_path_sets_with_internal(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([legal_id]),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["negotiationStatus"] == "With Internal"
    assert body["versionNumber"] == 1
    assert len(body["internalReviewers"]) == 1


def test_routing_moves_contract_to_in_negotiation_and_logs_it(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    assert _contract_status(db_session, contract_id) == "In Negotiation"
    assert _status_log(db_session, contract_id) == [
        "Status changed from Draft to In Negotiation: submitted for review"
    ]


def test_failed_routing_leaves_contract_in_draft(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([legal_id], externalPartyEmail="not-an-email"),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 400
    assert _contract_status(db_session, contract_id) == "Draft"
    assert _status_log(db_session, contract_id) == []


def test_routing_auto_adds_finance_head_above_threshold(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(
        db_client, db_session, contract_value=2_000_000
    )
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([legal_id]),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 200
    reviewers = resp.json()["internalReviewers"]
    assert any(r["reviewerName"] == "Finance Head" and r["isMandatory"] for r in reviewers)


def test_routing_blocked_when_already_routed(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([legal_id]),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([legal_id]),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 409


# ---- tracker + reviews (UC5-BR-007/019) ----------------------------------------------------


def _route(db_client, contract_id, owner_id, reviewer_ids, **overrides):
    return db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload(reviewer_ids, **overrides),
        headers=_headers(CONTRACT_OWNER, owner_id),
    ).json()


def test_tracker_not_found_before_routing(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    resp = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation", headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert resp.status_code == 404


def test_submit_review_transitions_to_with_counterparty_and_increments_version(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={"commentText": "Looks fine."},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["versionNumber"] == 2
    assert body["negotiationStatus"] == "With Counterparty"

    tracker = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation", headers=_headers(CONTRACT_OWNER, owner_id)
    ).json()
    assert tracker["negotiationStatus"] == "With Counterparty"
    assert len(tracker["versions"]) == 2
    assert len(tracker["comments"]) == 1


def test_submit_review_on_stale_version_conflicts_but_keeps_both_versions(db_client, db_session):
    """UC5: two reviewers redlining at once. The second submission is based on version 1,
    which is no longer the latest -- it is still saved as its own version (nothing is
    overwritten), but the reviewer is told to refresh and reapply."""
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    second_reviewer = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    _route(db_client, contract_id, owner_id, [legal_id, second_reviewer], routingType="Parallel")

    first = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={"redlineText": "Reviewer one's wording.", "expectedVersion": 1},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert first.status_code == 200
    assert first.json()["versionNumber"] == 2

    stale = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={"redlineText": "Reviewer two's wording.", "expectedVersion": 1},
        headers=_headers(LEGAL_REVIEWER, second_reviewer),
    )
    assert stale.status_code == 409
    assert stale.json()["error"] == (
        "A newer version was submitted while you were editing. "
        "Please refresh and reapply your changes."
    )

    tracker = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation", headers=_headers(CONTRACT_OWNER, owner_id)
    ).json()
    # Both redlines are on record, and the conflicted reviewer may still resubmit.
    assert tracker["versionNumber"] == 3
    assert {c["commentText"] for c in tracker["comments"]} == {
        "Reviewer one's wording.",
        "Reviewer two's wording.",
    }
    assert tracker["negotiationStatus"] == "With Internal"
    statuses = {r["reviewerId"]: r["reviewStatus"] for r in tracker["internalReviewers"]}
    assert statuses[str(legal_id)] == "Submitted"
    assert statuses[str(second_reviewer)] == "Pending"

    retry = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={"redlineText": "Reviewer two, reapplied.", "expectedVersion": 3},
        headers=_headers(LEGAL_REVIEWER, second_reviewer),
    )
    assert retry.status_code == 200
    assert retry.json()["negotiationStatus"] == "With Counterparty"


def test_submit_review_without_expected_version_is_accepted(db_client, db_session):
    """`expectedVersion` is optional -- a caller that does not send it is treated as being
    on the latest version, so the existing flow is unchanged."""
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={"commentText": "Fine by me."},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert resp.status_code == 200


def test_submit_review_rejects_non_assigned_reviewer(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    other_reviewer = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, other_reviewer),
    )
    assert resp.status_code == 403


# ---- external link + OTP flow (UC5-BR-005/016) ----------------------------------------------


def test_external_link_blocked_before_internal_review_completes(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/external-link",
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 409


def test_full_external_flow_round_trips_back_to_with_internal(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )

    link_resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/external-link",
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert link_resp.status_code == 200
    link = link_resp.json()
    token = link["linkToken"]
    otp = FIXED_OTP

    external_user_id = uuid.uuid4()

    wrong_otp = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp",
        json={"otp": "000000"},
        headers=_headers(EXTERNAL_PARTY, external_user_id),
    )
    assert wrong_otp.status_code == 200
    assert wrong_otp.json()["verified"] is False

    verify = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp",
        json={"otp": otp},
        headers=_headers(EXTERNAL_PARTY, external_user_id),
    )
    assert verify.status_code == 200
    assert verify.json()["verified"] is True
    assert verify.json()["negotiationData"]["versionNumber"] == 2

    submit = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{token}/submit",
        json={"redlineText": "Please change clause 3."},
        headers=_headers(EXTERNAL_PARTY, external_user_id),
    )
    assert submit.status_code == 200
    assert submit.json()["versionNumber"] == 3
    assert submit.json()["negotiationStatus"] == "With Internal"


def test_otp_locks_after_three_failed_attempts(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    link = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/external-link",
        headers=_headers(CONTRACT_OWNER, owner_id),
    ).json()
    token = link["linkToken"]
    external_user_id = uuid.uuid4()

    for _ in range(3):
        db_client.post(
            f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp",
            json={"otp": "000000"},
            headers=_headers(EXTERNAL_PARTY, external_user_id),
        )

    resp = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp",
        json={"otp": FIXED_OTP},
        headers=_headers(EXTERNAL_PARTY, external_user_id),
    )
    assert resp.status_code == 403


# ---- T-LIFECYCLE-NEGOTIATION-API scope: verify-otp / submit, no header auth (UC5-AF-002/003,
# UC5-BR-006/008/016/020) --------------------------------------------------------------------


def _generate_link(db_client, contract_id, owner_id, legal_id) -> dict:
    db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    return db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/external-link",
        headers=_headers(CONTRACT_OWNER, owner_id),
    ).json()


def test_verify_otp_requires_no_auth_headers(db_client, db_session):
    """UC5's endpoint contract marks verify-otp/submit `auth_required: no` -- the External
    Party has no X-User-Role/X-User-Id, only the link token and OTP."""
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    link = _generate_link(db_client, contract_id, owner_id, legal_id)

    resp = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{link['linkToken']}/verify-otp",
        json={"otp": FIXED_OTP},
    )
    assert resp.status_code == 200
    assert resp.json()["verified"] is True


def test_verify_otp_unknown_link_is_404(db_client, db_session):
    resp = db_client.post(
        "/api/v1/lifecycle/negotiation/external/does-not-exist/verify-otp",
        json={"otp": "123456"},
    )
    assert resp.status_code == 404


def test_verify_otp_third_failure_locks_with_exact_message(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    link = _generate_link(db_client, contract_id, owner_id, legal_id)
    token = link["linkToken"]

    for _ in range(2):
        resp = db_client.post(
            f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp", json={"otp": "000000"}
        )
        assert resp.status_code == 200
        assert resp.json()["verified"] is False

    third = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp", json={"otp": "000000"}
    )
    assert third.status_code == 403
    assert third.json()["error"] == "Invalid OTP. Link locked, please request a new link."


def test_verify_otp_reopening_locked_link_denies_access_with_no_fields(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    link = _generate_link(db_client, contract_id, owner_id, legal_id)
    token = link["linkToken"]
    for _ in range(3):
        db_client.post(f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp", json={"otp": "000000"})

    reopen = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp", json={"otp": FIXED_OTP}
    )
    assert reopen.status_code == 403
    assert "negotiationData" not in reopen.json()

    # UC5-AF-002: lockout does not affect the routing/reviewer configuration or Version Number.
    tracker = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation", headers=_headers(CONTRACT_OWNER, owner_id)
    ).json()
    assert tracker["versionNumber"] == 2
    assert tracker["negotiationStatus"] == "With Counterparty"


def test_external_submit_blocked_when_link_locked(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    link = _generate_link(db_client, contract_id, owner_id, legal_id)
    token = link["linkToken"]
    for _ in range(3):
        db_client.post(f"/api/v1/lifecycle/negotiation/external/{token}/verify-otp", json={"otp": "000000"})

    resp = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{token}/submit",
        json={"redlineText": "Please change clause 3."},
    )
    assert resp.status_code == 403

    tracker = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation", headers=_headers(CONTRACT_OWNER, owner_id)
    ).json()
    assert tracker["negotiationStatus"] == "With Counterparty"


def test_external_submit_requires_redline_text(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    link = _generate_link(db_client, contract_id, owner_id, legal_id)

    resp = db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{link['linkToken']}/submit",
        json={"redlineText": "   "},
    )
    assert resp.status_code == 400


def test_external_submit_unknown_link_is_404(db_client, db_session):
    resp = db_client.post(
        "/api/v1/lifecycle/negotiation/external/does-not-exist/submit",
        json={"redlineText": "x"},
    )
    assert resp.status_code == 404


# ---- compare versions (UC5-BR-012) -----------------------------------------------------------


def test_compare_versions_unknown_version_is_404(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])

    resp = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/compare",
        params={"versionA": 1, "versionB": 99},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 404


def test_compare_versions_happy_path(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    resp = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/compare",
        params={"versionA": 1, "versionB": 2},
        headers=_headers(APPROVER, _seed_user(db_session, tenant_id, APPROVER)),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["versionA"]["versionNumber"] == 1
    assert body["versionB"]["versionNumber"] == 2


# ---- reminder + mark agreed (UC5-AF-006, UC5-BR-021) -----------------------------------------


def test_reminder_blocked_when_not_overdue(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id], dueDate="2099-01-01")
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reminder",
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 409


def test_reminder_sent_when_overdue(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    _route(db_client, contract_id, owner_id, [legal_id], assignedDate="2020-01-01", dueDate=yesterday)
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reminder",
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 200
    assert resp.json()["reminderType"] == "Manual"


def test_mark_agreed_blocked_before_review_cycle_completes(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/mark-agreed",
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert resp.status_code == 409


def _review_and_mark_agreed(db_client, contract_id, legal_id):
    db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    return db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/mark-agreed",
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )


def test_mark_agreed_allowed_after_review_cycle(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _seed_approval_rule(db_session, tenant_id)
    _route(db_client, contract_id, owner_id, [legal_id])
    resp = _review_and_mark_agreed(db_client, contract_id, legal_id)
    assert resp.status_code == 200
    assert resp.json()["negotiationStatus"] == "Agreed"


def test_mark_agreed_moves_contract_to_pending_approval_and_opens_step_one(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    approver_ids = _seed_approval_rule(db_session, tenant_id, steps=2)
    _route(db_client, contract_id, owner_id, [legal_id])
    assert _review_and_mark_agreed(db_client, contract_id, legal_id).status_code == 200

    assert _contract_status(db_session, contract_id) == "Pending Approval"
    assert _status_log(db_session, contract_id)[-1] == (
        "Status changed from In Negotiation to Pending Approval: negotiation marked Agreed"
    )
    approvals = db_session.query(Approval).filter(Approval.contract_id == contract_id).all()
    assert len(approvals) == 1
    assert approvals[0].status == "PendingApproval"
    assert approvals[0].current_step_number == 1
    assert approvals[0].total_steps == 2

    # The Step 1 approver sees it in their Approvals list; the Step 2 approver does not yet.
    first = db_client.get("/api/v1/approvals", headers=_headers(APPROVER, approver_ids[0])).json()
    assert [i["contractId"] for i in first["items"]] == [str(contract_id)]
    second = db_client.get("/api/v1/approvals", headers=_headers(APPROVER, approver_ids[1])).json()
    assert second["items"] == []


def test_mark_agreed_without_matching_rule_keeps_contract_in_negotiation(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _seed_approval_rule(db_session, tenant_id, contract_type="MSA")  # does not match the NDA
    _route(db_client, contract_id, owner_id, [legal_id])
    resp = _review_and_mark_agreed(db_client, contract_id, legal_id)

    assert resp.status_code == 409
    assert resp.json()["error"] == (
        "No approval rule found for this contract type and value. Please contact your Tenant Admin."
    )
    assert _contract_status(db_session, contract_id) == "In Negotiation"
    tracker = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation", headers=_headers(LEGAL_REVIEWER, legal_id)
    ).json()
    assert tracker["negotiationStatus"] != "Agreed"
    assert db_session.query(Approval).filter(Approval.contract_id == contract_id).count() == 0


def test_mark_agreed_matches_settings_approval_rule(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    approver_id = _seed_user(db_session, tenant_id, APPROVER)
    seed_id = uuid.uuid4()
    # Settings > Routing & Approval rules key on Product/Service (the contract's industry).
    db_session.add(
        ApprovalMatrixRule(
            tenant_id=tenant_id, contract_type="Product", value_threshold=5000, approver_role="Approver",
            created_by=seed_id, updated_by=seed_id,
        )
    )
    db_session.add(
        ApprovalMatrixRule(
            tenant_id=tenant_id, contract_type="Product", value_threshold=50000, approver_role="Tenant Admin",
            created_by=seed_id, updated_by=seed_id,
        )
    )
    db_session.commit()
    _route(db_client, contract_id, owner_id, [legal_id])
    assert _review_and_mark_agreed(db_client, contract_id, legal_id).status_code == 200

    approval = db_session.query(Approval).filter(Approval.contract_id == contract_id).one()
    assert approval.total_steps == 1  # only the 5,000 threshold applies to a 10,000 contract
    listed = db_client.get("/api/v1/approvals", headers=_headers(APPROVER, approver_id)).json()
    assert [i["contractId"] for i in listed["items"]] == [str(contract_id)]


def test_sent_back_contract_can_be_resubmitted_and_gets_a_new_approval(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    (approver_id,) = _seed_approval_rule(db_session, tenant_id)
    _route(db_client, contract_id, owner_id, [legal_id])
    assert _review_and_mark_agreed(db_client, contract_id, legal_id).status_code == 200
    first_approval = db_session.query(Approval).filter(Approval.contract_id == contract_id).one()

    sent_back = db_client.post(
        f"/api/v1/approvals/{first_approval.id}/actions",
        json={"actionType": "SendBack", "comments": "Tighten the liability cap."},
        headers=_headers(APPROVER, approver_id),
    )
    assert sent_back.status_code == 200
    assert _contract_status(db_session, contract_id) == "In Negotiation"

    # REQ-1: a sent-back contract (already In Negotiation) can be sent for review again.
    resend = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/routing",
        json=_routing_payload([legal_id]),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resend.status_code == 200
    assert resend.json()["negotiationStatus"] == "With Internal"
    assert resend.json()["versionNumber"] > 1
    assert _contract_status(db_session, contract_id) == "In Negotiation"

    # REQ-2: agreeing again opens a new approval; the old one stays in history.
    assert _review_and_mark_agreed(db_client, contract_id, legal_id).status_code == 200
    assert _contract_status(db_session, contract_id) == "Pending Approval"
    approvals = {
        a.id: a.status for a in db_session.query(Approval).filter(Approval.contract_id == contract_id).all()
    }
    assert len(approvals) == 2
    assert approvals[first_approval.id] == "SentBack"
    assert sorted(approvals.values()) == ["PendingApproval", "SentBack"]


def test_mark_agreed_twice_is_rejected(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _seed_approval_rule(db_session, tenant_id)
    _route(db_client, contract_id, owner_id, [legal_id])
    assert _review_and_mark_agreed(db_client, contract_id, legal_id).status_code == 200
    again = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/mark-agreed",
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert again.status_code == 409
    assert db_session.query(Approval).filter(Approval.contract_id == contract_id).count() == 1


def test_mark_agreed_disallowed_for_contract_owner(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/mark-agreed",
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 403


# ---- comments (BR-6 style trail, UC5-FV-003) --------------------------------------------------


def test_add_comment_tied_to_current_version(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/comments",
        json={"commentText": "Please clarify clause 2."},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 200
    assert resp.json()["versionNumber"] == 1
    assert resp.json()["commentText"] == "Please clarify clause 2."


# ---- workflow participants can open their contracts ------------------------------------------


def test_linked_reviewer_and_approver_can_open_the_contract(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    (approver_id,) = _seed_approval_rule(db_session, tenant_id)
    unlinked_legal = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    _route(db_client, contract_id, owner_id, [legal_id])

    for path in (f"/api/v1/contracts/{contract_id}", f"/api/v1/contracts/{contract_id}/versions"):
        assert db_client.get(path, headers=_headers(LEGAL_REVIEWER, legal_id)).status_code == 200
        assert db_client.get(path, headers=_headers(LEGAL_REVIEWER, unlinked_legal)).status_code == 403
        # Not yet on an approval step.
        assert db_client.get(path, headers=_headers(APPROVER, approver_id)).status_code == 403

    assert _review_and_mark_agreed(db_client, contract_id, legal_id).status_code == 200
    resp = db_client.get(f"/api/v1/contracts/{contract_id}", headers=_headers(APPROVER, approver_id))
    assert resp.status_code == 200
    assert resp.json()["status"] == "Pending Approval"


# ---- the counterparty mail carries an openable link, like the signing mail -------------------


def test_counterparty_invite_mail_carries_the_review_url(db_client, db_session, caplog):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])
    db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )

    with caplog.at_level("INFO", logger="app.services.notifications"):
        link_resp = db_client.post(
            f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/external-link",
            headers=_headers(CONTRACT_OWNER, owner_id),
        )
    assert link_resp.status_code == 200
    token = link_resp.json()["linkToken"]

    # With no SMTP relay configured the log line IS the inbox.
    body = "\n".join(r.getMessage() for r in caplog.records)
    assert f"/negotiation/external/{token}" in body
    assert f"Secure link reference: {token}" in body
    assert f"One-time password: {FIXED_OTP}" in body


# ---- an already-routed contract keeps its way through to Negotiation ------------------------


def test_already_routed_contract_still_offers_proceed_to_negotiation(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    _route(db_client, contract_id, owner_id, [legal_id])

    analysis = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis",
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert analysis.status_code == 200
    assert analysis.json()["proceedToNegotiationEnabled"] is True

    # Proceeding again is a no-op that reports where the negotiation actually stands.
    proceed = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/proceed-to-negotiation",
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert proceed.status_code == 200
    assert proceed.json()["negotiationStatus"] == "With Internal"
    assert proceed.json()["routedAt"] is not None
