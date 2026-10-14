"""UC2 document generation: saving a contract produces its Version 1 document.

A Template contract gets a merged document; a Third Party Paper contract gets the uploaded
file as Version 1 with no merge. Both answer with UC2's confirmation message.
"""
import uuid

from app.models.contract_lifecycle import ContractDocument, ContractVersion
from app.models.uploaded_file import UploadedFile
from app.services.contract_documents import CREATED_MESSAGE, merge_template_body
from tests.test_contracts import (
    TENANT_ADMIN,
    _headers,
    _setup_basic,
    _valid_payload,
)


def _documents(db_session, contract_id):
    return (
        db_session.query(ContractDocument)
        .filter(ContractDocument.contract_id == uuid.UUID(contract_id))
        .all()
    )


def _versions(db_session, contract_id):
    return (
        db_session.query(ContractVersion)
        .filter(ContractVersion.contract_id == uuid.UUID(contract_id))
        .all()
    )


def test_merge_template_body_fills_known_fields_and_keeps_unknown_placeholders():
    merged = merge_template_body(
        "Between {{counterpartyCompany}} and us, value {{contractValue}} {{currency}}. {{unknownField}}",
        {"counterpartyCompany": "Globex Corp", "contractValue": "10000.00", "currency": "USD"},
    )
    assert merged == "Between Globex Corp and us, value 10000.00 USD. {{unknownField}}"


def test_create_from_template_generates_merged_version_one(db_client, db_session):
    _tenant_id, admin_id, owner_id, counterparty_id, template_id = _setup_basic(db_session)
    resp = db_client.post(
        "/api/v1/contracts",
        json=_valid_payload(template_id, counterparty_id, owner_id),
        headers=_headers(TENANT_ADMIN, admin_id),
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "Draft"
    assert body["message"] == CREATED_MESSAGE
    assert body["documentVersionNumber"] == 1

    documents = _documents(db_session, body["id"])
    assert len(documents) == 1
    assert documents[0].file_type == "DOCX"
    assert documents[0].file_name.endswith(".docx")
    assert documents[0].is_corrupted_or_missing is False

    versions = _versions(db_session, body["id"])
    assert [v.version_number for v in versions] == [1]
    assert "NDA Template" in versions[0].change_summary


def test_create_from_third_party_paper_uses_the_upload_as_version_one(db_client, db_session):
    tenant_id, admin_id, owner_id, counterparty_id, _template_id = _setup_basic(db_session)
    file_id = uuid.uuid4()
    db_session.add(
        UploadedFile(
            id=file_id,
            tenant_id=tenant_id,
            file_name="counterparty-paper.pdf",
            file_size=4096,
            file_format="PDF",
            storage_url="/uploads/counterparty-paper.pdf",
            created_by=admin_id,
            updated_by=admin_id,
        )
    )
    db_session.commit()

    payload = _valid_payload(uuid.uuid4(), counterparty_id, owner_id)
    payload.pop("templateId")
    payload["thirdPartyPaperFileId"] = str(file_id)
    resp = db_client.post("/api/v1/contracts", json=payload, headers=_headers(TENANT_ADMIN, admin_id))
    assert resp.status_code == 201
    body = resp.json()
    assert body["documentVersionNumber"] == 1
    assert body["message"] == CREATED_MESSAGE

    documents = _documents(db_session, body["id"])
    assert len(documents) == 1
    # The uploaded file itself is Version 1 -- same name, same size, no merge.
    assert documents[0].file_name == "counterparty-paper.pdf"
    assert documents[0].file_type == "PDF"
    assert documents[0].file_size_bytes == 4096

    versions = _versions(db_session, body["id"])
    assert [v.version_number for v in versions] == [1]
    assert "no merge" in versions[0].change_summary
