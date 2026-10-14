"""Business rules for the `contracts` resource: the tenant-scoped repository list, the
permitted-access check on contract detail, and full Create validation -- see CLAUDE.md's
uc123 module section and this task's stories UC1-AF-006, UC1-BR-007, UC1-FV-001,
UC1-FV-005, UC1-MF-001, UC2-AF-001..UC2-FV-002, UC2-MF-001 (T-CONTRACTS-API/TASK.md).
"""
import re
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.errors import ForbiddenError, NotFoundError, ValidationFailedError
from app.models.contract import Contract
from app.models.counterparty import Counterparty
from app.models.user import User
from app.repositories import contracts as contracts_repo
from app.schemas.contract import (
    ContractListItemResponse,
    ContractListResponse,
    ContractResponse,
    CreateContractRequest,
)
from app.schemas.pagination import PageParams
from app.services import contract_documents

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _is_blank(value: str | None) -> bool:
    return value is None or not value.strip()


def _resolve_user_name(db: Session, user_id: uuid.UUID) -> str:
    row = db.query(User).filter(User.id == user_id).first()
    return row.name if row is not None else "Unknown"


def _resolve_counterparty_row(db: Session, counterparty_id: uuid.UUID) -> Counterparty | None:
    return db.query(Counterparty).filter(Counterparty.id == counterparty_id).first()


def _to_list_item(db: Session, contract: Contract) -> ContractListItemResponse:
    counterparty = _resolve_counterparty_row(db, contract.counterparty_id)
    return ContractListItemResponse(
        id=contract.id,
        contractName=contract.contract_name,
        contractType=contract.contract_type,
        department=contract.department,
        counterpartyName=counterparty.name if counterparty else "Unknown",
        contractOwnerName=_resolve_user_name(db, contract.contract_owner_id),
        status=contract.status,
        startDate=contract.start_date,
        endDate=contract.end_date,
        contractValue=float(contract.contract_value),
        currency=contract.currency,
        riskScore=contract.risk_score,
    )


def _to_response(db: Session, contract: Contract) -> ContractResponse:
    counterparty = _resolve_counterparty_row(db, contract.counterparty_id)
    return ContractResponse(
        id=contract.id,
        contractName=contract.contract_name,
        contractType=contract.contract_type,
        industry=contract.industry,
        department=contract.department,
        templateId=contract.template_id,
        thirdPartyPaperFileId=contract.third_party_paper_file_id,
        counterpartyId=contract.counterparty_id,
        counterpartyName=counterparty.name if counterparty else "Unknown",
        counterpartyEmail=counterparty.email if counterparty else "",
        counterpartyCompany=counterparty.company if counterparty else "",
        counterpartyAddress=counterparty.address if counterparty else None,
        counterpartyGstTaxId=counterparty.gst_tax_id if counterparty else None,
        contractOwnerId=contract.contract_owner_id,
        contractOwnerName=_resolve_user_name(db, contract.contract_owner_id),
        contractValue=float(contract.contract_value),
        currency=contract.currency,
        startDate=contract.start_date,
        endDate=contract.end_date,
        renewalType=contract.renewal_type,
        noticePeriod=contract.notice_period,
        assignedDate=contract.assigned_date,
        dueDate=contract.due_date,
        status=contract.status,
        riskScore=contract.risk_score,
        createdAt=contract.created_at,
        updatedAt=contract.updated_at,
    )


