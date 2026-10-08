"""Exercises every endpoint this task owns (`/api/v1/contracts*`) against a real in-memory
database: the role matrix, tenant isolation, the permitted-access check on contract detail
(UC1-AF-006), and the Create validation chain named in TASK.md -- mandatory fields
(UC2-AF-001/FV-001/FV-002), template/third-party-paper mutual exclusivity (UC2-BR-008),
date ordering (UC2-AF-003/004, UC2-BR-006/007), Notice Period's conditional requirement
(UC2-BR-004), Contract Owner role validation (UC2-BR-003/012), and the Draft-only status
on save (UC2-BR-010/014/015).
"""
import uuid
from datetime import date, timedelta

from app.models.contract import Contract, ContractTask
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.template import Template
from app.models.user import User

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"
APPROVER = "APPROVER"
SIGNER = "SIGNER"


def _headers(role: str, user_id: uuid.UUID) -> dict:
    return {"X-User-Role": role, "X-User-Id": str(user_id)}


def _seed_tenant(db_session) -> uuid.UUID:
    tenant_id = uuid.uuid4()
    seed_id = uuid.uuid4()
    db_session.add(
        Tenant(
            id=tenant_id,
            name="Acme Co",
            high_risk_threshold=70,
            created_by=seed_id,
            updated_by=seed_id,
        )
    )
    db_session.commit()
    return tenant_id


