"""Exercises every endpoint this task owns under `/api/v1/lifecycle/contracts/{id}/...`
(excluding negotiation, see test_lifecycle_negotiation.py): the role matrix, lazy AI Clause
Analysis extraction and mandatory-clause detection (UC4-BR-002), the Overall Contract Risk
Score rollup (UC4-BR-001), Accept/Edit/Reject transitions and their audit trail
(UC4-BR-006/014/015), optimistic concurrency on Edit (UC4-AF-004), metadata relabelling
(UC4-BR-007), the Ask AI empty-question guard and disclaimer (UC4-AF-005, UC4-BR-008), and
the Proceed to Negotiation mandatory-clause gate (UC4-BR-005, UC4-AF-006).
"""
import uuid
from datetime import date

from app.models.clause import Clause as LibraryClause
from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.template import Template
from app.models.user import User

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
APPROVER = "APPROVER"
EXTERNAL_PARTY = "EXTERNAL_PARTY"


def _headers(role: str, user_id: uuid.UUID) -> dict:
    return {"X-User-Role": role, "X-User-Id": str(user_id)}


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
            id=user_id,
            tenant_id=tenant_id,
            name=name or f"{role.title()} User",
            email=f"{user_id}@acme.test",
            role=role,
            created_by=user_id,
            updated_by=user_id,
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
        id=contract_id,
        tenant_id=tenant_id,
        contract_name="NDA with Globex",
        contract_type="NDA",
        industry="Product",
        template_id=template_id,
        counterparty_id=counterparty_id,
        contract_owner_id=owner_id,
        contract_value=10000,
        currency="USD",
        start_date=date(2026, 1, 1),
        end_date=date(2027, 1, 1),
        renewal_type="None",
        assigned_date=date(2026, 1, 1),
        due_date=date(2026, 2, 1),
        status="Draft",
        created_by=admin_id,
        updated_by=admin_id,
    )
    defaults.update(overrides)
    db_session.add(Contract(**defaults))
    db_session.commit()
    return contract_id