def list_contracts(
    db: Session,
    tenant_id: uuid.UUID,
    page_params: PageParams,
    *,
    status: str | None,
    contract_type: str | None,
    department: str | None,
    counterparty_id: uuid.UUID | None,
    owner_id: uuid.UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> ContractListResponse:
    # UC1-MF-001: tenant scoping only -- every allowed role sees the full repository list for
    # its own tenant; UC1-AF-006's role-based restriction applies to opening contract detail,
    # not to this list (see get_contract_detail / _has_permitted_access below).
    rows, total = contracts_repo.list_by_tenant(
        db,
        tenant_id,
        search=page_params.search,
        sort_by=page_params.sort_by,
        sort_order=page_params.sort_order,
        status=status,
        contract_type=contract_type,
        department=department,
        counterparty_id=counterparty_id,
        owner_id=owner_id,
        start_date=start_date,
        end_date=end_date,
        offset=page_params.offset,
        limit=page_params.page_size,
    )
    items = [_to_list_item(db, row) for row in rows]
    no_match = "No contracts match the applied filters." if not items else None
    return ContractListResponse(
        items=items,
        page=page_params.page,
        pageSize=page_params.page_size,
        totalCount=total,
        noMatchMessage=no_match,
    )


def _has_permitted_access(db: Session, user: CurrentUser, contract: Contract) -> bool:
    if user.role == "TENANT_ADMIN":
        return True
    user_uuid = uuid.UUID(user.user_id)
    if user.role == "CONTRACT_OWNER":
        return contract.contract_owner_id == user_uuid
    # LEGAL_REVIEWER / APPROVER / SIGNER: permitted only while a `contract_tasks` row
    # currently assigns them this contract's pending step (UC1-AF-006's Approver example).
    task = contracts_repo.get_current_task_for_assignee(db, contract.id, user_uuid)
    return task is not None


def get_contract_detail(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, contract_id: uuid.UUID
) -> ContractResponse:
    contract = contracts_repo.get_by_id(db, tenant_id, contract_id)
    if contract is None:
        raise NotFoundError("contract not found")
    if not _has_permitted_access(db, user, contract):
        raise ForbiddenError("You do not have access to this contract")
    return _to_response(db, contract)


def _validate_template_and_paper_selection(
    db: Session, tenant_id: uuid.UUID, payload: CreateContractRequest
) -> None:
    # UC2-BR-008 / UC2-BR-011: Template and Upload Third Party Paper are mutually exclusive,
    # and exactly one document source must be chosen.
    if payload.templateId is not None and payload.thirdPartyPaperFileId is not None:
        raise ValidationFailedError(
            "Template and Upload Third Party Paper are mutually exclusive.",
            details=["Template and Upload Third Party Paper are mutually exclusive."],
        )
    if payload.templateId is None and payload.thirdPartyPaperFileId is None:
        raise ValidationFailedError(
            "Select a Template or upload a Third Party Paper.",
            details=["Select a Template or upload a Third Party Paper."],
        )
    if payload.templateId is not None:
        template = contracts_repo.get_template(db, tenant_id, payload.templateId)
        if template is None:
            raise ValidationFailedError("Template not found.", details=["Template not found."])
        if template.status != "Active":
            # UC2-AF-002's exact message for an unusable (non-Active) template selection.
            raise ValidationFailedError(
                "No active templates available for this combination. Please upload third party paper.",
                details=["Selected template is not Active."],
            )
    else:
        uploaded = contracts_repo.get_uploaded_file(db, tenant_id, payload.thirdPartyPaperFileId)
        if uploaded is None:
            raise ValidationFailedError("Uploaded file not found.", details=["Uploaded file not found."])


def _resolve_counterparty(
    db: Session, tenant_id: uuid.UUID, user_uuid: uuid.UUID, payload: CreateContractRequest
) -> Counterparty:
    if payload.counterpartyId is not None:
        counterparty = contracts_repo.get_counterparty(db, tenant_id, payload.counterpartyId)
        if counterparty is None:
            raise ValidationFailedError("Counterparty not found.", details=["Counterparty not found."])
        return counterparty

    # UC2-BR-011 / UC2-FV-002: no existing match selected -- Counterparty Search, Name,
    # Email and Company become mandatory to add a new counterparty; Address and GST/Tax ID
    # stay optional.
    missing = []
    if _is_blank(payload.counterpartySearch):
        missing.append("Counterparty Search is required.")
    if _is_blank(payload.counterpartyName):
        missing.append("Counterparty Name is required.")
    if _is_blank(payload.counterpartyEmail):
        missing.append("Counterparty Email is required.")
    if _is_blank(payload.counterpartyCompany):
        missing.append("Counterparty Company is required.")
    if missing:
        raise ValidationFailedError("Please fill all mandatory fields", details=missing)

    if not _EMAIL_RE.match(payload.counterpartyEmail):
        raise ValidationFailedError(
            "Counterparty Email must be a valid email address.",
            details=["Counterparty Email must be a valid email address."],
        )

    counterparty = Counterparty(
        tenant_id=tenant_id,
        name=payload.counterpartyName,
        email=payload.counterpartyEmail,
        company=payload.counterpartyCompany,
        address=payload.counterpartyAddress,
        gst_tax_id=payload.counterpartyGstTaxId,
        created_by=user_uuid,
        updated_by=user_uuid,
    )
    return contracts_repo.insert_counterparty(db, counterparty)


def _validate_contract_owner(db: Session, tenant_id: uuid.UUID, owner_id: uuid.UUID) -> User:
    # UC2-BR-003 / UC2-BR-012: Contract Owner must be a user holding the Contract Owner role
    # within the same tenant, whether the actor is reassigning themselves or (as Tenant
    # Admin) anyone else.
    owner = contracts_repo.get_user(db, tenant_id, owner_id)
    if owner is None or owner.role != "CONTRACT_OWNER":
        message = "Contract Owner must be a valid user with the Contract Owner role in your tenant."
        raise ValidationFailedError(message, details=[message])
    return owner


def _validate_dates(payload: CreateContractRequest) -> date:
    # UC2-AF-003 / UC2-BR-007: End Date must be strictly later than Start Date.
    if payload.endDate < payload.startDate:
        raise ValidationFailedError(
            "End date cannot be earlier than start date",
            details=["End date cannot be earlier than start date"],
        )
    if payload.endDate == payload.startDate:
        raise ValidationFailedError(
            "End date must be later than start date",
            details=["End date must be later than start date"],
        )
    # UC2-AF-004 / UC2-BR-005 / UC2-BR-006: Due Date must be on or after the system-generated
    # Assigned Date (today) -- computed once here so Assigned Date and the comparison agree.
    assigned_date = date.today()
    if payload.dueDate < assigned_date:
        raise ValidationFailedError(
            "Due date cannot be earlier than assigned date",
            details=["Due date cannot be earlier than assigned date"],
        )
    return assigned_date


def _validate_notice_period(payload: CreateContractRequest) -> int | None:
    # UC2-BR-004: Notice Period is mandatory only when Renewal Type is Auto or Manual; it is
    # disabled and cleared (never persisted) when Renewal Type is None.
    if payload.renewalType == "None":
        return None
    if payload.noticePeriod is None:
        raise ValidationFailedError(
            "Please fill all mandatory fields",
            details=["Notice Period is required when Renewal Type is Auto or Manual."],
        )
    return payload.noticePeriod


def create_contract(
    db: Session, tenant_id: uuid.UUID, user: CurrentUser, payload: CreateContractRequest
) -> ContractResponse:
    user_uuid = uuid.UUID(user.user_id)

    _validate_template_and_paper_selection(db, tenant_id, payload)
    counterparty = _resolve_counterparty(db, tenant_id, user_uuid, payload)
    owner = _validate_contract_owner(db, tenant_id, payload.contractOwnerId)
    assigned_date = _validate_dates(payload)
    notice_period = _validate_notice_period(payload)

    # UC2-BR-010 / UC2-BR-014 / UC2-BR-015: every new contract, from a Template or an
    # uploaded paper alike, is created in Draft and only Draft.
    contract = Contract(
        tenant_id=tenant_id,
        # ContractResponse/ContractListItemResponse require contractName, but
        # CreateContractRequest carries no such field (see this task's blockers) --
        # derived from Contract Type and Counterparty Company, the two values always known.
        contract_name=f"{payload.contractType} - {counterparty.company}",
        contract_type=payload.contractType,
        industry=payload.industry,
        department=None,
        template_id=payload.templateId,
        third_party_paper_file_id=payload.thirdPartyPaperFileId,
        counterparty_id=counterparty.id,
        contract_owner_id=owner.id,
        contract_value=Decimal(str(payload.contractValue)),
        currency=payload.currency,
        start_date=payload.startDate,
        end_date=payload.endDate,
        renewal_type=payload.renewalType,
        notice_period=notice_period,
        assigned_date=assigned_date,
        due_date=payload.dueDate,
        status="Draft",
        risk_score=None,
        created_by=user_uuid,
        updated_by=user_uuid,
    )
    contracts_repo.insert_contract(db, contract)
    # UC2-BR-014/015: saving the contract also produces its Version 1 document -- merged from
    # the Template, or the uploaded Third Party Paper taken as-is -- in the same transaction.
    version_number = contract_documents.generate_version_one(
        db, tenant_id, user_uuid, contract, counterparty, owner
    )
    db.commit()
    db.refresh(contract)
    response = _to_response(db, contract)
    response.documentVersionNumber = version_number
    response.message = contract_documents.CREATED_MESSAGE
    return response