def _seed_user(db_session, tenant_id: uuid.UUID, role: str, *, name: str | None = None) -> uuid.UUID:
    user_id = uuid.uuid4()
    label = name or f"{role.title()} User"
    db_session.add(
        User(
            id=user_id,
            tenant_id=tenant_id,
            name=label,
            email=f"{user_id}@acme.test",
            role=role,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()
    return user_id


def _seed_counterparty(db_session, tenant_id: uuid.UUID, admin_id: uuid.UUID) -> uuid.UUID:
    counterparty_id = uuid.uuid4()
    db_session.add(
        Counterparty(
            id=counterparty_id,
            tenant_id=tenant_id,
            name="Globex Contact",
            email="contact@globex.test",
            company="Globex Corp",
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()
    return counterparty_id


def _seed_template(db_session, tenant_id: uuid.UUID, admin_id: uuid.UUID, status: str = "Active") -> uuid.UUID:
    template_id = uuid.uuid4()
    db_session.add(
        Template(
            id=template_id,
            tenant_id=tenant_id,
            template_name="NDA Template",
            template_category="NDA",
            document_format="DOCX",
            template_body="Merge fields go here.",
            status=status,
            current_version=1,
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()
    return template_id


def _valid_payload(template_id: uuid.UUID, counterparty_id: uuid.UUID, owner_id: uuid.UUID, **overrides) -> dict:
    payload = {
        "contractType": "NDA",
        "industry": "Product",
        "templateId": str(template_id),
        "counterpartyId": str(counterparty_id),
        "contractOwnerId": str(owner_id),
        "contractValue": 10000.00,
        "currency": "USD",
        "startDate": "2026-11-01",
        "endDate": "2027-11-01",
        "renewalType": "None",
        "dueDate": "2026-12-01",
    }
    payload.update(overrides)
    return payload


def _setup_basic(db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    counterparty_id = _seed_counterparty(db_session, tenant_id, admin_id)
    template_id = _seed_template(db_session, tenant_id, admin_id)
    return tenant_id, admin_id, owner_id, counterparty_id, template_id


# ---- role / auth matrix -----------------------------------------------------------------


def test_missing_role_header_is_401(db_client):
    resp = db_client.get("/api/v1/contracts")
    assert resp.status_code == 401
    assert "error" in resp.json() and "details" in resp.json()


def test_list_disallowed_role_is_403(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    bad_user_id = _seed_user(db_session, tenant_id, "EXTERNAL_PARTY")
    resp = db_client.get("/api/v1/contracts", headers=_headers("EXTERNAL_PARTY", bad_user_id))
    assert resp.status_code == 403


def test_create_disallowed_for_signer(db_client, db_session):
    tenant_id, _admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    signer_id = _seed_user(db_session, tenant_id, SIGNER)
    resp = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(SIGNER, signer_id),
    )
    assert resp.status_code == 403


def test_malformed_contract_id_is_400(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.get("/api/v1/contracts/not-a-uuid", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 400


# ---- create happy path + Draft status (UC2-MF-001 / UC2-BR-010/014/015) ------------------


def test_create_contract_happy_path_returns_201_draft(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    resp = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 201
    assert "Location" in resp.headers
    body = resp.json()
    assert body["status"] == "Draft"
    assert body["contractType"] == "NDA"
    assert body["industry"] == "Product"
    assert body["counterpartyId"] == str(counterparty_id)
    assert body["counterpartyName"] == "Globex Contact"
    assert body["contractOwnerId"] == str(owner_id)
    assert body["templateId"] == str(template_id)
    assert body["currency"] == "USD"
    assert body["noticePeriod"] is None
    assert uuid.UUID(body["id"])
    assert resp.headers["Location"] == f"/api/v1/contracts/{body['id']}"


def test_create_contract_allowed_for_contract_owner(db_client, db_session):
    tenant_id, _admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    resp = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 201


def test_create_contract_with_new_counterparty(db_client, db_session):
    tenant_id, admin_id, owner_id, _counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(template_id, uuid.uuid4(), owner_id)
    payload.pop("counterpartyId")
    payload.update(
        {
            "counterpartySearch": "Initech",
            "counterpartyName": "Initech Contact",
            "counterpartyEmail": "contact@initech.test",
            "counterpartyCompany": "Initech LLC",
        }
    )
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["counterpartyName"] == "Initech Contact"
    assert body["counterpartyCompany"] == "Initech LLC"


# ---- mandatory-field / counterparty validation (UC2-AF-001, UC2-FV-001/002) --------------


def test_create_contract_missing_mandatory_scalar_field_is_400(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(template_id, counterparty_id, owner_id)
    payload.pop("currency")
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400


def test_create_contract_without_counterparty_selection_or_details_is_400(db_client, db_session):
    tenant_id, admin_id, owner_id, _counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(template_id, uuid.uuid4(), owner_id)
    payload.pop("counterpartyId")
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Please fill all mandatory fields"
    assert "Counterparty Search is required." in resp.json()["details"]
    assert "Counterparty Name is required." in resp.json()["details"]


def test_create_contract_invalid_new_counterparty_email_is_400(db_client, db_session):
    tenant_id, admin_id, owner_id, _counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(template_id, uuid.uuid4(), owner_id)
    payload.pop("counterpartyId")
    payload.update(
        {
            "counterpartySearch": "Initech",
            "counterpartyName": "Initech Contact",
            "counterpartyEmail": "not-an-email",
            "counterpartyCompany": "Initech LLC",
        }
    )
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Counterparty Email must be a valid email address."


def test_create_contract_unknown_counterparty_id_is_400(db_client, db_session):
    tenant_id, admin_id, owner_id, _counterparty_id, template_id = _setup_basic(db_session)
    resp = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, uuid.uuid4(), owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Counterparty not found."


# ---- template / third-party-paper mutual exclusivity (UC2-BR-008/011, UC2-AF-002) --------


def test_create_contract_requires_template_or_third_party_paper(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, _template_id = _setup_basic(db_session)
    payload = _valid_payload(uuid.uuid4(), counterparty_id, owner_id)
    payload.pop("templateId")
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Select a Template or upload a Third Party Paper."


def test_create_contract_blocks_template_and_third_party_paper_together(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(template_id, counterparty_id, owner_id)
    payload["thirdPartyPaperFileId"] = str(uuid.uuid4())
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Template and Upload Third Party Paper are mutually exclusive."


def test_create_contract_blocks_inactive_template(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, _template_id = _setup_basic(db_session)
    inactive_template_id = _seed_template(db_session, tenant_id, admin_id, status="Draft")
    resp = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(inactive_template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == (
        "No active templates available for this combination. Please upload third party paper."
    )


# ---- Contract Owner role validation (UC2-BR-003/012) --------------------------------------


def test_create_contract_blocks_non_contract_owner_as_owner(db_client, db_session):
    tenant_id, admin_id, _owner_id, counterparty_id, template_id = _setup_basic(db_session)
    legal_reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)
    resp = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, legal_reviewer_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 400
    assert "Contract Owner" in resp.json()["error"]


def test_create_contract_blocks_owner_from_other_tenant(db_client, db_session):
    tenant_id, admin_id, _owner_id, counterparty_id, template_id = _setup_basic(db_session)
    other_tenant_id = _seed_tenant(db_session)
    other_owner_id = _seed_user(db_session, other_tenant_id, CONTRACT_OWNER)
    resp = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, other_owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 400


# ---- date validation (UC2-AF-003/004, UC2-BR-005/006/007) ---------------------------------


def test_create_contract_blocks_end_date_earlier_than_start_date(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(
        template_id, counterparty_id, owner_id, startDate="2026-11-10", endDate="2026-11-01"
    )
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "End date cannot be earlier than start date"


def test_create_contract_blocks_end_date_equal_to_start_date(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(
        template_id, counterparty_id, owner_id, startDate="2026-11-10", endDate="2026-11-10"
    )
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "End date must be later than start date"


def test_create_contract_blocks_due_date_earlier_than_assigned_date(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    payload = _valid_payload(template_id, counterparty_id, owner_id, dueDate=yesterday)
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Due date cannot be earlier than assigned date"


# ---- Notice Period conditional requirement (UC2-BR-004) ------------------------------------


def test_create_contract_requires_notice_period_when_renewal_type_auto(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(template_id, counterparty_id, owner_id, renewalType="Auto")
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "Please fill all mandatory fields"


def test_create_contract_accepts_notice_period_when_renewal_type_manual(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(
        template_id, counterparty_id, owner_id, renewalType="Manual", noticePeriod=30
    )
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 201
    assert resp.json()["noticePeriod"] == 30


def test_create_contract_clears_notice_period_when_renewal_type_none(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    payload = _valid_payload(
        template_id, counterparty_id, owner_id, renewalType="None", noticePeriod=30
    )
    resp = db_client.post(
        "/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 201
    assert resp.json()["noticePeriod"] is None


# ---- list: tenant isolation, filters, paging ------------------------------------------------


def test_list_contracts_scoped_to_tenant(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    )

    other_tenant_id, other_admin_id, other_owner_id, other_cp_id, other_tpl_id = _setup_basic(
        db_session
    )
    db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(other_tpl_id, other_cp_id, other_owner_id),
        headers=_headers(TENANT_ADMIN, other_admin_id),
    )

    resp = db_client.get("/api/v1/contracts", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalCount"] == 1
    assert len(body["items"]) == 1


def test_list_contracts_filters_by_status(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    resp = db_client.get(
        "/api/v1/contracts", params={"status": "Executed"}, headers=_headers(TENANT_ADMIN, admin_id)
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["totalCount"] == 0
    assert body["noMatchMessage"] is not None


def test_list_contracts_paging(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    for _ in range(3):
        db_client.post(
            "/api/v1/contracts",
            json=_valid_payload(template_id, counterparty_id, owner_id),
            headers=_headers(TENANT_ADMIN, admin_id),
        )
    resp = db_client.get(
        "/api/v1/contracts",
        params={"page": 1, "pageSize": 2},
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    body = resp.json()
    assert body["totalCount"] == 3
    assert len(body["items"]) == 2
    assert body["page"] == 1
    assert body["pageSize"] == 2


# ---- detail: permitted-access check (UC1-AF-006) --------------------------------------------


def test_get_contract_detail_not_found_is_404(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)
    resp = db_client.get(f"/api/v1/contracts/{uuid.uuid4()}", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 404


def test_tenant_admin_can_access_any_contract(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    created = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    ).json()
    resp = db_client.get(f"/api/v1/contracts/{created['id']}", headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 200


def test_contract_owner_can_access_own_contract(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    created = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    ).json()
    resp = db_client.get(f"/api/v1/contracts/{created['id']}", headers=_headers(CONTRACT_OWNER, owner_id))
    assert resp.status_code == 200


def test_contract_owner_blocked_from_contract_they_do_not_own(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    other_owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    created = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    ).json()
    resp = db_client.get(
        f"/api/v1/contracts/{created['id']}", headers=_headers(CONTRACT_OWNER, other_owner_id)
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "You do not have access to this contract"


def test_approver_blocked_without_assignment(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    approver_id = _seed_user(db_session, tenant_id, APPROVER)
    created = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    ).json()
    resp = db_client.get(
        f"/api/v1/contracts/{created['id']}", headers=_headers(APPROVER, approver_id)
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "You do not have access to this contract"


def test_approver_allowed_when_assigned_current_task(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    approver_id = _seed_user(db_session, tenant_id, APPROVER)
    created = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    ).json()
    db_session.add(
        ContractTask(
            id=uuid.uuid4(),
            contract_id=uuid.UUID(created["id"]),
            assignee_user_id=approver_id,
            assignment_role="APPROVER",
            due_date=date(2026, 12, 1),
            is_current=True,
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()

    resp = db_client.get(
        f"/api/v1/contracts/{created['id']}", headers=_headers(APPROVER, approver_id)
    )
    assert resp.status_code == 200