def _seed_mandatory_library_clause(db_session, tenant_id: uuid.UUID, admin_id: uuid.UUID, category: str) -> uuid.UUID:
    clause_id = uuid.uuid4()
    db_session.add(
        LibraryClause(
            id=clause_id,
            tenant_id=tenant_id,
            clause_name=f"{category} Clause",
            clause_category=category,
            standard_text="Standard wording.",
            risk_level="Medium",
            mandatory=True,
            status="Active",
            current_version=1,
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()
    return clause_id


def _setup(db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    legal_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    contract_id = _seed_contract(db_session, tenant_id, admin_id, owner_id)
    return tenant_id, admin_id, owner_id, legal_id, contract_id


# ---- auth matrix -------------------------------------------------------------------------


def test_missing_role_header_is_401(db_client):
    resp = db_client.get(f"/api/v1/lifecycle/contracts/{uuid.uuid4()}/clause-analysis")
    assert resp.status_code == 401


def test_disallowed_role_is_403(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    approver_id = _seed_user(db_session, tenant_id, APPROVER)
    resp = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(APPROVER, approver_id)
    )
    assert resp.status_code == 403


def test_contract_owner_cannot_edit_clause_text(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    resp = db_client.put(
        f"/api/v1/lifecycle/contracts/{contract_id}/clauses/{uuid.uuid4()}",
        json={"clauseText": "x", "expectedVersion": 1},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 403


# ---- clause analysis: extraction + risk rollup (UC4-BR-001/002) ---------------------------


def test_clause_analysis_not_found_is_404(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    resp = db_client.get(
        f"/api/v1/lifecycle/contracts/{uuid.uuid4()}/clause-analysis", headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 404


def test_clause_analysis_defaults_to_low_risk_with_no_mandatory_clauses(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    resp = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["contractId"] == str(contract_id)
    assert body["fileFormatSupported"] is True
    assert body["overallContractRiskScore"] == "Low"
    assert body["clauses"] == []
    assert body["proceedToNegotiationEnabled"] is True
    assert body["metadata"]["partiesLabel"] == "AI-suggested"


def test_clause_analysis_flags_missing_mandatory_clause(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    _seed_mandatory_library_clause(db_session, tenant_id, admin_id, "Confidentiality")

    resp = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["clauses"]) == 1
    clause = body["clauses"][0]
    assert clause["libraryMatchStatus"] == "Missing"
    assert clause["mandatoryClauseFlag"] is True
    assert clause["mandatoryClauseFlagLabel"] == "Mandatory clause missing"
    assert body["overallContractRiskScore"] == "High"
    assert body["proceedToNegotiationEnabled"] is False


def test_retry_extraction_is_idempotent(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    _seed_mandatory_library_clause(db_session, tenant_id, admin_id, "Liability")
    db_client.get(f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id))
    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/retry-extraction", headers=_headers(LEGAL_REVIEWER, legal_id)
    )
    assert resp.status_code == 200
    assert len(resp.json()["clauses"]) == 1


# ---- proceed to negotiation gate (UC4-BR-005/AF-006) --------------------------------------


def test_proceed_to_negotiation_blocked_when_mandatory_clause_missing(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    _seed_mandatory_library_clause(db_session, tenant_id, admin_id, "Termination")
    db_client.get(f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id))

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/proceed-to-negotiation", headers=_headers(LEGAL_REVIEWER, legal_id)
    )
    assert resp.status_code == 409
    assert "mandatory" in resp.json()["error"].lower()


def test_proceed_to_negotiation_allowed_once_resolved(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    _seed_mandatory_library_clause(db_session, tenant_id, admin_id, "Termination")
    analysis = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id)
    ).json()
    clause_id = analysis["clauses"][0]["clauseId"]

    edit_resp = db_client.put(
        f"/api/v1/lifecycle/contracts/{contract_id}/clauses/{clause_id}",
        json={"clauseText": "Replacement termination clause.", "expectedVersion": 1},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert edit_resp.status_code == 200
    assert edit_resp.json()["status"] == "Edited (Manual)"
    assert edit_resp.json()["mandatoryClauseFlag"] is False

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/proceed-to-negotiation", headers=_headers(LEGAL_REVIEWER, legal_id)
    )
    assert resp.status_code == 200
    assert resp.json()["negotiationStatus"] == "Ready for Negotiation"


# ---- edit: concurrency conflict (UC4-AF-004) ------------------------------------------------


def test_edit_clause_stale_version_is_409(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    _seed_mandatory_library_clause(db_session, tenant_id, admin_id, "IP")
    analysis = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id)
    ).json()
    clause_id = analysis["clauses"][0]["clauseId"]

    resp = db_client.put(
        f"/api/v1/lifecycle/contracts/{contract_id}/clauses/{clause_id}",
        json={"clauseText": "New text", "expectedVersion": 99},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert resp.status_code == 409
    assert "refresh" in resp.json()["error"].lower()


def test_edit_clause_not_found_is_404(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    resp = db_client.put(
        f"/api/v1/lifecycle/contracts/{contract_id}/clauses/{uuid.uuid4()}",
        json={"clauseText": "New text", "expectedVersion": 1},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert resp.status_code == 404


# ---- reject (UC4-BR-006 audit trail) --------------------------------------------------------


def test_reject_clause_logs_audit_entry(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    _seed_mandatory_library_clause(db_session, tenant_id, admin_id, "Payment")
    analysis = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id)
    ).json()
    clause_id = analysis["clauses"][0]["clauseId"]

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/clauses/{clause_id}/reject",
        json={"reason": "Not applicable"},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "Rejected"

    audit_resp = db_client.get(
        f"/api/v1/lifecycle/contracts/{contract_id}/audit-log", headers=_headers(LEGAL_REVIEWER, legal_id)
    )
    assert audit_resp.status_code == 200
    body = audit_resp.json()
    assert body["totalCount"] == 1
    assert body["items"][0]["actionType"] == "Reject"
    assert body["items"][0]["clauseId"] == clause_id


# ---- metadata relabelling (UC4-BR-007) ------------------------------------------------------


def test_update_metadata_relabels_only_edited_fields(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    db_client.get(f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id))

    resp = db_client.put(
        f"/api/v1/lifecycle/contracts/{contract_id}/metadata",
        json={"parties": "Acme and Globex"},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["parties"] == "Acme and Globex"
    assert body["partiesLabel"] == "User-confirmed"
    assert body["contractValueLabel"] == "AI-suggested"


# ---- ask ai (UC4-AF-005, UC4-BR-008) ---------------------------------------------------------


def test_ask_ai_blocks_empty_question(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    db_client.get(f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id))

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/ask-ai",
        json={"question": "   "},
        headers=_headers(LEGAL_REVIEWER, legal_id),
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Please enter a question before submitting."


def test_ask_ai_returns_disclaimer(db_client, db_session):
    tenant_id, admin_id, owner_id, legal_id, contract_id = _setup(db_session)
    db_client.get(f"/api/v1/lifecycle/contracts/{contract_id}/clause-analysis", headers=_headers(LEGAL_REVIEWER, legal_id))

    resp = db_client.post(
        f"/api/v1/lifecycle/contracts/{contract_id}/ask-ai",
        json={"question": "What is the termination clause?"},
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 200
    assert resp.json()["disclaimer"] == "AI suggestion only — verify before relying on this answer."
