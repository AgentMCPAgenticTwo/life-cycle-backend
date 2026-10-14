"""Exercises `POST /api/v1/tracker/export` (T-TRACKER-EXPORT-API): the role matrix,
tab/format/Period/Date-Range validation (UC10-FV-001), the empty-tenant export-unavailable
tier (UC10-AF-001), the no-records-still-exports tier (UC10-AF-003), and role-scoped
visibility (UC10-BR-005/009).
"""
import io
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.tenant import Tenant
from app.models.tracker import ContractOwner
from app.models.user import User
from tests.conftest import auth_headers

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
EXTERNAL_PARTY = "EXTERNAL_PARTY"


@pytest.fixture(autouse=True)
def _export_dir(tmp_path):
    """Generated export files go to a per-test temp directory, not the repo's var/exports."""
    original = settings.export_storage_dir
    settings.export_storage_dir = str(tmp_path / "exports")
    yield
    settings.export_storage_dir = original


def _seed_tenant_and_user(db_session, role: str, tenant_id: uuid.UUID | None = None) -> tuple[uuid.UUID, uuid.UUID]:
    is_new_tenant = tenant_id is None
    tenant_id = tenant_id or uuid.uuid4()
    user_id = uuid.uuid4()
    if is_new_tenant:
        db_session.add(
            Tenant(id=tenant_id, name="Acme Co", high_risk_threshold=70, created_by=user_id, updated_by=user_id)
        )
    db_session.add(
        User(
            id=user_id,
            tenant_id=tenant_id,
            name=f"{role.title()} User",
            email=f"{role.lower()}-{user_id}@acme.test",
            role=role,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()
    return tenant_id, user_id


def _headers(role: str, user_id: uuid.UUID) -> dict:
    return auth_headers(role, user_id)


def _seed_contract(
    db_session,
    tenant_id: uuid.UUID,
    actor_id: uuid.UUID,
    *,
    name: str = "MSA with Globex",
    contract_type: str = "MSA",
    status: str = "Draft",
    owner_id: uuid.UUID | None = None,
) -> Contract:
    counterparty = Counterparty(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        name="Globex",
        email=f"globex-{uuid.uuid4()}@example.test",
        company="Globex Corp",
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(counterparty)
    db_session.flush()

    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        contract_name=name,
        contract_type=contract_type,
        industry="Technology",
        counterparty_id=counterparty.id,
        contract_owner_id=owner_id or actor_id,
        owner_id=owner_id or actor_id,
        contract_value=1000,
        currency="USD",
        renewal_type="Manual",
        assigned_date=datetime.now(timezone.utc).date(),
        due_date=datetime.now(timezone.utc).date(),
        status=status,
        created_by=actor_id,
        updated_by=actor_id,
    )
    db_session.add(contract)
    db_session.commit()
    return contract


def _seed_owner_role(db_session, tenant_id, contract_id, user_id, role, actor_id) -> None:
    db_session.add(
        ContractOwner(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            contract_id=contract_id,
            user_id=user_id,
            role=role,
            created_by=actor_id,
            updated_by=actor_id,
        )
    )
    db_session.commit()


def _body(**overrides) -> dict:
    payload = {"tab": "Bottleneck", "format": "Excel", "period": "Monthly"}
    payload.update(overrides)
    return payload


def test_requires_role_header(db_client):
    response = db_client.post("/api/v1/tracker/export", json=_body())
    assert response.status_code == 401


def test_rejects_disallowed_role(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, EXTERNAL_PARTY)
    response = db_client.post("/api/v1/tracker/export", json=_body(), headers=_headers(EXTERNAL_PARTY, user_id))
    assert response.status_code == 403


def test_invalid_tab_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/tracker/export", json=_body(tab="Overview"), headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400
    assert "Tab must be one of: Ownership, CycleTime, Bottleneck, Turnaround." in response.json()["details"]


def test_invalid_format_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/tracker/export", json=_body(format="Word"), headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400
    assert "Format must be one of: Excel, PDF." in response.json()["details"]


def test_missing_period_without_date_range_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/tracker/export", json=_body(period=None), headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 400
    assert "Period selection is required." in response.json()["details"]


def test_date_range_from_not_earlier_than_to_is_validation_error(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post(
        "/api/v1/tracker/export",
        json=_body(period=None, dateRangeFrom="2026-01-10", dateRangeTo="2026-01-01"),
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 400
    assert "Date Range From must be earlier than Date Range To." in response.json()["details"]


def test_empty_tenant_export_is_unavailable(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    response = db_client.post("/api/v1/tracker/export", json=_body(), headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["fileUrl"] is None
    assert body["failureMessage"] == "No contract data available to display."


def test_no_records_for_period_still_succeeds(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _seed_contract(db_session, tenant_id, user_id)

    far_past_from = (datetime.now(timezone.utc) - timedelta(days=400)).date().isoformat()
    far_past_to = (datetime.now(timezone.utc) - timedelta(days=390)).date().isoformat()
    response = db_client.post(
        "/api/v1/tracker/export",
        json=_body(tab="Ownership", period=None, dateRangeFrom=far_past_from, dateRangeTo=far_past_to),
        headers=_headers(TENANT_ADMIN, user_id),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["fileUrl"] is not None


def test_happy_path_bottleneck_export_excel(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    contract = _seed_contract(db_session, tenant_id, user_id)
    from app.models.tracker import ContractLifecycleStageHistory

    db_session.add(
        ContractLifecycleStageHistory(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            contract_id=contract.id,
            stage="Drafting",
            stage_start_date=datetime.now(timezone.utc) - timedelta(days=1),
            stage_end_date=None,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()

    response = db_client.post(
        "/api/v1/tracker/export", json=_body(tab="Bottleneck", format="Excel"), headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["failureMessage"] is None
    assert body["fileUrl"].startswith("/api/v1/tracker/exports/")

    # The URL serves a real .xlsx (a zip of SpreadsheetML parts), not a placeholder.
    download = db_client.get(body["fileUrl"], headers=_headers(TENANT_ADMIN, user_id))
    assert download.status_code == 200
    assert download.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert download.content[:2] == b"PK"
    sheet = zipfile.ZipFile(io.BytesIO(download.content)).read("xl/worksheets/sheet1.xml").decode()
    assert "Current Stage" in sheet  # the Bottleneck tab's columns
    assert "Drafting" in sheet  # the seeded contract's current stage


def test_happy_path_turnaround_export_pdf(db_client, db_session):
    tenant_id, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _seed_contract(db_session, tenant_id, user_id)

    response = db_client.post(
        "/api/v1/tracker/export", json=_body(tab="Turnaround", format="PDF"), headers=_headers(TENANT_ADMIN, user_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["fileUrl"].startswith("/api/v1/tracker/exports/")

    # The URL serves a real PDF whose text stream carries the Turnaround tab's columns.
    download = db_client.get(body["fileUrl"], headers=_headers(TENANT_ADMIN, user_id))
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/pdf")
    assert download.content.startswith(b"%PDF-")
    assert download.content.rstrip().endswith(b"%%EOF")
    assert b"Estimated Turnaround" in download.content


def test_download_unknown_export_file_is_404(db_client, db_session):
    _, user_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)

    response = db_client.get(f"/api/v1/tracker/exports/{uuid.uuid4()}", headers=_headers(TENANT_ADMIN, user_id))
    assert response.status_code == 404


def test_contract_owner_export_scoped_to_owned_contracts(db_client, db_session):
    tenant_id, admin_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _, owner_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER, tenant_id)
    contract = _seed_contract(db_session, tenant_id, admin_id)
    _seed_owner_role(db_session, tenant_id, contract.id, owner_id, "CONTRACT_OWNER", admin_id)

    response = db_client.post(
        "/api/v1/tracker/export", json=_body(tab="Ownership"), headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert response.status_code == 200
    assert response.json()["success"] is True


def test_contract_owner_with_no_owned_contracts_export_unavailable(db_client, db_session):
    tenant_id, admin_id = _seed_tenant_and_user(db_session, TENANT_ADMIN)
    _, owner_id = _seed_tenant_and_user(db_session, CONTRACT_OWNER, tenant_id)
    _seed_contract(db_session, tenant_id, admin_id)

    response = db_client.post(
        "/api/v1/tracker/export", json=_body(tab="Ownership"), headers=_headers(CONTRACT_OWNER, owner_id)
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is False
    assert body["failureMessage"] == "No contract data available to display."
