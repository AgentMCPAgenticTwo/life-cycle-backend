"""UC2 document generation: turning a saved contract into its Version 1 document.

Two sources, one outcome (UC2-BR-014/015 -- both paths end in a Draft contract that owns a
`contract_documents` row and a `contract_versions` row numbered 1):

* **Template** -- the template body's merge fields are populated from the contract and its
  counterparty, and the rendered document becomes Version 1.
* **Third Party Paper** -- the uploaded file itself becomes Version 1, with no merge.

There is no blob store in this sandbox, so the rendered body is not persisted byte-for-byte:
`contract_documents` carries the generated file's name/type/size and a deterministic storage
path, exactly as the uploaded-paper path already does (see `app.services.contract_lifecycle`,
which serves these rows to UC8's document panel).
"""
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.contract import Contract
from app.models.contract_lifecycle import ContractDocument, ContractVersion
from app.models.counterparty import Counterparty
from app.models.template import Template
from app.models.user import User
from app.repositories import contract_lifecycle as lifecycle_repo
from app.repositories import contracts as contracts_repo

CREATED_MESSAGE = "Contract created successfully and saved as Draft"

_MERGE_FIELD_RE = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")


def _merge_values(contract: Contract, counterparty: Counterparty, owner: User) -> dict[str, str]:
    def _text(value) -> str:
        return "" if value is None else str(value)

    return {
        "contractName": _text(contract.contract_name),
        "contractType": _text(contract.contract_type),
        "industry": _text(contract.industry),
        "contractValue": _text(contract.contract_value),
        "currency": _text(contract.currency),
        "startDate": _text(contract.start_date),
        "endDate": _text(contract.end_date),
        "renewalType": _text(contract.renewal_type),
        "noticePeriod": _text(contract.notice_period),
        "assignedDate": _text(contract.assigned_date),
        "dueDate": _text(contract.due_date),
        "contractOwnerName": _text(owner.name),
        "counterpartyName": _text(counterparty.name),
        "counterpartyEmail": _text(counterparty.email),
        "counterpartyCompany": _text(counterparty.company),
        "counterpartyAddress": _text(counterparty.address),
        "counterpartyGstTaxId": _text(counterparty.gst_tax_id),
    }


def merge_template_body(template_body: str, values: dict[str, str]) -> str:
    """Replaces every `{{mergeField}}` the contract knows a value for. A placeholder with no
    matching value is left untouched rather than blanked, so an unmapped field stays visible
    in the generated document instead of silently disappearing."""
    return _MERGE_FIELD_RE.sub(
        lambda m: values[m.group(1)] if m.group(1) in values else m.group(0), template_body
    )


def generate_version_one(
    db: Session,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    contract: Contract,
    counterparty: Counterparty,
    owner: User,
) -> int:
    """Creates the contract's Version 1 document. Returns the version number (always 1).

    Flushes but does not commit -- the caller owns the transaction so the contract and its
    document are saved together.
    """
    now = datetime.now(timezone.utc)

    if contract.template_id is not None:
        template: Template = contracts_repo.get_template(db, tenant_id, contract.template_id)
        rendered = merge_template_body(template.template_body, _merge_values(contract, counterparty, owner))
        file_type = template.document_format
        file_name = f"{contract.contract_name}.{file_type.lower()}"
        file_size = len(rendered.encode("utf-8"))
        change_summary = (
            f"Version 1 generated from template '{template.template_name}' with merge fields populated."
        )
    else:
        uploaded = contracts_repo.get_uploaded_file(db, tenant_id, contract.third_party_paper_file_id)
        file_type = uploaded.file_format
        file_name = uploaded.file_name
        file_size = uploaded.file_size
        change_summary = "Version 1 created from the uploaded third party paper (no merge applied)."

    lifecycle_repo.insert_document(
        db,
        ContractDocument(
            contract_id=contract.id,
            file_name=file_name,
            file_type=file_type,
            file_size_bytes=file_size,
            storage_path=f"/documents/{contract.id}/v1.{file_type.lower()}",
            is_corrupted_or_missing=False,
            created_at=now,
            created_by=user_id,
            updated_at=now,
            updated_by=user_id,
        ),
    )
    lifecycle_repo.insert_contract_version(
        db,
        ContractVersion(
            contract_id=contract.id,
            version_number=1,
            change_summary=change_summary,
            created_at=now,
            created_by=user_id,
            updated_at=now,
            updated_by=user_id,
        ),
    )
    return 1
