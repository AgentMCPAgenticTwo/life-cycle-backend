"""Exercises the one endpoint this task owns, `POST /api/v1/contracts/third-party-paper`,
against a real in-memory database: the role matrix (401/403), the happy path (201,
FileUploadResponse field-by-field), unsupported file format (UC2-AF-005), oversized file
(UC2-AF-006), and the recovery path where a corrected re-upload succeeds.
"""
import base64
import uuid

from app.models.tenant import Tenant
from app.models.user import User

TENANT_ADMIN = "TENANT_ADMIN"
CONTRACT_OWNER = "CONTRACT_OWNER"
LEGAL_REVIEWER = "LEGAL_REVIEWER"

_CONTENT_B64 = base64.b64encode(b"%PDF-1.4 fake contents").decode()


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


def _seed_user(db_session, tenant_id: uuid.UUID, role: str) -> uuid.UUID:
    user_id = uuid.uuid4()
    db_session.add(
        User(
            id=user_id,
            tenant_id=tenant_id,
            name=f"{role.title()} User",
            email=f"{user_id}@acme.test",
            role=role,
            created_by=user_id,
            updated_by=user_id,
        )
    )
    db_session.commit()
    return user_id


def _payload(**overrides) -> dict:
    payload = {
        "fileName": "msa-draft.pdf",
        "fileContentBase64": _CONTENT_B64,
        "fileSize": 1024,
        "fileFormat": "PDF",
    }
    payload.update(overrides)
    return payload


def test_missing_role_header_is_401(db_client):
    resp = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(),
        headers={"X-User-Id": str(uuid.uuid4())},
    )
    assert resp.status_code == 401


def test_disallowed_role_is_403(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    reviewer_id = _seed_user(db_session, tenant_id, LEGAL_REVIEWER)

    resp = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(),
        headers=_headers(LEGAL_REVIEWER, reviewer_id),
    )
    assert resp.status_code == 403


def test_contract_owner_upload_happy_path(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)

    resp = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(fileName="agreement.docx", fileFormat="DOCX", fileSize=2048),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )

    assert resp.status_code == 201
    body = resp.json()
    assert set(body.keys()) == {"fileId", "fileName", "fileSize", "fileFormat", "storageUrl"}
    uuid.UUID(body["fileId"])  # must be a UUID, not a human-readable key
    assert body["fileName"] == "agreement.docx"
    assert body["fileSize"] == 2048
    assert body["fileFormat"] == "DOCX"
    assert isinstance(body["storageUrl"], str) and body["storageUrl"]


def test_tenant_admin_can_upload(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    admin_id = _seed_user(db_session, tenant_id, TENANT_ADMIN)

    resp = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 201


def test_unsupported_file_format_is_rejected(db_client, db_session):
    # UC2-AF-005: exact message for a non-PDF/DOCX format.
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)

    resp = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(fileName="notes.txt", fileFormat="TXT"),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "Unsupported file format. Please upload PDF or DOCX only."


def test_oversized_file_is_rejected(db_client, db_session):
    # UC2-AF-006: exact message for a file over the 25 MB limit.
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)

    resp = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(fileSize=25 * 1024 * 1024 + 1),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )

    assert resp.status_code == 400
    body = resp.json()
    assert body["error"] == "File size exceeds the 25 MB limit. Please upload a smaller file."


def test_file_at_exactly_25mb_is_accepted(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)

    resp = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(fileSize=25 * 1024 * 1024),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 201


def test_corrected_reupload_after_format_error_succeeds(db_client, db_session):
    # UC2-AF-005: re-selecting with a supported format clears the error and succeeds.
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)
    headers = _headers(CONTRACT_OWNER, owner_id)

    rejected = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(fileName="notes.exe", fileFormat="EXE"),
        headers=headers,
    )
    assert rejected.status_code == 400

    accepted = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(fileName="notes.pdf", fileFormat="PDF"),
        headers=headers,
    )
    assert accepted.status_code == 201


def test_invalid_base64_content_is_rejected(db_client, db_session):
    tenant_id = _seed_tenant(db_session)
    owner_id = _seed_user(db_session, tenant_id, CONTRACT_OWNER)

    resp = db_client.post(
        "/api/v1/contracts/third-party-paper",
        json=_payload(fileContentBase64="not-valid-base64!!!"),
        headers=_headers(CONTRACT_OWNER, owner_id),
    )
    assert resp.status_code == 400
