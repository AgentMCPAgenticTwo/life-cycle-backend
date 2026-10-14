"""UC5: re-check risk after external changes.

Only the clauses the counterparty actually changed are re-scored, the overall contract score
follows from them, Compare Versions shows the redline diff with `source` spelled
`Internal`/`External`, and a failed AI pass still leaves the submitted version saved and
retryable.
"""
import uuid

from app.models.lifecycle_clause import ContractClause
from tests.test_lifecycle_negotiation import (
    CONTRACT_OWNER,
    LEGAL_REVIEWER,
    _headers,
    _route,
    _setup_analyzed_contract,
)


def _seed_clause(db_session, contract_id, user_id, text, *, category, risk="Low"):
    clause_id = uuid.uuid4()
    db_session.add(
        ContractClause(
            id=clause_id,
            contract_id=contract_id,
            clause_category=category,
            library_match_status="Matched",
            risk_score=risk,
            clause_text=text,
            status="Accepted",
            is_mandatory=False,
            mandatory_flag_cleared=False,
            version=1,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()
    return clause_id


def _external_link(db_client, contract_id, owner_id, legal_id):
    _route(db_client, contract_id, owner_id, [legal_id])
    db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/reviews",
        json={},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    return db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/external-link",
        headers=_headers(CONTRACT_OWNER, owner_id),
    ).json()


def _submit(db_client, token, clause_id, new_text):
    return db_client.post(
        f"/api/v1/lifecycle/negotiation/external/{token}/submit",
        json={
            "redlineText": "See attached redline.",
            "clauseRedlines": [{"clauseId": str(clause_id), "clauseText": new_text}],
        },
    )


def test_external_redline_rescores_only_changed_clauses(db_client, db_session):
    _tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    changed_id = _seed_clause(
        db_session, contract_id, admin_id, "Liability is capped at fees paid.", category="Liability"
    )
    untouched_id = _seed_clause(
        db_session, contract_id, admin_id, "Notices are sent by email.", category="Notices"
    )
    link = _external_link(db_client, contract_id, owner_id, legal_id)

    assert _submit(db_client, link["linkToken"], changed_id, "Supplier accepts unlimited liability.").status_code == 200

    analysis = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis",
        headers=_headers(CONTRACT_OWNER, owner_id),
    ).json()
    assert analysis["analysisStatus"] == "Completed"
    by_id = {c["clauseId"]: c for c in analysis["clauses"]}
    assert by_id[str(changed_id)]["riskScore"] == "High"
    assert by_id[str(changed_id)]["clauseText"] == "Supplier accepts unlimited liability."
    # The untouched clause keeps its original score and explanation.
    assert by_id[str(untouched_id)]["riskScore"] == "Low"
    assert by_id[str(untouched_id)]["aiExplanation"] is None
    # The overall score follows the re-scored clause.
    assert analysis["overallContractRiskScore"] == "High"


def test_compare_versions_exposes_the_external_redline_diff(db_client, db_session):
    _tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    clause_id = _seed_clause(db_session, contract_id, admin_id, "Original payment terms.", category="Payment")
    link = _external_link(db_client, contract_id, owner_id, legal_id)
    submitted = _submit(db_client, link["linkToken"], clause_id, "Revised payment terms.").json()

    compare = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation/compare",
        params={"versionA": submitted["versionNumber"] - 1, "versionB": submitted["versionNumber"]},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert compare.status_code == 200
    body = compare.json()
    assert body["versionA"]["source"] == "Internal"
    assert body["versionB"]["source"] == "External"
    diff = next(d for d in body["differences"] if d["clauseId"] == str(clause_id))
    assert diff["textA"] == "Original payment terms."
    assert diff["textB"] == "Revised payment terms."


def test_failed_reanalysis_keeps_version_and_allows_retry(db_client, db_session, monkeypatch):
    from app.services import lifecycle_clauses as clause_service

    _tenant_id, admin_id, owner_id, legal_id, contract_id = _setup_analyzed_contract(db_client, db_session)
    clause_id = _seed_clause(db_session, contract_id, admin_id, "Original indemnity wording.", category="Indemnity")
    link = _external_link(db_client, contract_id, owner_id, legal_id)

    def _boom(_text):
        raise RuntimeError("AI unavailable")

    monkeypatch.setattr(clause_service, "_score_clause_text", _boom)
    submit = _submit(db_client, link["linkToken"], clause_id, "Supplier indemnifies the buyer.")
    # The version is still saved even though the re-analysis failed.
    assert submit.status_code == 200
    saved_version = submit.json()["versionNumber"]

    failed = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis",
        headers=_headers(CONTRACT_OWNER, owner_id),
    ).json()
    assert failed["analysisStatus"] == "Failed"
    assert failed["proceedToNegotiationEnabled"] is False

    monkeypatch.undo()
    retried = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/retry-extraction",
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert retried.status_code == 200
    body = retried.json()
    assert body["analysisStatus"] == "Completed"
    assert next(c for c in body["clauses"] if c["clauseId"] == str(clause_id))["riskScore"] == "High"

    # The saved version is untouched by the failure/retry cycle.
    tracker = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/negotiation",
        headers=_headers(CONTRACT_OWNER, owner_id),
    ).json()
    assert tracker["versionNumber"] == saved_version
